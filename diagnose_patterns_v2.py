"""诊断脚本V2：基于实际数据限制重新设计匹配逻辑"""
import json
import pandas as pd
import numpy as np
from collections import defaultdict

def load_samples(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def analyze_sample(kline_data):
    """分析单个样本的各项指标"""
    if len(kline_data) < 5:
        return None

    df = pd.DataFrame(kline_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 计算成交量比率 - 使用实际可用的数据
    window_size = min(20, len(df))
    min_periods = min(5, len(df))
    df['avg_volume'] = df['volume'].rolling(window=window_size, min_periods=min_periods).mean()
    df['volume_ratio'] = df['volume'] / df['avg_volume']

    # 计算涨跌幅
    df['pct_change'] = df['close'].pct_change()

    return df

# ============ 改进版P001: 适应10-14天数据 ============
def match_p001_improved(df, params_v1, params_v2):
    """
    改进版P001: 缩量震荡后放量突破

    关键改进：
    1. 移除last_idx < 20的硬编码限制
    2. 调整横盘期要求：2-5天(适应14天数据)
    3. 放宽放量要求：1.2倍起步
    4. 保留核心逻辑：找横盘+突破
    """
    last_idx = len(df) - 1

    if last_idx < 5:  # 最少需要6天数据
        return None, "data_too_short"

    last_day = df.iloc[last_idx]

    # V1参数检查 (当前严格版)
    v1_match = True
    v1_issues = []

    if last_day['volume_ratio'] < params_v1['breakout_volume_ratio']['min']:
        v1_match = False
        v1_issues.append('volume')
    if last_day['pct_change'] < params_v1['breakout_rise']['min']:
        v1_match = False
        v1_issues.append('rise')

    # V2参数检查 (改进宽松版)
    v2_match = True
    v2_issues = []

    if last_day['volume_ratio'] < params_v2['breakout_volume_ratio']['min']:
        v2_match = False
        v2_issues.append('volume')
    if last_day['pct_change'] < params_v2['breakout_rise']['min']:
        v2_match = False
        v2_issues.append('rise')

    # 找横盘期 - V1
    consolidation_v1 = False
    for days in range(params_v1['consolidation_days']['min'],
                      min(params_v1['consolidation_days']['max'] + 1, last_idx)):
        start_idx = last_idx - days
        if start_idx < 0:
            break
        consolidation_period = df.iloc[start_idx:last_idx]

        price_range = (consolidation_period['high'].max() - consolidation_period['low'].min()) / consolidation_period['close'].mean()
        avg_volume_ratio = consolidation_period['volume_ratio'].mean()

        if price_range <= params_v1['price_range_during_consolidation']['max'] and \
           avg_volume_ratio <= params_v1['volume_shrink_ratio']['max']:
            consolidation_v1 = True
            break

    if not consolidation_v1:
        v1_match = False
        v1_issues.append('consolidation')

    # 找横盘期 - V2 (更宽松)
    consolidation_v2 = False
    for days in range(params_v2['consolidation_days']['min'],
                      min(params_v2['consolidation_days']['max'] + 1, last_idx)):
        start_idx = last_idx - days
        if start_idx < 0:
            break
        consolidation_period = df.iloc[start_idx:last_idx]

        price_range = (consolidation_period['high'].max() - consolidation_period['low'].min()) / consolidation_period['close'].mean()
        avg_volume_ratio = consolidation_period['volume_ratio'].mean()

        if price_range <= params_v2['price_range_during_consolidation']['max'] and \
           avg_volume_ratio <= params_v2['volume_shrink_ratio']['max']:
            consolidation_v2 = True
            break

    if not consolidation_v2:
        v2_match = False
        v2_issues.append('consolidation')

    return {
        'v1_match': v1_match and consolidation_v1,
        'v2_match': v2_match and consolidation_v2,
        'v1_issues': v1_issues,
        'v2_issues': v2_issues,
        'last_day_volume_ratio': last_day['volume_ratio'],
        'last_day_pct_change': last_day['pct_change']
    }, "ok"

# ============ 改进版P002: 适应10-14天数据 ============
def match_p002_improved(df, params_v1, params_v2):
    """
    改进版P002: V型反转放量上攻

    关键改进：
    1. 移除last_idx < 15的硬编码限制
    2. 缩短下跌-反弹周期要求
    3. 放宽放量和涨幅要求
    """
    last_idx = len(df) - 1

    if last_idx < 5:  # 最少需要6天数据
        return None, "data_too_short"

    # 在可用数据范围内找底部
    search_range = min(last_idx, 12)  # 最多往前看12天
    recent_period = df.iloc[max(0, last_idx - search_range):last_idx + 1]

    if len(recent_period) < 4:
        return None, "data_too_short"

    bottom_idx_relative = recent_period['close'].idxmin()
    bottom_idx = bottom_idx_relative

    result = {
        'bottom_idx': bottom_idx,
        'last_idx': last_idx,
        'bottom_distance': last_idx - bottom_idx
    }

    # 底部太近的检查
    if bottom_idx >= last_idx - 1:
        return result, "bottom_too_close"

    # V1参数检查
    v1_match = check_v_reversal(df, bottom_idx, last_idx, params_v1)

    # V2参数检查
    v2_match = check_v_reversal(df, bottom_idx, last_idx, params_v2)

    result['v1_match'] = v1_match['match']
    result['v2_match'] = v2_match['match']
    result['v1_issues'] = v1_match['issues']
    result['v2_issues'] = v2_match['issues']
    result['decline_amplitude'] = v1_match.get('decline_amplitude', 0)
    result['rebound_rise'] = v1_match.get('rebound_rise', 0)
    result['rebound_days'] = v1_match.get('rebound_days', 0)
    result['rebound_volume_ratio'] = v1_match.get('rebound_volume_ratio', 0)

    return result, "ok"

def check_v_reversal(df, bottom_idx, last_idx, params):
    """检查V型反转"""
    issues = []
    match = True
    result = {'issues': issues}

    # 检查下跌段
    decline_start = max(0, bottom_idx - params['decline_days']['max'])
    decline_days = bottom_idx - decline_start

    if decline_days < params['decline_days']['min']:
        match = False
        issues.append('decline_days')
    else:
        decline_period = df.iloc[decline_start:bottom_idx + 1]
        if len(decline_period) >= 2:
            decline_amplitude = (decline_period['close'].iloc[0] - decline_period['close'].iloc[-1]) / decline_period['close'].iloc[0]
            result['decline_amplitude'] = decline_amplitude

            if decline_amplitude < params['decline_amplitude']['min']:
                match = False
                issues.append('decline_amplitude')

    # 检查反弹段
    rebound_period = df.iloc[bottom_idx:last_idx + 1]
    rebound_days = len(rebound_period)
    result['rebound_days'] = rebound_days

    if rebound_days < params['rebound_days']['min']:
        match = False
        issues.append('rebound_days_short')
    elif rebound_days > params['rebound_days']['max']:
        match = False
        issues.append('rebound_days_long')
    else:
        # 检查反弹放量
        rebound_volume_ratio = rebound_period['volume_ratio'].mean()
        result['rebound_volume_ratio'] = rebound_volume_ratio

        if rebound_volume_ratio < params['rebound_volume_ratio']['min']:
            match = False
            issues.append('rebound_volume')

        # 检查反弹涨幅
        if len(rebound_period) >= 2:
            rebound_rise = (rebound_period['close'].iloc[-1] - rebound_period['close'].iloc[0]) / rebound_period['close'].iloc[0]
            result['rebound_rise'] = rebound_rise

            if rebound_rise < params['rebound_rise']['min']:
                match = False
                issues.append('rebound_rise')

    result['match'] = match
    return result

def main():
    print("Loading samples...")
    special_samples = load_samples('special_samples.json')
    classic_samples = load_samples('classic_samples_stat.json')

    with open('classic_patterns.json', 'r', encoding='utf-8') as f:
        patterns_data = json.load(f)

    patterns = {p['pattern_id']: p for p in patterns_data['patterns']}

    print(f"Special samples: {len(special_samples)}")
    print(f"Classic samples: {len(classic_samples)}")

    # 当前参数 V1
    p001_v1 = {
        'consolidation_days': {'min': 3, 'max': 10},
        'volume_shrink_ratio': {'max': 1.2},
        'breakout_volume_ratio': {'min': 1.3},
        'price_range_during_consolidation': {'max': 0.10},
        'breakout_rise': {'min': 0.02}
    }

    # 改进参数 V2 - 适应14天数据
    p001_v2 = {
        'consolidation_days': {'min': 2, 'max': 8},  # 缩短
        'volume_shrink_ratio': {'max': 1.5},  # 放宽
        'breakout_volume_ratio': {'min': 1.2},  # 放宽
        'price_range_during_consolidation': {'max': 0.12},  # 放宽
        'breakout_rise': {'min': 0.015}  # 放宽
    }

    # 更宽松的V3
    p001_v3 = {
        'consolidation_days': {'min': 2, 'max': 6},
        'volume_shrink_ratio': {'max': 1.8},
        'breakout_volume_ratio': {'min': 1.1},
        'price_range_during_consolidation': {'max': 0.15},
        'breakout_rise': {'min': 0.01}
    }

    p002_v1 = {
        'decline_days': {'min': 2, 'max': 8},
        'decline_amplitude': {'min': 0.03},
        'rebound_days': {'min': 2, 'max': 6},
        'rebound_volume_ratio': {'min': 1.3},
        'rebound_rise': {'min': 0.03}
    }

    # 改进参数 V2
    p002_v2 = {
        'decline_days': {'min': 1, 'max': 6},  # 缩短
        'decline_amplitude': {'min': 0.02},  # 放宽
        'rebound_days': {'min': 2, 'max': 10},  # 延长上限
        'rebound_volume_ratio': {'min': 1.1},  # 放宽
        'rebound_rise': {'min': 0.02}  # 放宽
    }

    # 更宽松的V3
    p002_v3 = {
        'decline_days': {'min': 1, 'max': 8},
        'decline_amplitude': {'min': 0.015},
        'rebound_days': {'min': 2, 'max': 12},
        'rebound_volume_ratio': {'min': 1.0},
        'rebound_rise': {'min': 0.015}
    }

    # ============ P001 测试 ============
    print("\n" + "="*80)
    print("P001 Matching Test (Consolidation Breakout)")
    print("="*80)

    p001_v1_count = 0
    p001_v2_count = 0
    p001_v3_count = 0

    all_samples = special_samples + [{'kline_data': None, 'sample_id': s['sample_id']} for s in classic_samples]

    # 重新加载所有样本数据
    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        result_v1, _ = match_p001_improved(df, p001_v1, p001_v1)
        result_v2, _ = match_p001_improved(df, p001_v2, p001_v2)
        result_v3, _ = match_p001_improved(df, p001_v3, p001_v3)

        if result_v1 and result_v1.get('v1_match'):
            p001_v1_count += 1
        if result_v2 and result_v2.get('v2_match'):
            p001_v2_count += 1
        if result_v3 and result_v3.get('v2_match'):
            p001_v3_count += 1

    total = len(special_samples)
    print(f"\nP001 V1 (current params): {p001_v1_count}/{total} ({p001_v1_count/total*100:.1f}%)")
    print(f"P001 V2 (improved params): {p001_v2_count}/{total} ({p001_v2_count/total*100:.1f}%)")
    print(f"P001 V3 (relaxed params): {p001_v3_count}/{total} ({p001_v3_count/total*100:.1f}%)")

    # ============ P002 测试 ============
    print("\n" + "="*80)
    print("P002 Matching Test (V-Reversal)")
    print("="*80)

    p002_v1_count = 0
    p002_v2_count = 0
    p002_v3_count = 0
    p002_issues_stat = defaultdict(int)

    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        result_v1, status = match_p002_improved(df, p002_v1, p002_v1)
        result_v2, _ = match_p002_improved(df, p002_v2, p002_v2)
        result_v3, _ = match_p002_improved(df, p002_v3, p002_v3)

        if result_v1 and result_v1.get('v1_match'):
            p002_v1_count += 1
        if result_v2 and result_v2.get('v2_match'):
            p002_v2_count += 1
        if result_v3 and result_v3.get('v2_match'):
            p002_v3_count += 1

        # 统计失败原因
        if result_v2 and not result_v2.get('v2_match'):
            for issue in result_v2.get('v2_issues', []):
                p002_issues_stat[issue] += 1

    print(f"\nP002 V1 (current params): {p002_v1_count}/{total} ({p002_v1_count/total*100:.1f}%)")
    print(f"P002 V2 (improved params): {p002_v2_count}/{total} ({p002_v2_count/total*100:.1f}%)")
    print(f"P002 V3 (relaxed params): {p002_v3_count}/{total} ({p002_v3_count/total*100:.1f}%)")

    print("\nP002 V2 failure reasons:")
    for issue, count in sorted(p002_issues_stat.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count} ({count/total*100:.1f}%)")

    # ============ 综合统计 ============
    print("\n" + "="*80)
    print("Combined Pattern Matching Summary")
    print("="*80)

    # 使用V2参数统计各模式覆盖
    any_v2_count = 0
    p001_only = 0
    p002_only = 0
    p003_count = 16  # 已知的经典样本数

    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        result_p001, _ = match_p001_improved(df, p001_v2, p001_v2)
        result_p002, _ = match_p002_improved(df, p002_v2, p002_v2)

        p001_match = result_p001 and result_p001.get('v2_match')
        p002_match = result_p002 and result_p002.get('v2_match')

        if p001_match or p002_match:
            any_v2_count += 1
        if p001_match and not p002_match:
            p001_only += 1
        if p002_match and not p001_match:
            p002_only += 1

    print(f"\nWith V2 params (special samples only):")
    print(f"  P001 matches: {p001_v2_count} ({p001_v2_count/total*100:.1f}%)")
    print(f"  P002 matches: {p002_v2_count} ({p002_v2_count/total*100:.1f}%)")
    print(f"  Any match (P001 or P002): {any_v2_count} ({any_v2_count/total*100:.1f}%)")
    print(f"  P001 only: {p001_only}")
    print(f"  P002 only: {p002_only}")

    total_all = 282
    classic_with_v2 = p003_count + any_v2_count
    print(f"\nProjected total coverage:")
    print(f"  P003 (already working): {p003_count} ({p003_count/total_all*100:.1f}%)")
    print(f"  P001+P002 (with V2): {any_v2_count} ({any_v2_count/total_all*100:.1f}%)")
    print(f"  Total classic: {classic_with_v2} ({classic_with_v2/total_all*100:.1f}%)")
    print(f"  Remaining for AI: {total_all - classic_with_v2} ({(total_all - classic_with_v2)/total_all*100:.1f}%)")

    # ============ V3 激进策略 ============
    print("\n" + "="*80)
    print("V3 Aggressive Strategy")
    print("="*80)

    any_v3_count = 0
    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        result_p001, _ = match_p001_improved(df, p001_v3, p001_v3)
        result_p002, _ = match_p002_improved(df, p002_v3, p002_v3)

        if (result_p001 and result_p001.get('v2_match')) or \
           (result_p002 and result_p002.get('v2_match')):
            any_v3_count += 1

    classic_with_v3 = p003_count + any_v3_count
    print(f"  Total classic with V3: {classic_with_v3} ({classic_with_v3/total_all*100:.1f}%)")
    print(f"  Remaining for AI: {total_all - classic_with_v3} ({(total_all - classic_with_v3)/total_all*100:.1f}%)")

    # ============ 分析特定数据特征 ============
    print("\n" + "="*80)
    print("Data Characteristics Analysis")
    print("="*80)

    # 分析哪些样本有V型反转特征
    v_shape_samples = []
    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        last_idx = len(df) - 1
        if last_idx < 5:
            continue

        # 找底部
        bottom_idx = df['close'].idxmin()

        # 计算底部前后的涨跌
        if bottom_idx > 1 and bottom_idx < last_idx - 1:
            decline = (df['close'].iloc[0] - df['close'].iloc[bottom_idx]) / df['close'].iloc[0]
            rebound = (df['close'].iloc[last_idx] - df['close'].iloc[bottom_idx]) / df['close'].iloc[bottom_idx]

            if decline > 0.02 and rebound > 0.02:  # 有明显的V型
                v_shape_samples.append({
                    'sample_id': sample['sample_id'],
                    'decline': decline,
                    'rebound': rebound,
                    'bottom_pos': bottom_idx,
                    'total_days': last_idx + 1
                })

    print(f"\nSamples with V-shape pattern (decline>2%, rebound>2%):")
    print(f"  Count: {len(v_shape_samples)} ({len(v_shape_samples)/len(special_samples)*100:.1f}%)")

    if v_shape_samples:
        declines = [s['decline'] for s in v_shape_samples]
        rebounds = [s['rebound'] for s in v_shape_samples]
        print(f"  Avg decline: {np.mean(declines)*100:.2f}%")
        print(f"  Avg rebound: {np.mean(rebounds)*100:.2f}%")

if __name__ == '__main__':
    main()
