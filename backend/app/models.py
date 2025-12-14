from pydantic import BaseModel
from datetime import date
from typing import List, Optional

class StockData(BaseModel):
    """股票K线数据模型"""
    code: str  # 股票代码
    name: str  # 股票名称
    date: date  # 日期
    open: float  # 开盘价
    close: float  # 收盘价
    high: float  # 最高价
    low: float  # 最低价
    volume: float  # 成交量

class StockPrediction(BaseModel):
    """股票预测结果模型"""
    code: str
    name: str
    probability: float  # 上涨概率
    reason: str  # 原因说明
    current_price: float  # 当前价格
    last_date: str  # 数据最后日期

class PatternAnnotationRegion(BaseModel):
    """区域标注（用于横盘期、上涨期等）"""
    start_index: int  # 相对于kline_data末尾的偏移 (-3 = 倒数第3天)
    end_index: int  # 相对于末尾的偏移 (-1 = 最后一天)
    label: str  # "横盘整理期"
    type: str  # 'consolidation' | 'rise' | 'decline' | 'breakout'
    color: Optional[str] = None

class PatternAnnotationPoint(BaseModel):
    """点标注（用于突破点、放量日等）"""
    index: int  # 相对于末尾的偏移
    label: str  # "放量突破"
    type: str  # 'volume_spike' | 'price_breakout' | 'pattern_signal'
    position: str  # 'above' | 'below' | 'volume'

class PatternAnnotationLine(BaseModel):
    """线标注（用于压力位、支撑位等）"""
    price: float  # 价格水平
    label: str  # "前期高点压力位"
    type: str  # 'resistance' | 'support'
    style: str  # 'solid' | 'dashed'

class PatternAnnotation(BaseModel):
    """模式标注元数据"""
    regions: Optional[List[PatternAnnotationRegion]] = []
    points: Optional[List[PatternAnnotationPoint]] = []
    lines: Optional[List[PatternAnnotationLine]] = []

class AnalysisPattern(BaseModel):
    """上涨模式"""
    pattern_name: str
    description: str
    characteristics: List[str]
    example_stock_code: Optional[str] = None
    key_days: Optional[str] = ""
    key_features: Optional[List[str]] = []
    kline_data: Optional[List[dict]] = []
    annotations: Optional[PatternAnnotation] = None  # 新增：标注元数据

class FetchDataRequest(BaseModel):
    """数据获取请求"""
    years: Optional[int] = 5

class AnalyzeRequest(BaseModel):
    """分析请求"""
    pattern_count: Optional[int] = 2000  # 提取多少个上涨案例

class TrainingRequest(BaseModel):
    """训练请求"""
    sample_count: Optional[int] = 300  # 训练样本数量
