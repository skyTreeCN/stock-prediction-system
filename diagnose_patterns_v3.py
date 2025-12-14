"""诊断脚本V3：最终优化分析"""
import json
import pandas as pd
import numpy as np
from collections import defaultdict

def load_samples(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_sample(kline_data):
    if len(kline_data) < 5:
        return None

    df = pd.DataFrame(kline_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    window_size = min(20, len(df))
    min_periods = min(5, len(df))
    df['avg_volume'] = df['volume'].rolling(window=window_size, min_periods=min_periods).mean()
    df['volume_ratio'] = df['volume'] / df['avg_volume']
    df['pct_change'] = df['close'].pct_change()

    return df

def match_p001_v4(df, params):
    """
    P001 V4: 更智能的横盘突破检测

    核心逻辑改进：
    1. 不要求最后一天同时放量+上涨，只要最近3天有放量突破即可
    2. 横盘检测使用滑动窗口
    3. 引入"相对突破"概念
    """
    last_idx = len(df) - 1
    if last_idx < 5:
        return False, {}

    # 检查最近3天是否有放量突破
    breakout_found = False
    for i in range(last_idx, max(last_idx-3, 0), -1):
        day = df.iloc[i]
        if day['volume_ratio'] >= params['breakout_volume_ratio']['min'] and \
           day['pct_change'] >= params['breakout_rise']['min']:
            breakout_found = True
            break

    if not breakout_found:
        return False, {'issue': 'no_breakout'}

    # 找横盘期（在突破前）
    for days in range(params['consolidation_days']['min'],
                      min(params['consolidation_days']['max'] + 1, i)):
        start_idx = i - days
        if start_idx < 0:
            break
        consolidation_period = df.iloc[start_idx:i]

        price_range = (consolidation_period['high'].max() - consolidation_period['low'].min()) / consolidation_period['close'].mean()
        avg_volume_ratio = consolidation_period['volume_ratio'].mean()

        if price_range <= params['price_range_during_consolidation']['max'] and \
           avg_volume_ratio <= params['volume_shrink_ratio']['max']:
            return True, {'consolidation_days': days, 'breakout_day': i}

    return False, {'issue': 'no_consolidation'}

def match_p002_v4(df, params):
    """
    P002 V4: 更灵活的V型反转检测

    核心逻辑改进：
    1. 放宽反弹天数上限（适应数据长度）
    2. 使用相对下跌幅度（从局部高点到底部）
    3. 不强制要求放量，改为可选加分项
    """
    last_idx = len(df) - 1
    if last_idx < 5:
        return False, {}

    # 找底部（整个数据范围内的最低点）
    bottom_idx = df['close'].idxmin()

    # 底部位置检查
    if bottom_idx >= last_idx - 1 or bottom_idx < 1:
        return False, {'issue': 'bottom_position'}

    # 找底部前的局部高点
    pre_bottom = df.iloc[:bottom_idx + 1]
    peak_idx = pre_bottom['close'].idxmax()

    # 计算下跌幅度（从峰值到底部）
    decline_amplitude = (df['close'].iloc[peak_idx] - df['close'].iloc[bottom_idx]) / df['close'].iloc[peak_idx]

    if decline_amplitude < params['decline_amplitude']['min']:
        return False, {'issue': 'decline_too_small', 'decline': decline_amplitude}

    # 计算反弹幅度
    rebound_rise = (df['close'].iloc[last_idx] - df['close'].iloc[bottom_idx]) / df['close'].iloc[bottom_idx]

    if rebound_rise < params['rebound_rise']['min']:
        return False, {'issue': 'rebound_too_small', 'rebound': rebound_rise}

    # 反弹天数
    rebound_days = last_idx - bottom_idx

    if rebound_days < params['rebound_days']['min']:
        return False, {'issue': 'rebound_days_short'}

    # 不再强制检查反弹天数上限和放量

    return True, {
        'decline': decline_amplitude,
        'rebound': rebound_rise,
        'rebound_days': rebound_days,
        'bottom_idx': bottom_idx
    }

def match_p003_original(df, params):
    """保持P003原有逻辑"""
    last_idx = len(df) - 1
    if last_idx < 5:
        return False, {}

    continuous_days = 0
    total_rise = 0
    has_pullback = False
    volume_ratios = []

    for i in range(last_idx, max(0, last_idx - 10), -1):
        day = df.iloc[i]

        if day['pct_change'] < params['daily_rise']['min']:
            if day['pct_change'] < -0.01:
                has_pullback = True
            break

        continuous_days += 1
        total_rise += day['pct_change']
        volume_ratios.append(day['volume_ratio'])

    if continuous_days < params['continuous_days']['min']:
        return False, {}

    if total_rise < params['total_rise']['min']:
        return False, {}

    if params.get('no_pullback', True) and has_pullback:
        return False, {}

    if volume_ratios:
        days_above_threshold = sum(1 for v in volume_ratios if v >= params['daily_volume_ratio']['min'])
        if days_above_threshold < len(volume_ratios) * 0.6:
            return False, {}

        if 'max_volume_ratio' in params:
            if max(volume_ratios) < params['max_volume_ratio']['min']:
                return False, {}

    return True, {'continuous_days': continuous_days, 'total_rise': total_rise}

def main():
    print("Loading samples...")
    special_samples = load_samples('special_samples.json')
    classic_samples = load_samples('classic_samples_stat.json')

    total_samples = 282

    # 最优参数配置
    p001_optimal = {
        'consolidation_days': {'min': 2, 'max': 6},
        'volume_shrink_ratio': {'max': 1.5},
        'breakout_volume_ratio': {'min': 1.2},
        'price_range_during_consolidation': {'max': 0.12},
        'breakout_rise': {'min': 0.015}
    }

    p002_optimal = {
        'decline_amplitude': {'min': 0.02},  # 2%下跌即可
        'rebound_rise': {'min': 0.03},  # 3%反弹
        'rebound_days': {'min': 2}  # 至少2天反弹
    }

    p003_params = {
        'continuous_days': {'min': 3},
        'daily_volume_ratio': {'min': 1.0},
        'max_volume_ratio': {'min': 1.5},
        'daily_rise': {'min': 0.01},
        'total_rise': {'min': 0.05},
        'no_pullback': True
    }

    # ============ 全面测试 ============
    print("\n" + "="*80)
    print("FINAL OPTIMAL MATCHING RESULTS")
    print("="*80)

    p001_matches = set()
    p002_matches = set()
    p003_matches = set()

    # 已经匹配P003的样本
    for s in classic_samples:
        p003_matches.add(s['sample_id'])

    # 测试P001和P002
    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        sid = sample['sample_id']

        match_p001, _ = match_p001_v4(df, p001_optimal)
        match_p002, _ = match_p002_v4(df, p002_optimal)
        match_p003, _ = match_p003_original(df, p003_params)

        if match_p001:
            p001_matches.add(sid)
        if match_p002:
            p002_matches.add(sid)
        if match_p003:
            p003_matches.add(sid)

    # 计算覆盖
    all_classic = p001_matches | p002_matches | p003_matches
    p001_only = p001_matches - p002_matches - p003_matches
    p002_only = p002_matches - p001_matches - p003_matches
    p003_only = p003_matches - p001_matches - p002_matches

    print(f"\nPattern Coverage:")
    print(f"  P001 (Consolidation Breakout): {len(p001_matches)} samples")
    print(f"  P002 (V-Reversal): {len(p002_matches)} samples")
    print(f"  P003 (Continuous Rise): {len(p003_matches)} samples")

    print(f"\nUnique matches:")
    print(f"  P001 only: {len(p001_only)}")
    print(f"  P002 only: {len(p002_only)}")
    print(f"  P003 only: {len(p003_only)}")

    print(f"\nOverlap:")
    print(f"  P001 & P002: {len(p001_matches & p002_matches)}")
    print(f"  P001 & P003: {len(p001_matches & p003_matches)}")
    print(f"  P002 & P003: {len(p002_matches & p003_matches)}")

    print(f"\nTotal Coverage:")
    print(f"  Any classic pattern: {len(all_classic)}/{total_samples} ({len(all_classic)/total_samples*100:.1f}%)")
    print(f"  Remaining for AI: {total_samples - len(all_classic)}/{total_samples} ({(total_samples - len(all_classic))/total_samples*100:.1f}%)")

    # ============ 成本分析 ============
    print("\n" + "="*80)
    print("COST ANALYSIS")
    print("="*80)

    ai_cost_per_sample = 3.30 / total_samples  # 假设原始$3.30是处理所有样本

    # 当前方案
    current_classic = 16  # 只有P003
    current_ai = total_samples - current_classic
    current_cost = current_ai * ai_cost_per_sample

    # 优化方案
    optimized_classic = len(all_classic)
    optimized_ai = total_samples - optimized_classic
    optimized_cost = optimized_ai * ai_cost_per_sample

    print(f"\nCurrent approach (P003 only):")
    print(f"  Classic samples: {current_classic} ({current_classic/total_samples*100:.1f}%)")
    print(f"  AI samples: {current_ai} ({current_ai/total_samples*100:.1f}%)")
    print(f"  Estimated cost: ${current_cost:.2f}")

    print(f"\nOptimized approach (P001+P002+P003):")
    print(f"  Classic samples: {optimized_classic} ({optimized_classic/total_samples*100:.1f}%)")
    print(f"  AI samples: {optimized_ai} ({optimized_ai/total_samples*100:.1f}%)")
    print(f"  Estimated cost: ${optimized_cost:.2f}")

    print(f"\nSavings:")
    print(f"  Cost reduction: ${current_cost - optimized_cost:.2f}")
    print(f"  Percentage saved: {(current_cost - optimized_cost)/current_cost*100:.1f}%")

    # ============ 推荐的参数配置 ============
    print("\n" + "="*80)
    print("RECOMMENDED PARAMETER CONFIGURATION")
    print("="*80)

    print("""
P001 - Consolidation Breakout (Optimized for 10-14 day data):
{
  "consolidation_days": {"min": 2, "max": 6},
  "volume_shrink_ratio": {"max": 1.5},
  "breakout_volume_ratio": {"min": 1.2},
  "price_range_during_consolidation": {"max": 0.12},
  "breakout_rise": {"min": 0.015}
}

Logic changes:
- Remove the 'last_idx < 20' hard limit
- Check last 3 days for breakout (not just last day)
- Allow breakout detection within the window

P002 - V-Reversal (Simplified for short data):
{
  "decline_amplitude": {"min": 0.02},
  "rebound_rise": {"min": 0.03},
  "rebound_days": {"min": 2}
}

Logic changes:
- Remove the 'last_idx < 15' hard limit
- Remove rebound_days max limit
- Remove mandatory volume requirement
- Find local peak before bottom for decline calculation
- Simplify to: peak -> bottom -> current (V shape)

P003 - Continuous Rise (Keep current):
{
  "continuous_days": {"min": 3},
  "daily_volume_ratio": {"min": 1.0},
  "max_volume_ratio": {"min": 1.5},
  "daily_rise": {"min": 0.01},
  "total_rise": {"min": 0.05},
  "no_pullback": true
}
""")

if __name__ == '__main__':
    main()
