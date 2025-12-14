"""模式匹配器 - 程序化匹配经典上涨模式"""
import json
from typing import List, Dict, Optional
import pandas as pd


def load_classic_patterns(pattern_file: str = "classic_patterns.json") -> List[Dict]:
    """加载经典模式定义"""
    with open(pattern_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['patterns']


def match_classic_patterns(kline_data: List[Dict], patterns: List[Dict]) -> List[Dict]:
    """匹配经典模式

    Args:
        kline_data: K线数据列表，每项包含 {date, open, high, low, close, volume}
        patterns: 模式定义列表

    Returns:
        匹配结果列表 [{pattern_id, pattern_name, confidence, match_details}, ...]
    """
    if len(kline_data) < 5:  # Minimum 5 days for basic analysis
        return []

    # 转换为DataFrame便于计算
    df = pd.DataFrame(kline_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 计算成交量平均值（使用可用的所有数据，最少5天）
    window_size = min(20, len(df))
    min_periods = min(5, len(df))
    df['avg_volume'] = df['volume'].rolling(window=window_size, min_periods=min_periods).mean()
    df['volume_ratio'] = df['volume'] / df['avg_volume']

    # 计算涨跌幅（日间涨跌，即今日收盘 vs 昨日收盘）
    df['pct_change'] = df['close'].pct_change()

    matched = []

    for pattern in patterns:
        if not pattern.get('is_active', True):
            continue

        pattern_id = pattern['pattern_id']

        if pattern_id == 'P001':
            result = _match_consolidation_breakout(df, pattern)
        elif pattern_id == 'P002':
            result = _match_v_reversal(df, pattern)
        elif pattern_id == 'P003':
            result = _match_continuous_rise(df, pattern)
        else:
            continue

        if result:
            matched.append(result)

    return matched


def _match_consolidation_breakout(df: pd.DataFrame, pattern: Dict) -> Optional[Dict]:
    """匹配P001：缩量震荡后放量突破"""
    params = pattern['parameters']
    last_idx = len(df) - 1

    # 最少需要6天数据
    if last_idx < 5:
        return None

    # 检查最近3天是否有放量突破（不仅仅是最后一天）
    breakout_day = None
    for i in range(last_idx, max(last_idx - 3, 0), -1):
        day = df.iloc[i]
        if day['volume_ratio'] >= params['breakout_volume_ratio']['min'] and \
           day['pct_change'] >= params['breakout_rise']['min']:
            breakout_day = i
            break

    if breakout_day is None:
        return None

    # 在突破日之前寻找横盘期
    consolidation_found = False
    matched_days = 0
    for days in range(params['consolidation_days']['min'],
                      min(params['consolidation_days']['max'] + 1, breakout_day)):
        start_idx = breakout_day - days
        if start_idx < 0:
            break

        consolidation_period = df.iloc[start_idx:breakout_day]

        # 检查横盘期波动
        price_range = (consolidation_period['high'].max() - consolidation_period['low'].min()) / consolidation_period['close'].mean()
        if price_range > params['price_range_during_consolidation']['max']:
            continue

        # 检查横盘期成交量相对平稳
        avg_volume_ratio = consolidation_period['volume_ratio'].mean()
        if avg_volume_ratio <= params['volume_shrink_ratio']['max']:
            consolidation_found = True
            matched_days = days
            break

    if not consolidation_found:
        return None

    return {
        'pattern_id': pattern['pattern_id'],
        'pattern_name': pattern['pattern_name'],
        'confidence': 0.85,
        'match_details': f"横盘{matched_days}天后放量突破"
    }


def _match_v_reversal(df: pd.DataFrame, pattern: Dict) -> Optional[Dict]:
    """匹配P002：V型反转放量上攻"""
    params = pattern['parameters']
    last_idx = len(df) - 1

    # 最少需要5天数据
    if last_idx < 4:
        return None

    # 在整个数据范围内找底部
    bottom_idx = df['close'].idxmin()

    # 底部位置检查
    if bottom_idx >= last_idx - 1 or bottom_idx < 1:
        return None

    # 找底部前的局部高点
    pre_bottom = df.iloc[:bottom_idx + 1]
    peak_idx = pre_bottom['close'].idxmax()

    # 计算下跌幅度（从局部峰值到底部）
    decline_amplitude = (df['close'].iloc[peak_idx] - df['close'].iloc[bottom_idx]) / \
                        df['close'].iloc[peak_idx]

    if decline_amplitude < params['decline_amplitude']['min']:
        return None

    # 计算反弹幅度
    rebound_rise = (df['close'].iloc[last_idx] - df['close'].iloc[bottom_idx]) / \
                   df['close'].iloc[bottom_idx]

    if rebound_rise < params['rebound_rise']['min']:
        return None

    # 检查最小反弹天数
    rebound_days = last_idx - bottom_idx
    if rebound_days < params['rebound_days']['min']:
        return None

    return {
        'pattern_id': pattern['pattern_id'],
        'pattern_name': pattern['pattern_name'],
        'confidence': 0.80,
        'match_details': f"V型反转: 下跌{decline_amplitude*100:.1f}%后反弹{rebound_rise*100:.1f}%"
    }


def _match_continuous_rise(df: pd.DataFrame, pattern: Dict) -> Optional[Dict]:
    """匹配P003：连续放量上攻"""
    params = pattern['parameters']
    last_idx = len(df) - 1

    if last_idx < 5:
        return None

    # 从最后一天往前找连续上涨
    continuous_days = 0
    total_rise = 0
    has_pullback = False
    volume_ratios = []

    for i in range(last_idx, max(0, last_idx - 10), -1):
        day = df.iloc[i]

        # 检查当日涨幅
        if day['pct_change'] < params['daily_rise']['min']:
            if day['pct_change'] < -0.01:  # 单日跌幅>1%
                has_pullback = True
            break

        continuous_days += 1
        total_rise += day['pct_change']
        volume_ratios.append(day['volume_ratio'])

    if continuous_days < params['continuous_days']['min']:
        return None

    if total_rise < params['total_rise']['min']:
        return None

    if params.get('no_pullback', True) and has_pullback:
        return None

    # 检查成交量要求：大部分日期>daily_volume_ratio，最大值>max_volume_ratio
    if volume_ratios:
        days_above_threshold = sum(1 for v in volume_ratios if v >= params['daily_volume_ratio']['min'])
        if days_above_threshold < len(volume_ratios) * 0.6:  # 至少60%的日期满足
            return None

        if 'max_volume_ratio' in params:
            if max(volume_ratios) < params['max_volume_ratio']['min']:
                return None

    return {
        'pattern_id': pattern['pattern_id'],
        'pattern_name': pattern['pattern_name'],
        'confidence': 0.90,
        'match_details': f"连续{continuous_days}天放量上涨"
    }


def pre_screen_stocks(stocks_kline_data: Dict[str, List[Dict]],
                     patterns: List[Dict]) -> List[str]:
    """程序预筛选股票（用于场景二）

    Args:
        stocks_kline_data: {stock_code: kline_data_list}
        patterns: 模式定义列表

    Returns:
        符合条件的股票代码列表
    """
    candidates = []

    for stock_code, kline_data in stocks_kline_data.items():
        matched = match_classic_patterns(kline_data, patterns)
        if len(matched) >= 1:  # 至少匹配1个模式
            candidates.append(stock_code)

    return candidates
