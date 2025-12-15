from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging
from typing import List

from .database import StockDatabase
from .data_fetcher import StockDataFetcher
from .data_fetcher_baostock import BaoStockDataFetcher
from .data_fetcher_tushare import TushareDataFetcher
from .data_fetcher_akshare import AkShareDataFetcher
from .data_fetcher_yfinance import YahooFinanceDataFetcher
from .analyzer import StockAnalyzer
from .config import get_sample_size, get_rise_threshold
from .data_fetcher_akshare import fetch_sse_component_stocks
from .models import (
    StockPrediction,
    FetchDataRequest,
    AnalyzeRequest,
    AnalysisPattern,
    TrainingRequest
)
from .routers import pattern_training

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('logs/app.log', encoding='utf-8') if os.path.exists('logs') or os.makedirs('logs', exist_ok=True) else logging.StreamHandler()
    ]
)

# 设置不同模块的日志级别
logging.getLogger('uvicorn').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('anthropic').setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info("股票预测系统API启动中...")

# 加载环境变量
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

app = FastAPI(title="股票预测系统API")

# 注册路由
app.include_router(pattern_training.router)

# 允许跨域请求（前端访问）
# 从环境变量读取允许的源，默认仅localhost
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:3002"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 明确指定允许的方法
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With"
    ],  # 明确指定允许的headers
    max_age=3600,  # 预检请求缓存1小时
)

logger.info(f"CORS配置: 允许的源 = {ALLOWED_ORIGINS}")

# 初始化组件
# 优先读取环境变量 DATABASE_PATH；若未设置，则定位到仓库根目录下的 data/stocks.db，避免工作目录差异导致读取空库
default_db_path = os.getenv("DATABASE_PATH")
if not default_db_path:
    default_db_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "stocks.db")
    )

db = StockDatabase(default_db_path)

# 验证 API Key 并初始化 Analyzer（允许无密钥启动）
api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    logger.info(f"✅ API Key已加载: {api_key[:20]}...")
    logger.info("   AI功能已启用")
else:
    logger.warning("⚠️  未设置ANTHROPIC_API_KEY环境变量")
    logger.warning("   系统将以基础模式运行，AI相关功能将不可用")
    logger.warning("   基础功能（数据抓取、股票池更新、统计）仍可正常使用")

# 注入数据库依赖，允许无API Key启动
analyzer = StockAnalyzer(api_key=api_key, db=db)

# 全局状态
task_status = {
    "fetch_data": {"running": False, "progress": 0, "message": ""},
    "analyze": {"running": False, "progress": 0, "message": ""},
    "predict": {"running": False, "progress": 0, "message": ""}
}


@app.get("/")
async def root():
    """健康检查"""
    return {"status": "ok", "message": "股票预测系统API运行中"}


@app.get("/api/statistics")
async def get_statistics():
    """获取数据统计信息"""
    try:
        stats = db.get_data_statistics()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fetch-data")
async def fetch_data(request: FetchDataRequest, background_tasks: BackgroundTasks):
    """
    区域1：获取股票数据
    后台任务方式，避免超时
    """
    if task_status["fetch_data"]["running"]:
        return {"success": False, "message": "数据获取任务正在运行中"}

    def fetch_task(years: int):
        try:
            task_status["fetch_data"]["running"] = True
            task_status["fetch_data"]["message"] = "开始获取数据..."

            # 创建数据获取器 - 测试Yahoo Finance
            fetcher = YahooFinanceDataFetcher(years=years)  # Yahoo Finance真实数据
            # fetcher = AkShareDataFetcher(years=years)  # AkShare免费数据（连接问题）
            # fetcher = TushareDataFetcher(years=years)  # Tushare真实数据（需要积分）
            # fetcher = BaoStockDataFetcher(years=years)  # BaoStock真实数据（连接问题）
            # fetcher = StockDataFetcher(years=years)  # 模拟数据（离线可用）

            task_status["fetch_data"]["message"] = "从股票池获取股票列表..."
            task_status["fetch_data"]["progress"] = 10

            # 从股票池获取股票代码
            pool_stocks = db.get_stock_pool(active_only=True)
            if not pool_stocks or len(pool_stocks) == 0:
                task_status["fetch_data"]["message"] = "股票池为空，请先更新股票池"
                task_status["fetch_data"]["progress"] = 0
                return

            # 转换为Yahoo格式：6开头加.SS，0/3开头加.SZ
            stock_codes = []
            for stock in pool_stocks:
                code = stock.get('code', '')
                if code.startswith('6'):
                    stock_codes.append(f"{code}.SS")
                elif code.startswith(('0', '3')):
                    stock_codes.append(f"{code}.SZ")

            # 手动抓取股票数据（支持增量更新）
            stock_data_list = []
            incremental_count = 0
            full_fetch_count = 0

            for i, code in enumerate(stock_codes, 1):
                # 检查该股票的最后日期
                stock_code_only = code.split('.')[0]  # 去掉.SS/.SZ后缀
                last_date = db.get_stock_last_date(stock_code_only)

                if last_date:
                    # 增量更新：只获取最后日期之后的数据
                    data = fetcher.fetch_stock_data(code, start_from=last_date)
                    incremental_count += 1
                    task_status["fetch_data"]["message"] = f"增量更新 {i}/{len(stock_codes)} ({stock_code_only}, 从{last_date}开始)"
                else:
                    # 全量获取：该股票没有历史数据
                    data = fetcher.fetch_stock_data(code)
                    full_fetch_count += 1
                    task_status["fetch_data"]["message"] = f"全量获取 {i}/{len(stock_codes)} ({stock_code_only}, {years}年数据)"

                if data:
                    stock_data_list.append(data)

                # 更新进度
                progress = 10 + int((i / len(stock_codes)) * 70)
                task_status["fetch_data"]["progress"] = progress

                if i < len(stock_codes):
                    import time
                    time.sleep(0.3)

            if not stock_data_list:
                task_status["fetch_data"]["message"] = "数据获取失败，请检查网络连接"
                task_status["fetch_data"]["progress"] = 0
                return

            task_status["fetch_data"]["message"] = "保存到数据库..."
            task_status["fetch_data"]["progress"] = 80

            # 保存到数据库（需要转换格式）
            for stock_data in stock_data_list:
                db.save_single_stock_data(stock_data)

            # 生成统计信息
            summary = f"成功！"
            if full_fetch_count > 0:
                summary += f"全量获取{full_fetch_count}只股票，"
            if incremental_count > 0:
                summary += f"增量更新{incremental_count}只股票，"
            summary += f"共{len(stock_data_list)}只"

            task_status["fetch_data"]["message"] = summary
            task_status["fetch_data"]["progress"] = 100

        except Exception as e:
            logger.error(f"数据获取任务失败: {str(e)}", exc_info=True)
            task_status["fetch_data"]["message"] = f"错误: {str(e)}"
            task_status["fetch_data"]["progress"] = 0
        finally:
            task_status["fetch_data"]["running"] = False

    background_tasks.add_task(fetch_task, request.years)

    return {
        "success": True,
        "message": "数据获取任务已启动，请查看任务状态"
    }


@app.get("/api/task-status/{task_name}")
async def get_task_status(task_name: str):
    """获取任务状态"""
    if task_name not in task_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "success": True,
        "data": task_status[task_name]
    }


@app.get("/api/claude-api-statistics")
async def get_claude_api_statistics():
    """获取Claude API调用统计和成本信息"""
    try:
        # 从全局analyzer获取统计（如果存在）
        if 'analyzer' in globals() and analyzer is not None:
            stats = analyzer.get_api_statistics()
            return {
                "success": True,
                "data": stats,
                "message": "API统计信息"
            }
        else:
            return {
                "success": False,
                "message": "分析器未初始化",
                "data": {
                    'total_calls': 0,
                    'total_errors': 0,
                    'success_rate': 0,
                    'input_tokens': 0,
                    'output_tokens': 0,
                    'total_tokens': 0,
                    'estimated_cost_usd': 0.0
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@app.post("/api/analyze")
async def analyze_patterns(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    区域2：分析上涨模式
    使用 Claude AI 分析历史数据，提取上涨模式
    """
    logger.info(f"收到模式分析请求: pattern_count={request.pattern_count}")

    # 检查AI是否可用
    if not analyzer.ai_enabled:
        logger.error("AI功能不可用：未配置ANTHROPIC_API_KEY")
        return {
            "success": False,
            "message": "AI功能不可用：请配置ANTHROPIC_API_KEY环境变量后重启服务"
        }

    if task_status["analyze"]["running"]:
        logger.warning("分析任务正在运行中，拒绝新请求")
        return {"success": False, "message": "分析任务正在运行中"}

    def analyze_task(pattern_count: int):
        try:
            logger.info(f"开始分析任务: pattern_count={pattern_count}")
            task_status["analyze"]["running"] = True
            task_status["analyze"]["message"] = "获取历史上涨样本..."
            task_status["analyze"]["progress"] = 20

            # 从配置获取样本量和上涨阈值
            sample_size = get_sample_size()
            rise_threshold = get_rise_threshold()

            # 从数据库获取上涨样本
            samples = db.get_rising_samples(sample_count=sample_size, rise_threshold=rise_threshold)

            if samples.empty:
                task_status["analyze"]["message"] = f"未找到符合条件的样本 (3天后上涨≥{rise_threshold*100}%)"
                return

            task_status["analyze"]["message"] = f"找到{len(samples)}个样本 (上涨≥{rise_threshold*100}%)，正在分析..."
            task_status["analyze"]["progress"] = 40

            # Step1: 使用 Claude 分析
            patterns = analyzer.analyze_rising_patterns(samples)

            if not patterns:
                task_status["analyze"]["message"] = "分析失败"
                return

            task_status["analyze"]["message"] = "验证模式有效性（历史回测）..."
            task_status["analyze"]["progress"] = 60

            # Step2: 历史验证（新功能 - 核心卖点）
            validation_samples = db.get_validation_samples(days_back=30, rise_threshold=rise_threshold)

            if not validation_samples.empty:
                # 使用AI方法验证（精确但有成本）
                # 限制验证样本数量（避免成本过高）
                max_validation = 100  # 最多验证100个样本
                if len(validation_samples) > max_validation:
                    validation_samples = validation_samples.sample(n=max_validation, random_state=42)
                    print(f"   💡 验证样本过多，随机抽取{max_validation}个进行AI验证")

                patterns = analyzer.validate_patterns_ai(patterns, validation_samples, rise_threshold)
            else:
                print("   ⚠️  无验证数据，跳过验证步骤")

            task_status["analyze"]["message"] = "保存分析结果..."
            task_status["analyze"]["progress"] = 80

            # 保存模式（包含验证结果）
            db.save_patterns(patterns)

            task_status["analyze"]["message"] = f"成功！识别出{len(patterns)}种模式（已验证）"
            task_status["analyze"]["progress"] = 100
            logger.info(f"分析任务完成: 识别出{len(patterns)}种模式")

        except Exception as e:
            logger.error(f"分析任务失败: {str(e)}", exc_info=True)
            task_status["analyze"]["message"] = f"错误: {str(e)}"
        finally:
            task_status["analyze"]["running"] = False

    background_tasks.add_task(analyze_task, request.pattern_count)

    return {
        "success": True,
        "message": "分析任务已启动"
    }


@app.get("/api/patterns", response_model=List[AnalysisPattern])
async def get_patterns():
    """获取已识别的上涨模式"""
    try:
        patterns = db.get_patterns()
        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predict")
async def predict_stocks(background_tasks: BackgroundTasks):
    """
    区域3：预测股票上涨概率
    根据最近数据和已识别模式进行预测
    """
    # 检查AI是否可用
    if not analyzer.ai_enabled:
        logger.error("AI功能不可用：未配置ANTHROPIC_API_KEY")
        return {
            "success": False,
            "message": "AI功能不可用：请配置ANTHROPIC_API_KEY环境变量后重启服务"
        }

    if task_status["predict"]["running"]:
        return {"success": False, "message": "预测任务正在运行中"}

    def predict_task():
        try:
            task_status["predict"]["running"] = True
            task_status["predict"]["message"] = "获取上涨模式..."
            task_status["predict"]["progress"] = 10

            # 获取已保存的模式
            patterns = db.get_patterns()

            if not patterns:
                task_status["predict"]["message"] = "请先执行数据分析"
                return

            task_status["predict"]["message"] = "获取最近股票数据..."
            task_status["predict"]["progress"] = 30

            # 获取所有股票最近30天的数据
            recent_data = db.get_recent_data_all_stocks(days=30)

            if recent_data.empty:
                task_status["predict"]["message"] = "没有数据"
                return

            task_status["predict"]["message"] = "AI预测中..."
            task_status["predict"]["progress"] = 50

            # 使用 Claude 预测
            predictions = analyzer.predict_stock_probability(recent_data, patterns)

            task_status["predict"]["message"] = f"完成！找到{len(predictions)}只潜力股票"
            task_status["predict"]["progress"] = 100

            # 保存预测结果到全局变量（简化版，生产环境应该存数据库）
            task_status["predict"]["result"] = predictions

        except Exception as e:
            logger.error(f"预测任务失败: {str(e)}", exc_info=True)
            task_status["predict"]["message"] = f"错误: {str(e)}"
            task_status["predict"]["progress"] = 0
        finally:
            task_status["predict"]["running"] = False

    background_tasks.add_task(predict_task)

    return {
        "success": True,
        "message": "预测任务已启动"
    }


@app.get("/api/predictions", response_model=List[StockPrediction])
async def get_predictions(days: int = 1):
    """获取预测结果

    优先返回内存中的最新预测结果；若无，则从数据库读取最近N天的预测

    Args:
        days: 从数据库读取最近N天的预测（默认1天，即最近一次）
    """
    # 优先返回内存中的结果（刚完成的预测）
    if "result" in task_status["predict"]:
        logger.info("返回内存中的预测结果")
        return task_status["predict"]["result"]

    # 内存中无结果，从数据库读取最近一次预测
    logger.info(f"内存中无预测结果，从数据库读取最近{days}天的预测")
    try:
        predictions_from_db = db.get_predictions(days=days, verified_only=False)

        # 转换为StockPrediction格式
        result = []
        for pred in predictions_from_db:
            result.append({
                'code': pred['stock_code'],
                'name': pred['stock_name'],
                'probability': pred['probability'],
                'reason': pred['reasoning'],
                'current_price': 0.0,  # 历史预测无当前价格
                'last_date': pred['prediction_date']
            })

        logger.info(f"从数据库读取到 {len(result)} 条预测记录")
        return result[:100]  # 返回前100条

    except Exception as e:
        logger.error(f"从数据库读取预测失败: {e}")
        return []


@app.get("/api/stock/{code}/kline")
async def get_stock_kline(code: str, days: int = 90):
    """获取指定股票的K线数据"""
    try:
        df = db.get_stock_data(code, days=days)
        if df.empty:
            return {"code": code, "data": []}

        # 转换为前端需要的格式
        kline_data = []
        for _, row in df.iterrows():
            kline_data.append({
                'date': row['date'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })

        # 按日期正序排列
        kline_data.reverse()

        return {"code": code, "name": df.iloc[0]['name'], "data": kline_data}
    except Exception as e:
        print(f"获取K线数据失败 {code}: {e}")
        return {"code": code, "data": []}


# ===== 股票池管理 API =====

@app.post("/api/stock-pool/update")
async def update_stock_pool(background_tasks: BackgroundTasks):
    """更新股票池（获取上交所成分股）"""
    if task_status.get("update_pool", {}).get("running", False):
        return {"success": False, "message": "股票池更新任务正在运行中"}

    # 初始化任务状态
    if "update_pool" not in task_status:
        task_status["update_pool"] = {"running": False, "progress": 0, "message": ""}

    def update_pool_task():
        try:
            task_status["update_pool"]["running"] = True
            task_status["update_pool"]["message"] = "获取上交所成分股列表..."
            task_status["update_pool"]["progress"] = 20

            # 获取SSE成分股
            stocks = fetch_sse_component_stocks()

            if not stocks:
                task_status["update_pool"]["message"] = "未能获取成分股列表"
                task_status["update_pool"]["progress"] = 0
                return

            task_status["update_pool"]["message"] = f"保存 {len(stocks)} 只股票到股票池..."
            task_status["update_pool"]["progress"] = 60

            # 更新数据库
            db.update_stock_pool(stocks)

            task_status["update_pool"]["message"] = f"成功！股票池已更新（{len(stocks)}只股票）"
            task_status["update_pool"]["progress"] = 100

        except Exception as e:
            logger.error(f"股票池更新任务失败: {str(e)}", exc_info=True)
            task_status["update_pool"]["message"] = f"错误: {str(e)}"
            task_status["update_pool"]["progress"] = 0
        finally:
            task_status["update_pool"]["running"] = False

    background_tasks.add_task(update_pool_task)

    return {
        "success": True,
        "message": "股票池更新任务已启动"
    }


@app.get("/api/stock-pool")
async def get_stock_pool():
    """获取股票池列表"""
    try:
        stocks = db.get_stock_pool(active_only=True)
        return {
            "success": True,
            "data": stocks,
            "count": len(stocks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock-pool/status")
async def get_stock_pool_status():
    """检查股票池状态"""
    try:
        is_empty = db.is_stock_pool_empty()
        pool_count = 0 if is_empty else len(db.get_stock_pool())

        return {
            "success": True,
            "is_empty": is_empty,
            "count": pool_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.get("/api/predictions/history")
async def get_prediction_history(days: int = 30, verified_only: bool = False):
    """获取历史预测记录
    
    Args:
        days: 获取最近N天的预测
        verified_only: 是否只返回已验证的预测
    """
    try:
        predictions = db.get_predictions(days=days, verified_only=verified_only)
        return {
            "success": True,
            "data": predictions,
            "count": len(predictions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/predictions/{prediction_id}/verify")
async def verify_prediction(prediction_id: int, actual_rise: float):
    """验证预测结果
    
    Args:
        prediction_id: 预测ID
        actual_rise: 实际涨幅(如0.08表示8%)
    """
    try:
        from datetime import datetime
        verified_date = datetime.now().strftime('%Y-%m-%d')
        
        db.verify_prediction(prediction_id, actual_rise, verified_date)
        
        return {
            "success": True,
            "message": "预测结果已验证"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
