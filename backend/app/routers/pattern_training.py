"""
Pattern Training Router
重建版本（简化）用于训练与验证相关API
"""
import os
import json
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.database import StockDatabase
from app.pattern_matcher import load_classic_patterns, match_classic_patterns

router = APIRouter(prefix="/api/training", tags=["Pattern Training"])

# 全局任务状态，与前端的 task_name 对齐
training_status: Dict[str, Dict[str, Any]] = {
    "filter_special_samples": {"running": False, "progress": 0, "message": ""},
    "extract_features": {"running": False, "progress": 0, "message": ""},
    "cluster_samples": {"running": False, "progress": 0, "message": ""},
    "extract_ai_patterns": {"running": False, "progress": 0, "message": ""},
    "validate_patterns": {"running": False, "progress": 0, "message": ""},
}


# --------- 基础工具 ---------
def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _root_path(*parts: str) -> str:
    return os.path.join(_script_dir(), "..", "..", "..", *parts)


# --------- 任务状态查询 ---------
@router.get("/task-status/{task_name}")
async def get_task_status(task_name: str):
    data = training_status.get(task_name)
    if not data:
        return {"success": False, "message": "任务不存在"}
    return {"success": True, "data": data}


# --------- 步骤1 过滤特殊样本（简化占位） ---------
@router.post("/filter-special-samples")
async def filter_special_samples(background_tasks: BackgroundTasks):
    if training_status["filter_special_samples"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            training_status["filter_special_samples"].update(
                running=True, progress=100, message="占位任务完成（未实际执行）"
            )
        finally:
            training_status["filter_special_samples"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "过滤任务已启动"}


# --------- 步骤2 提取特征（占位） ---------
@router.post("/extract-features")
async def extract_features(background_tasks: BackgroundTasks):
    if training_status["extract_features"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            training_status["extract_features"].update(
                running=True, progress=100, message="占位任务完成（未实际执行）"
            )
        finally:
            training_status["extract_features"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "特征提取任务已启动"}


# --------- 步骤3 聚类（占位） ---------
@router.post("/cluster-samples")
async def cluster_samples(background_tasks: BackgroundTasks):
    if training_status["cluster_samples"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            training_status["cluster_samples"].update(
                running=True, progress=100, message="占位任务完成（未实际执行）"
            )
        finally:
            training_status["cluster_samples"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "聚类任务已启动"}


# --------- 步骤4 AI 模式提取（占位） ---------
@router.post("/extract-ai-patterns")
async def extract_ai_patterns(background_tasks: BackgroundTasks):
    if training_status["extract_ai_patterns"]["running"]:
        return {"success": False, "message": "任务正在运行中"}

    def task():
        try:
            training_status["extract_ai_patterns"].update(
                running=True, progress=100, message="占位任务完成（未实际执行）"
            )
        finally:
            training_status["extract_ai_patterns"]["running"] = False

    background_tasks.add_task(task)
    return {"success": True, "message": "AI 模式提取任务已启动"}


# --------- 步骤5 程序化模式验证（核心逻辑） ---------
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
            import numpy as np

            training_status["validate_patterns"].update(
                running=True, progress=5, message="初始化中..."
            )

            db_path = _root_path("data", "stocks.db")
            patterns_path = _root_path("classic_patterns.json")
            validation_file = _root_path("pattern_validation.json")

            db = StockDatabase(db_path=db_path)
            patterns = load_classic_patterns(patterns_path) if os.path.exists(patterns_path) else []
            if not patterns:
                training_status["validate_patterns"].update(progress=0, message="未找到模式")
                return

            training_status["validate_patterns"].update(
                progress=10, message=f"已加载{len(patterns)}个模式"
            )

            # 获取数据库最新交易日
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

            # 分段采样覆盖不同市场环境
            samples = sample_window(90, 30, 1000) + sample_window(60, 30, 1000)
            if not samples:
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

                matched = match_classic_patterns(kline_data, patterns)
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
            for pattern_name, data in stats.items():
                total = data["total"]
                arr = np.array(data["rises"]) if total > 0 else np.array([])
                if total == 0 or arr.size == 0:
                    continue

                rate_1pct = float((arr >= 0.01).sum() / total)
                rate_3pct = float((arr >= 0.03).sum() / total)
                rate_5pct = float((arr >= 0.05).sum() / total)
                positive_rate = float((arr > 0).sum() / total)
                avg_rise = float(arr.mean()) if arr.size else 0
                median_rise = float(np.median(arr)) if arr.size else 0

                validation_summary.append(
                    {
                        "pattern_name": pattern_name,
                        "total_matches": total,
                        "successful_matches": int((arr >= 0.03).sum()),
                        "success_rate": rate_3pct,
                        "success_rate_1pct": rate_1pct,
                        "success_rate_3pct": rate_3pct,
                        "success_rate_5pct": rate_5pct,
                        "positive_rate": positive_rate,
                        "avg_rise": avg_rise,
                        "median_rise": median_rise,
                        "is_valid": rate_3pct >= 0.30,
                    }
                )

            if len(validation_summary) == 0:
                validation_summary.append(
                    {
                        "pattern_name": "未找到匹配样本",
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

            with open(validation_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

            training_status["validate_patterns"].update(
                message=f"完成！已验证{len(validation_summary)}个模式", progress=100
            )

        except Exception as e:
            training_status["validate_patterns"].update(
                message=f"错误: {str(e)}", progress=0
            )
        finally:
            training_status["validate_patterns"]["running"] = False

    background_tasks.add_task(validate_task)
    return {"success": True, "message": "验证任务已启动"}


@router.get("/results/pattern-validation")
async def get_pattern_validation():
    """获取模式验证结果"""
    try:
        validation_file = _root_path("pattern_validation.json")
        if not os.path.exists(validation_file):
            return {"success": False, "message": "No validation results found"}
        with open(validation_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------- AI 模式列表（占位） ---------
@router.get("/results/ai-patterns")
async def get_ai_patterns():
    patterns_file = _root_path("new_patterns.json")
    if not os.path.exists(patterns_file):
        return {"success": False, "message": "No AI patterns found"}
    with open(patterns_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {"success": True, "data": data}


# --------- 模式可视化（简化版，与原逻辑类似） ---------
@router.get("/patterns/{pattern_name}/visualization")
async def get_pattern_visualization(pattern_name: str):
    try:
        import random

        db = StockDatabase(db_path=_root_path("data", "stocks.db"))
        samples_df = db.get_rising_samples(sample_count=100, rise_threshold=0.05)
        if len(samples_df) == 0:
            raise HTTPException(status_code=404, detail="No sample data available")

        sample_row = samples_df.iloc[random.randint(0, len(samples_df) - 1)]
        sample_id = sample_row["id"]
        samples_with_context = db.get_samples_with_context([sample_id], days_before=30)
        if len(samples_with_context) == 0:
            raise HTTPException(status_code=404, detail="No K-line data available")

        sample_data = samples_with_context[0]
        kline_data = sample_data["kline_data"]
        formatted = [
            {
                "date": k["date"],
                "open": float(k["open"]),
                "high": float(k["high"]),
                "low": float(k["low"]),
                "close": float(k["close"]),
                "volume": float(k["volume"]),
            }
            for k in kline_data
        ]

        return {
            "success": True,
            "data": {
                "pattern_name": pattern_name,
                "pattern_description": "",
                "stock_code": sample_data["code"],
                "date_range": {"start": formatted[0]["date"], "end": formatted[-1]["date"]},
                "kline_data": formatted,
                "annotations": [],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --------- 模式验证合并占位 ---------
@router.post("/merge-valid-patterns")
async def merge_valid_patterns():
    return {"success": False, "message": "占位：未实现合并逻辑"}
