"""
Pattern Training Router
完整训练/验证流程（重建版）
"""

import os
import json
import random
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.database import StockDatabase
from app.pattern_matcher import load_classic_patterns, match_all_patterns
from app.models import TrainingRequest

router = APIRouter(prefix="/api/training", tags=["Pattern Training"])

# 全局任务状态，与前端 task_name 对齐
training_status: Dict[str, Dict[str, Any]] = {
    "filter_special_samples": {"running": False, "progress": 0, "message": ""},
    "extract_features": {"running": False, "progress": 0, "message": ""},
    "cluster_samples": {"running": False, "progress": 0, "message": ""},
    "extract_ai_patterns": {"running": False, "progress": 0, "message": ""},
    "validate_patterns": {"running": False, "progress": 0, "message": ""},
}


def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _root_path(*parts: str) -> str:
    return os.path.join(_script_dir(), "..", "..", "..", *parts)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@router.get("/task-status/{task_name}")
async def get_task_status(task_name: str):
    data = training_status.get(task_name)
    if not data:
        return {"success": False, "message": "任务不存在"}
    return {"success": True, "data": data}


# ------------------------------------------------------------
# 步骤1：过滤特殊样本（去除已匹配经典模式的样本）
# ------------------------------------------------------------
@router.post("/filter-special-samples")
async def filter_special_samples(request: TrainingRequest, background_tasks: BackgroundTasks):
    if training_status["filter_special_samples"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task(sample_count: int):
        try:
            training_status["filter_special_samples"].update(running=True, progress=10, message="初始化数据库...")
            db = StockDatabase(db_path=_root_path("data", "stocks.db"))

            patterns_path = _root_path("classic_patterns.json")
            # 经典 + AI 模式合并
            patterns = []
            if os.path.exists(patterns_path):
                patterns.extend(load_classic_patterns(patterns_path))
            ai_path = _root_path("new_patterns.json")
            if os.path.exists(ai_path):
                ai_data = _load_json(ai_path)
                patterns.extend(ai_data.get("patterns", []))
            if not patterns:
                training_status["filter_special_samples"].update(progress=0, message="未找到经典模式")
                return
            training_status["filter_special_samples"].update(
                progress=20, message=f"已加载{len(patterns)}个经典模式"
            )

            samples_df = db.get_rising_samples(sample_count=sample_count, rise_threshold=0.06)
            if len(samples_df) == 0:
                training_status["filter_special_samples"].update(progress=0, message="未找到样本")
                return
            training_status["filter_special_samples"].update(
                progress=30, message=f"获取样本{len(samples_df)}条"
            )

            sample_ids = samples_df["id"].tolist()
            samples_with_context = db.get_samples_with_context(sample_ids, days_before=20)
            training_status["filter_special_samples"].update(
                progress=50, message=f"获取完整样本{len(samples_with_context)}条"
            )

            special_samples: List[Dict[str, Any]] = []
            classic_samples: List[Dict[str, Any]] = []
            for i, sample in enumerate(samples_with_context):
                matched = match_all_patterns(sample["kline_data"], patterns)
                if len(matched) == 0:
                    special_samples.append(
                        {
                            "sample_id": sample["sample_id"],
                            "code": sample["code"],
                            "date": sample["date"],
                            "kline_data": sample["kline_data"],
                        }
                    )
                else:
                    classic_samples.append(
                        {
                            "sample_id": sample["sample_id"],
                            "code": sample["code"],
                            "date": sample["date"],
                            "matched_patterns": [m["pattern_name"] for m in matched],
                        }
                    )
                if (i + 1) % 50 == 0:
                    progress = 50 + int((i + 1) / len(samples_with_context) * 30)
                    training_status["filter_special_samples"]["progress"] = progress

            output_dir = _root_path()
            _save_json(os.path.join(output_dir, "special_samples.json"), special_samples)
            _save_json(os.path.join(output_dir, "classic_samples_stat.json"), classic_samples)

            training_status["filter_special_samples"].update(
                progress=100,
                message=f"完成：经典{len(classic_samples)}，特殊{len(special_samples)}",
            )
        except Exception as e:
            training_status["filter_special_samples"].update(progress=0, message=f"错误: {str(e)}")
        finally:
            training_status["filter_special_samples"]["running"] = False

    background_tasks.add_task(task, request.sample_count or 300)
    return {"success": True, "message": "过滤任务已启动"}


@router.get("/results/special-samples")
async def get_special_samples():
    path = _root_path("special_samples.json")
    if not os.path.exists(path):
        return {"success": False, "message": "No special samples found"}
    data = _load_json(path)
    return {"success": True, "count": len(data), "data": data}


# ------------------------------------------------------------
# 步骤2：提取特征
# ------------------------------------------------------------
@router.post("/extract-features")
async def extract_features(background_tasks: BackgroundTasks):
    if training_status["extract_features"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            training_status["extract_features"].update(running=True, progress=20, message="加载特殊样本...")
            special_file = _root_path("special_samples.json")
            if not os.path.exists(special_file):
                training_status["extract_features"].update(progress=0, message="无特殊样本")
                return
            special_samples = _load_json(special_file)
            if len(special_samples) == 0:
                training_status["extract_features"].update(progress=0, message="无特殊样本")
                return

            training_status["extract_features"].update(
                progress=40, message=f"提取 {len(special_samples)} 个样本特征..."
            )
            feature_vectors = []
            for i, sample in enumerate(special_samples):
                kline_data = sample["kline_data"]
                closes = [day["close"] for day in kline_data]
                volumes = [day["volume"] for day in kline_data]

                volatility = float(np.std(closes) / np.mean(closes)) if len(closes) > 0 else 0.0
                mid = len(volumes) // 2
                volume_trend = (
                    float(np.mean(volumes[mid:]) / np.mean(volumes[:mid]))
                    if mid > 0 and np.mean(volumes[:mid]) > 0
                    else 1.0
                )
                momentum = float((closes[-1] - closes[0]) / closes[0]) if len(closes) > 1 and closes[0] > 0 else 0.0
                total_rise = momentum

                feature_vectors.append(
                    {
                        "sample_id": sample["sample_id"],
                        "code": sample["code"],
                        "date": sample["date"],
                        "features": {
                            "volatility": volatility,
                            "volume_trend": volume_trend,
                            "momentum": momentum,
                            "total_rise": total_rise,
                        },
                    }
                )
                if (i + 1) % 20 == 0:
                    training_status["extract_features"]["progress"] = 40 + int((i + 1) / len(special_samples) * 50)

            _save_json(_root_path("feature_vectors.json"), feature_vectors)
            training_status["extract_features"].update(
                progress=100, message=f"完成，提取 {len(feature_vectors)} 个特征向量"
            )
        except Exception as e:
            training_status["extract_features"].update(progress=0, message=f"错误: {str(e)}")
        finally:
            training_status["extract_features"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "特征提取任务已启动"}


@router.get("/results/feature-vectors")
async def get_feature_vectors():
    path = _root_path("feature_vectors.json")
    if not os.path.exists(path):
        return {"success": False, "message": "No feature vectors found"}
    data = _load_json(path)
    return {"success": True, "count": len(data), "data": data}


# ------------------------------------------------------------
# 步骤3：K-means 聚类
# ------------------------------------------------------------
@router.post("/cluster-samples")
async def cluster_samples(background_tasks: BackgroundTasks):
    if training_status["cluster_samples"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            from sklearn.cluster import KMeans
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics import silhouette_score

            training_status["cluster_samples"].update(running=True, progress=20, message="加载特征向量...")
            feature_file = _root_path("feature_vectors.json")
            if not os.path.exists(feature_file):
                training_status["cluster_samples"].update(progress=0, message="无特征向量")
                return
            sample_features = _load_json(feature_file)
            if len(sample_features) == 0:
                training_status["cluster_samples"].update(progress=0, message="无特征向量")
                return

            features_df = pd.DataFrame([s["features"] for s in sample_features])
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features_df)

            training_status["cluster_samples"].update(progress=40, message="寻找最优簇数...")
            max_clusters = min(8, len(features_df))
            silhouette_scores: List[float] = []
            ks: List[int] = []
            for k in range(2, max_clusters + 1):
                kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                labels = kmeans.fit_predict(features_scaled)
                ks.append(k)
                silhouette_scores.append(silhouette_score(features_scaled, labels))
            best_k = ks[int(np.argmax(silhouette_scores))] if silhouette_scores else 2

            training_status["cluster_samples"].update(progress=60, message=f"使用 k={best_k} 聚类...")
            kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(features_scaled)

            for i, sample in enumerate(sample_features):
                sample["cluster"] = int(labels[i])

            clustered_data: Dict[str, Any] = {}
            for cluster_id in range(best_k):
                cluster_samples = [s for s in sample_features if s["cluster"] == cluster_id]
                clustered_data[f"cluster_{cluster_id}"] = {
                    "cluster_id": cluster_id,
                    "sample_count": len(cluster_samples),
                    "samples": [
                        {"sample_id": s["sample_id"], "code": s["code"], "date": s["date"]} for s in cluster_samples
                    ],
                }

            _save_json(_root_path("clustered_samples.json"), clustered_data)
            training_status["cluster_samples"].update(
                progress=100, message=f"完成，{best_k} 个簇"
            )
        except Exception as e:
            training_status["cluster_samples"].update(progress=0, message=f"错误: {str(e)}")
        finally:
            training_status["cluster_samples"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "聚类任务已启动"}


@router.get("/results/clustered-samples")
async def get_clustered_samples():
    path = _root_path("clustered_samples.json")
    if not os.path.exists(path):
        return {"success": False, "message": "No clustered samples found"}
    data = _load_json(path)
    return {"success": True, "data": data}


# ------------------------------------------------------------
# 步骤4：AI 模式提取（若无 API Key 则生成占位）
# ------------------------------------------------------------
@router.post("/extract-ai-patterns")
async def extract_ai_patterns(background_tasks: BackgroundTasks):
    if training_status["extract_ai_patterns"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            import anthropic
            from dotenv import load_dotenv

            training_status["extract_ai_patterns"].update(running=True, progress=10, message="加载环境...")
            # 尝试加载 .env（若不存在则继续）
            env_path = _root_path("backend", ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path)
            api_key = os.environ.get("ANTHROPIC_API_KEY")

            clustered_file = _root_path("clustered_samples.json")
            if not os.path.exists(clustered_file):
                training_status["extract_ai_patterns"].update(progress=0, message="无聚类结果")
                return
            clustered_data = _load_json(clustered_file)

            special_samples = _load_json(_root_path("special_samples.json")) if os.path.exists(_root_path("special_samples.json")) else []
            sample_map = {s["sample_id"]: s for s in special_samples}
            features_data = _load_json(_root_path("feature_vectors.json")) if os.path.exists(_root_path("feature_vectors.json")) else []
            feature_map = {f["sample_id"]: f["features"] for f in features_data}

            def analyze_cluster(cluster_id: int, cluster_samples: List[Dict[str, Any]], cluster_stats: Dict[str, Any]):
                # 无 API Key 时返回占位模式
                if not api_key:
                    return {
                        "pattern_name": f"AI模式{cluster_id}",
                        "description": "占位：未配置 API Key",
                        "pattern_id": f"AI{cluster_id:03d}",
                        "pattern_type": "ai_discovered",
                        "is_active": True,
                        "cluster_id": cluster_id,
                        "cluster_size": len(cluster_samples),
                        "cluster_stats": cluster_stats,
                        "match_rules": [],
                    }
                client = anthropic.Anthropic(api_key=api_key)
                prompt = f"""你是资深量化分析师，请基于簇特征提取可编程的模式定义：
簇大小: {len(cluster_samples)}
簇特征: {json.dumps(cluster_stats, ensure_ascii=False)}
样本示例(前5): {json.dumps(cluster_samples[:5], ensure_ascii=False)}
要求输出 JSON：pattern_name, description, match_rules(中文描述列表)"""
                message = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1200,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = message.content[0].text
                if "```" in text:
                    start = text.find("```")
                    end = text.find("```", start + 3)
                    text = text[start + 3 : end].strip()
                return json.loads(text)

            new_patterns = []
            total_clusters = len(clustered_data)
            for idx, (_, cluster_info) in enumerate(clustered_data.items()):
                cluster_id = cluster_info["cluster_id"]
                cluster_samples = []
                for sample_ref in cluster_info["samples"]:
                    sid = sample_ref["sample_id"]
                    if sid in sample_map:
                        cluster_samples.append(sample_map[sid])
                cluster_features = [feature_map[s["sample_id"]] for s in cluster_samples if s["sample_id"] in feature_map]
                if cluster_features:
                    cluster_stats = {
                        "volatility": float(np.mean([f["volatility"] for f in cluster_features])),
                        "volume_trend": float(np.mean([f["volume_trend"] for f in cluster_features])),
                        "momentum": float(np.mean([f["momentum"] for f in cluster_features])),
                        "total_rise": float(np.mean([f["total_rise"] for f in cluster_features])),
                    }
                else:
                    cluster_stats = {"volatility": 0, "volume_trend": 1.0, "momentum": 0, "total_rise": 0}

                training_status["extract_ai_patterns"].update(
                    progress=20 + int(idx / max(1, total_clusters) * 70),
                    message=f"分析簇 {cluster_id} ({len(cluster_samples)} 样本)...",
                )
                try:
                    pattern = analyze_cluster(cluster_id, cluster_samples, cluster_stats)
                    new_patterns.append(pattern)
                except Exception as e:
                    print(f"Cluster {cluster_id} failed: {e}")
                    continue

            output_data = {
                "patterns": new_patterns,
                "metadata": {"version": "1.0", "created_date": datetime.now().strftime("%Y-%m-%d")},
            }
            _save_json(_root_path("new_patterns.json"), output_data)
            training_status["extract_ai_patterns"].update(progress=100, message=f"完成，提取 {len(new_patterns)} 个 AI 模式")
        except Exception as e:
            training_status["extract_ai_patterns"].update(progress=0, message=f"错误: {str(e)}")
        finally:
            training_status["extract_ai_patterns"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "AI 模式提取任务已启动"}


@router.get("/results/ai-patterns")
async def get_ai_patterns():
    patterns_file = _root_path("new_patterns.json")
    if not os.path.exists(patterns_file):
        return {"success": False, "message": "No AI patterns found"}
    data = _load_json(patterns_file)
    return {"success": True, "data": data}


# ------------------------------------------------------------
# 步骤5：程序化模式验证
# ------------------------------------------------------------
@router.post("/validate-patterns")
async def validate_patterns(background_tasks: BackgroundTasks):
    """
    方案B：程序化验证
    使用历史快照 + 程序化匹配计算多级涨幅命中率
    """
    if training_status["validate_patterns"]["running"]:
        return {"success": False, "message": "验证任务正在运行中"}

    def validate_task():
        try:
            training_status["validate_patterns"].update(running=True, progress=5, message="初始化中...")

            db_path = _root_path("data", "stocks.db")
            patterns_path = _root_path("classic_patterns.json")
            validation_file = _root_path("pattern_validation.json")

            db = StockDatabase(db_path=db_path)
            patterns = []
            if os.path.exists(patterns_path):
                patterns.extend(load_classic_patterns(patterns_path))
            ai_path = _root_path("new_patterns.json")
            if os.path.exists(ai_path):
                ai_data = _load_json(ai_path)
                patterns.extend(ai_data.get("patterns", []))
            if len(patterns) == 0:
                training_status["validate_patterns"].update(progress=0, message="未找到模式")
                return

            training_status["validate_patterns"].update(progress=10, message=f"已加载{len(patterns)}个模式")

            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM stock_data")
            latest_row = cursor.fetchone()
            conn.close()
            latest_date = latest_row[0] if latest_row and latest_row[0] else None
            if not latest_date:
                training_status["validate_patterns"].update(progress=0, message="无K线数据")
                return

            def sample_window(start_back: int, window: int, count: int):
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    f"""
                    SELECT code, date
                    FROM stock_data
                    WHERE date BETWEEN date(?, '-{start_back} days') AND date(?, '-{start_back - window} days')
                    ORDER BY RANDOM()
                    LIMIT {count}
                    """,
                    (latest_date, latest_date),
                )
                rows = cursor.fetchall()
                conn.close()
                return [{"code": r[0], "date": r[1]} for r in rows]

            # 分段采样
            # 扩大采样窗口覆盖 120-60 天、60-30 天
            samples = (
                [{"code": r["code"], "date": r["date"]} for _, r in db.get_rising_samples(sample_count=1500, rise_threshold=0.03).iterrows()]
                + sample_window(180, 90, 500)
                + sample_window(90, 60, 500)
                + sample_window(60, 30, 500)
            )
            if len(samples) == 0:
                training_status["validate_patterns"].update(progress=0, message="未找到样本")
                return

            training_status["validate_patterns"].update(
                progress=25, message=f"获取样本{len(samples)}条"
            )

            stats: Dict[str, Dict[str, Any]] = {}
            processed = 0

            for sample in samples:
                code = sample["code"]
                base_date = sample["date"]

                stock_df = db.get_stock_data(code, days=40)
                if len(stock_df) == 0:
                    continue

                stock_df = stock_df[stock_df["date"] <= base_date].sort_values("date")
                kline_data = []
                for _, k in stock_df.tail(30).iterrows():
                    kline_data.append(
                        {
                            "date": k["date"],
                            "open": k["open"],
                            "high": k["high"],
                            "low": k["low"],
                            "close": k["close"],
                            "volume": k["volume"],
                        }
                    )
                if len(kline_data) < 10:
                    continue

                matched = match_all_patterns(kline_data, patterns)
                if not matched:
                    continue

                rise_3d = db.get_future_rise(code, base_date, days=3)
                if rise_3d is None:
                    continue

                for m in matched:
                    name = m["pattern_name"]
                    if name not in stats:
                        stats[name] = {"total": 0, "rises": []}
                    stats[name]["total"] += 1
                    stats[name]["rises"].append(rise_3d)

                processed += 1
                if processed % 200 == 0:
                    training_status["validate_patterns"].update(
                        message=f"处理中 {processed}/{len(samples)}",
                        progress=min(90, 25 + int(processed / len(samples) * 50)),
                    )

            validation_summary = []
            # 先把有匹配的模式写入
            for pattern_name, data in stats.items():
                total = data["total"]
                arr = np.array(data["rises"]) if total > 0 else np.array([])
                if total == 0 or arr.size == 0:
                    continue

                # 基础成功率统计
                rate_1pct = float((arr >= 0.01).sum() / total)
                rate_3pct = float((arr >= 0.03).sum() / total)
                rate_5pct = float((arr >= 0.05).sum() / total)
                positive_rate = float((arr > 0).sum() / total)

                # 收益分布统计
                avg_rise = float(arr.mean()) if arr.size else 0
                median_rise = float(np.median(arr)) if arr.size else 0
                std_rise = float(arr.std()) if arr.size else 0

                # 最大/最小收益
                max_rise = float(arr.max()) if arr.size else 0
                min_rise = float(arr.min()) if arr.size else 0

                # 胜率统计（期望收益）
                win_count = (arr > 0).sum()
                loss_count = (arr < 0).sum()
                win_rate = float(win_count / total) if total > 0 else 0

                # 平均盈利和平均亏损
                avg_profit = float(arr[arr > 0].mean()) if (arr > 0).any() else 0
                avg_loss = float(arr[arr < 0].mean()) if (arr < 0).any() else 0

                # 盈亏比（平均盈利/平均亏损的绝对值）
                profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0

                # 期望收益 = 胜率 * 平均盈利 + 亏损率 * 平均亏损
                expected_return = win_rate * avg_profit + (1 - win_rate) * avg_loss

                # 最大回撤（连续亏损）
                cumulative_returns = np.cumsum(arr)
                running_max = np.maximum.accumulate(cumulative_returns)
                drawdown = cumulative_returns - running_max
                max_drawdown = float(drawdown.min()) if drawdown.size else 0

                # 夏普比率（简化版，假设无风险利率为0）
                sharpe_ratio = float(avg_rise / std_rise) if std_rise != 0 else 0

                # 收益分布百分位数
                percentile_25 = float(np.percentile(arr, 25)) if arr.size else 0
                percentile_75 = float(np.percentile(arr, 75)) if arr.size else 0

                validation_summary.append(
                    {
                        "pattern_name": pattern_name,
                        "total_matches": total,
                        "successful_matches": int((arr >= 0.03).sum()),

                        # 成功率指标
                        "success_rate": rate_3pct,
                        "success_rate_1pct": rate_1pct,
                        "success_rate_3pct": rate_3pct,
                        "success_rate_5pct": rate_5pct,
                        "positive_rate": positive_rate,

                        # 收益统计
                        "avg_rise": avg_rise,
                        "median_rise": median_rise,
                        "std_rise": std_rise,
                        "max_rise": max_rise,
                        "min_rise": min_rise,

                        # 胜率与期望
                        "win_rate": win_rate,
                        "win_count": int(win_count),
                        "loss_count": int(loss_count),
                        "avg_profit": avg_profit,
                        "avg_loss": avg_loss,
                        "profit_loss_ratio": profit_loss_ratio,
                        "expected_return": expected_return,

                        # 风险指标
                        "max_drawdown": max_drawdown,
                        "sharpe_ratio": sharpe_ratio,

                        # 分布百分位
                        "percentile_25": percentile_25,
                        "percentile_75": percentile_75,

                        "is_valid": rate_3pct >= 0.30,
                    }
                )

            # 对于无匹配的模式（包含 AI），也写入 0 占位，便于前端显示
            existing = {item["pattern_name"] for item in validation_summary}
            for p in patterns:
                name = p.get("pattern_name")
                if not name or name in existing:
                    continue
                validation_summary.append(
                    {
                        "pattern_name": name,
                        "total_matches": 0,
                        "successful_matches": 0,
                        "success_rate": 0,
                        "success_rate_1pct": 0,
                        "success_rate_3pct": 0,
                        "success_rate_5pct": 0,
                        "positive_rate": 0,
                        "avg_rise": 0,
                        "median_rise": 0,
                        "is_valid": False,
                    }
                )

            result = {
                "validation_summary": validation_summary,
                "metadata": {
                    "total_snapshots": len(samples),
                    "validation_date": datetime.now().isoformat(),
                    "method": "programmatic_matching",
                    "thresholds": [0.01, 0.03, 0.05],
                },
            }
            _save_json(validation_file, result)
            training_status["validate_patterns"].update(
                message=f"完成！已验证{len(validation_summary)}个模式", progress=100
            )
        except Exception as e:
            training_status["validate_patterns"].update(message=f"错误: {str(e)}", progress=0)
        finally:
            training_status["validate_patterns"]["running"] = False

    background_tasks.add_task(validate_task)
    return {"success": True, "message": "验证任务已启动"}


@router.get("/results/pattern-validation")
async def get_pattern_validation():
    try:
        validation_file = _root_path("pattern_validation.json")
        if not os.path.exists(validation_file):
            return {"success": False, "message": "No validation results found"}
        data = _load_json(validation_file)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/merge-valid-patterns")
async def merge_valid_patterns():
    return {"success": False, "message": "未实现合并逻辑"}
