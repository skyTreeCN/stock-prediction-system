"""模式匹配器 - 程序化匹配经典与 AI 模式（AI 规则放宽版）"""

import json
from typing import List, Dict, Optional

import numpy as np
import pandas as pd


def load_classic_patterns(pattern_file: str = "classic_patterns.json") -> List[Dict]:
    """加载经典模式定义"""
    with open(pattern_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["patterns"]


def match_classic_patterns(kline_data: List[Dict], patterns: List[Dict]) -> List[Dict]:
    """匹配经典模式"""
    if len(kline_data) < 5:
        return []

    df = pd.DataFrame(kline_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    window_size = min(20, len(df))
    min_periods = min(5, len(df))
    df["avg_volume"] = df["volume"].rolling(window=window_size, min_periods=min_periods).mean()
    df["volume_ratio"] = df["volume"] / df["avg_volume"]
    df["pct_change"] = df["close"].pct_change()

    matched = []
    for pattern in patterns:
        if not pattern.get("is_active", True):
            continue
        pid = pattern.get("pattern_id")
        if pid == "P001":
            result = _match_consolidation_breakout(df, pattern)
        elif pid == "P002":
            result = _match_v_reversal(df, pattern)
        elif pid == "P003":
            result = _match_continuous_rise(df, pattern)
        else:
            continue
        if result:
            matched.append(result)
    return matched


def match_ai_patterns(kline_data: List[Dict], patterns: List[Dict]) -> List[Dict]:
    """
    匹配 AI 模式（当前支持 AI000/AI001 的粗略规则）
    再次放宽阈值，先确保有命中，再逐步收紧
    """
    if len(kline_data) < 10:
        return []
    df = pd.DataFrame(kline_data)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df["pct_change"] = df["close"].pct_change()
    df["avg_volume"] = df["volume"].rolling(window=min(20, len(df)), min_periods=3).mean()
    df["volume_ratio"] = df["volume"] / df["avg_volume"]

    matched = []
    for p in patterns:
        if p.get("pattern_type") != "ai_discovered" or not p.get("is_active", True):
            continue
        pid = p.get("pattern_id")
        if pid == "AI000" and _match_ai000(df, p):
            matched.append({"pattern_id": pid, "pattern_name": p["pattern_name"], "confidence": 0.5})
        elif pid == "AI001" and _match_ai001(df, p):
            matched.append({"pattern_id": pid, "pattern_name": p["pattern_name"], "confidence": 0.5})
    return matched


def match_all_patterns(kline_data: List[Dict], patterns: List[Dict]) -> List[Dict]:
    """同时匹配经典与 AI 模式"""
    classics = [p for p in patterns if p.get("pattern_type", "").startswith("classic") or p.get("pattern_id", "").startswith("P")]
    ai = [p for p in patterns if p.get("pattern_type") == "ai_discovered" or p.get("pattern_id", "").startswith("AI")]
    return match_classic_patterns(kline_data, classics) + match_ai_patterns(kline_data, ai)


# ---------- 经典模式 ----------
def _match_consolidation_breakout(df: pd.DataFrame, pattern: Dict) -> Optional[Dict]:
    params = pattern["parameters"]
    last_idx = len(df) - 1
    if last_idx < 5:
        return None
    breakout_day = None
    for i in range(last_idx, max(last_idx - 3, 0), -1):
        day = df.iloc[i]
        if day["volume_ratio"] >= params["breakout_volume_ratio"]["min"] and day["pct_change"] >= params["breakout_rise"]["min"]:
            breakout_day = i
            break
    if breakout_day is None:
        return None
    consolidation_found = False
    matched_days = 0
    for days in range(params["consolidation_days"]["min"], min(params["consolidation_days"]["max"] + 1, breakout_day)):
        start_idx = breakout_day - days
        if start_idx < 0:
            break
        period = df.iloc[start_idx:breakout_day]
        price_range = (period["high"].max() - period["low"].min()) / period["close"].mean()
        if price_range > params["price_range_during_consolidation"]["max"]:
            continue
        avg_volume_ratio = period["volume_ratio"].mean()
        if avg_volume_ratio <= params["volume_shrink_ratio"]["max"]:
            consolidation_found = True
            matched_days = days
            break
    if not consolidation_found:
        return None
    return {
        "pattern_id": pattern["pattern_id"],
        "pattern_name": pattern["pattern_name"],
        "confidence": 0.85,
        "match_details": f"横盘{matched_days}天后放量突破",
    }


def _match_v_reversal(df: pd.DataFrame, pattern: Dict) -> Optional[Dict]:
    params = pattern["parameters"]
    last_idx = len(df) - 1
    if last_idx < 4:
        return None
    bottom_idx = df["close"].idxmin()
    if bottom_idx >= last_idx - 1 or bottom_idx < 1:
        return None
    pre_bottom = df.iloc[: bottom_idx + 1]
    peak_idx = pre_bottom["close"].idxmax()
    decline_amplitude = (df["close"].iloc[peak_idx] - df["close"].iloc[bottom_idx]) / df["close"].iloc[peak_idx]
    if decline_amplitude < params["decline_amplitude"]["min"]:
        return None
    rebound_rise = (df["close"].iloc[last_idx] - df["close"].iloc[bottom_idx]) / df["close"].iloc[bottom_idx]
    if rebound_rise < params["rebound_rise"]["min"]:
        return None
    rebound_days = last_idx - bottom_idx
    if rebound_days < params["rebound_days"]["min"]:
        return None
    return {
        "pattern_id": pattern["pattern_id"],
        "pattern_name": pattern["pattern_name"],
        "confidence": 0.80,
        "match_details": f"V型反转: 下跌{decline_amplitude*100:.1f}%后反弹{rebound_rise*100:.1f}%",
    }


def _match_continuous_rise(df: pd.DataFrame, pattern: Dict) -> Optional[Dict]:
    params = pattern["parameters"]
    last_idx = len(df) - 1
    if last_idx < 5:
        return None
    continuous_days = 0
    total_rise = 0
    has_pullback = False
    volume_ratios = []
    for i in range(last_idx, max(0, last_idx - 10), -1):
        day = df.iloc[i]
        if day["pct_change"] < params["daily_rise"]["min"]:
            if day["pct_change"] < -0.01:
                has_pullback = True
            break
        continuous_days += 1
        total_rise += day["pct_change"]
        volume_ratios.append(day["volume_ratio"])
    if continuous_days < params["continuous_days"]["min"]:
        return None
    if total_rise < params["total_rise"]["min"]:
        return None
    if params.get("no_pullback", True) and has_pullback:
        return None
    if volume_ratios:
        days_above_threshold = sum(1 for v in volume_ratios if v >= params["daily_volume_ratio"]["min"])
        if days_above_threshold < len(volume_ratios) * 0.6:
            return None
        if "max_volume_ratio" in params and max(volume_ratios) < params["max_volume_ratio"]["min"]:
            return None
    return {
        "pattern_id": pattern["pattern_id"],
        "pattern_name": pattern["pattern_name"],
        "confidence": 0.90,
        "match_details": f"连续{continuous_days}天放量上涨",
    }


# ---------- AI 模式（放宽规则） ----------
def _match_ai000(df: pd.DataFrame, pattern: Dict) -> bool:
    params = pattern.get("parameters", {})
    obs = params.get("observation_period", 30)
    base_days = params.get("base_volume_days", 4)
    vol_mult = max(1.2, params.get("breakout_volume_multiplier", 2.0))
    price_inc = max(0.03, params.get("price_increase_threshold", 0.08))
    cons_range = max(0.20, params.get("consolidation_range", 0.12))
    momentum_th = max(0.03, params.get("momentum_threshold", 0.1))

    if len(df) < obs + base_days:
        return False
    sub = df.tail(obs + base_days).copy()
    sub["rolling_vol"] = sub["volume"].rolling(base_days, min_periods=base_days).mean()
    sub["rolling_high"] = sub["close"].rolling(obs, min_periods=5).max()
    for i in range(len(sub) - 1, base_days - 1, -1):
        row = sub.iloc[i]
        base_vol = sub["rolling_vol"].iloc[i]
        prev_high = sub["rolling_high"].iloc[i - 1] if i > 0 else row["close"]
        if base_vol == 0 or prev_high <= 0:
            continue
        if row["volume"] >= base_vol * vol_mult and (row["close"] - prev_high) / prev_high >= price_inc:
            window_start = max(0, i - obs)
            period = sub.iloc[window_start:i]
            if len(period) < 5:
                continue
            price_range = (period["high"].max() - period["low"].min()) / period["close"].mean()
            if price_range > cons_range:
                continue
            post = sub.iloc[i : i + 5]
            total_rise = (post["close"].iloc[-1] - post["close"].iloc[0]) / post["close"].iloc[0] if len(post) > 1 else 0
            if total_rise < -0.05:
                continue
            overall_rise = (sub["close"].iloc[-1] - sub["close"].iloc[0]) / sub["close"].iloc[0]
            if overall_rise < momentum_th:
                continue
            return True
    return False


def _match_ai001(df: pd.DataFrame, pattern: Dict) -> bool:
    params = pattern.get("parameters", {})
    vol_th = params.get("volatility_threshold", 0.15)
    vol_range = params.get("volume_change_range", [0.5, 1.5])
    mom_range = params.get("momentum_range", [0.0, 0.10])
    cons_days = params.get("consolidation_days", [5, 20])
    final_vol_inc = params.get("final_day_volume_increase", 1.0)
    price_comp = params.get("price_range_compression", 0.30)
    breakthrough = params.get("breakthrough_amplitude", 0.003)

    if len(df) < cons_days[1] + 1:
        return False
    sub = df.tail(cons_days[1] + 5).copy()
    prices = sub["close"]
    if prices.std() / prices.mean() > vol_th:
        return False
    vol_mean = sub["volume"].mean()
    if vol_mean <= 0:
        return False
    vol_ratio_range = (sub["volume"] / vol_mean).between(vol_range[0], vol_range[1]).mean()
    if vol_ratio_range < 0.5:  # 更宽松
        return False

    for win in range(cons_days[0], cons_days[1] + 1):
        if len(sub) < win + 1:
            continue
        base = sub.iloc[-(win + 1) : -1]
        price_range = (base["high"].max() - base["low"].min()) / base["close"].mean()
        if price_range > price_comp:
            continue
        last = sub.iloc[-1]
        if last["volume"] < vol_mean * final_vol_inc:
            continue
        prev_high = base["high"].max()
        if prev_high <= 0:
            continue
        if (last["close"] - prev_high) / prev_high < breakthrough:
            continue
        total_rise = (last["close"] - base["close"].iloc[0]) / base["close"].iloc[0]
        if not (mom_range[0] <= total_rise <= mom_range[1]):
            continue
        return True
    return False


def pre_screen_stocks(stocks_kline_data: Dict[str, List[Dict]], patterns: List[Dict]) -> List[str]:
    """程序化预选股票"""
    candidates = []
    for stock_code, kline_data in stocks_kline_data.items():
        matched = match_all_patterns(kline_data, patterns)
        if len(matched) >= 1:
            candidates.append(stock_code)
    return candidates
