"""诊断脚本：深入分析为什么P001和P002模式匹配率为0%"""
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

    # 计算成交量比率
    window_size = min(20, len(df))
    min_periods = min(5, len(df))
    df['avg_volume'] = df['volume'].rolling(window=window_size, min_periods=min_periods).mean()
    df['volume_ratio'] = df['volume'] / df['avg_volume']

    # 计算涨跌幅
    df['pct_change'] = df['close'].pct_change()

    return df

def diagnose_p001_failure(df, params):
    """诊断P001失败的具体原因"""
    last_idx = len(df) - 1
    issues = []
    stats = {}

    # 问题1：数据量限制
    if last_idx < 20:
        issues.append(f"数据量不足: {last_idx+1}天 < 20天要求")
        stats['data_length'] = last_idx + 1
        stats['data_issue'] = True
        return issues, stats

    stats['data_length'] = last_idx + 1
    stats['data_issue'] = False

    # 问题2：最后一天放量检查
    last_day = df.iloc[last_idx]
    stats['last_day_volume_ratio'] = last_day['volume_ratio']
    stats['last_day_pct_change'] = last_day['pct_change']

    if last_day['volume_ratio'] < params['breakout_volume_ratio']['min']:
        issues.append(f"最后一天未放量: {last_day['volume_ratio']:.2f} < {params['breakout_volume_ratio']['min']}")
        stats['volume_issue'] = True
    else:
        stats['volume_issue'] = False

    if last_day['pct_change'] < params['breakout_rise']['min']:
        issues.append(f"最后一天涨幅不足: {last_day['pct_change']*100:.2f}% < {params['breakout_rise']['min']*100:.1f}%")
        stats['rise_issue'] = True
    else:
        stats['rise_issue'] = False

    # 问题3：横盘期检查
    stats['consolidation_found'] = False
    best_price_range = float('inf')
    best_avg_volume_ratio = float('inf')

    for days in range(params['consolidation_days']['min'],
                      min(params['consolidation_days']['max'] + 1, last_idx - 5)):
        start_idx = last_idx - days
        consolidation_period = df.iloc[start_idx:last_idx]

        price_range = (consolidation_period['high'].max() - consolidation_period['low'].min()) / consolidation_period['close'].mean()
        avg_volume_ratio = consolidation_period['volume_ratio'].mean()

        if price_range < best_price_range:
            best_price_range = price_range
        if avg_volume_ratio < best_avg_volume_ratio:
            best_avg_volume_ratio = avg_volume_ratio

        if price_range <= params['price_range_during_consolidation']['max'] and \
           avg_volume_ratio <= params['volume_shrink_ratio']['max']:
            stats['consolidation_found'] = True
            break

    stats['best_price_range'] = best_price_range
    stats['best_avg_volume_ratio'] = best_avg_volume_ratio

    if not stats['consolidation_found']:
        issues.append(f"未找到横盘区间: 最佳价格波动{best_price_range*100:.2f}% > {params['price_range_during_consolidation']['max']*100}%, 最佳量比{best_avg_volume_ratio:.2f} > {params['volume_shrink_ratio']['max']}")

    return issues, stats

def diagnose_p002_failure(df, params):
    """诊断P002失败的具体原因"""
    last_idx = len(df) - 1
    issues = []
    stats = {}

    # 问题1：数据量限制
    if last_idx < 15:
        issues.append(f"数据量不足: {last_idx+1}天 < 15天要求")
        stats['data_issue'] = True
        return issues, stats

    stats['data_issue'] = False

    # 找最近的底部
    recent_period = df.iloc[last_idx - 15:last_idx + 1]
    bottom_idx_relative = recent_period['close'].idxmin()
    bottom_idx = df.index.get_loc(bottom_idx_relative)

    stats['bottom_idx'] = bottom_idx
    stats['last_idx'] = last_idx
    stats['bottom_distance'] = last_idx - bottom_idx

    # 问题2：底部位置检查
    if bottom_idx >= last_idx - 1:
        issues.append(f"底部太近: 底部在倒数第{last_idx - bottom_idx + 1}天")
        stats['bottom_too_close'] = True
        return issues, stats

    stats['bottom_too_close'] = False

    # 问题3：下跌段检查
    decline_days = bottom_idx - max(0, bottom_idx - params['decline_days']['max'])
    stats['decline_days'] = decline_days

    if decline_days < params['decline_days']['min']:
        issues.append(f"下跌天数不足: {decline_days}天 < {params['decline_days']['min']}天")
        stats['decline_days_issue'] = True
    else:
        stats['decline_days_issue'] = False

        decline_period = df.iloc[bottom_idx - decline_days:bottom_idx + 1]
        decline_amplitude = (decline_period['close'].iloc[0] - decline_period['close'].iloc[-1]) / decline_period['close'].iloc[0]
        stats['decline_amplitude'] = decline_amplitude

        if decline_amplitude < params['decline_amplitude']['min']:
            issues.append(f"下跌幅度不足: {decline_amplitude*100:.2f}% < {params['decline_amplitude']['min']*100}%")
            stats['decline_amplitude_issue'] = True
        else:
            stats['decline_amplitude_issue'] = False

    # 问题4：反弹段检查
    rebound_period = df.iloc[bottom_idx:last_idx + 1]
    rebound_days = len(rebound_period)
    stats['rebound_days'] = rebound_days

    if rebound_days < params['rebound_days']['min']:
        issues.append(f"反弹天数不足: {rebound_days}天 < {params['rebound_days']['min']}天")
        stats['rebound_days_issue'] = 'too_short'
    elif rebound_days > params['rebound_days']['max']:
        issues.append(f"反弹天数过长: {rebound_days}天 > {params['rebound_days']['max']}天")
        stats['rebound_days_issue'] = 'too_long'
    else:
        stats['rebound_days_issue'] = None

        # 检查反弹放量
        rebound_volume_ratio = rebound_period['volume_ratio'].mean()
        stats['rebound_volume_ratio'] = rebound_volume_ratio

        if rebound_volume_ratio < params['rebound_volume_ratio']['min']:
            issues.append(f"反弹期未放量: {rebound_volume_ratio:.2f} < {params['rebound_volume_ratio']['min']}")
            stats['rebound_volume_issue'] = True
        else:
            stats['rebound_volume_issue'] = False

        # 检查反弹涨幅
        rebound_rise = (rebound_period['close'].iloc[-1] - rebound_period['close'].iloc[0]) / rebound_period['close'].iloc[0]
        stats['rebound_rise'] = rebound_rise

        if rebound_rise < params['rebound_rise']['min']:
            issues.append(f"反弹涨幅不足: {rebound_rise*100:.2f}% < {params['rebound_rise']['min']*100}%")
            stats['rebound_rise_issue'] = True
        else:
            stats['rebound_rise_issue'] = False

    return issues, stats

def diagnose_p003_success(df, params):
    """分析P003成功的原因"""
    last_idx = len(df) - 1
    stats = {}

    if last_idx < 5:
        return None

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

    stats['continuous_days'] = continuous_days
    stats['total_rise'] = total_rise
    stats['has_pullback'] = has_pullback
    stats['volume_ratios'] = volume_ratios

    if volume_ratios:
        stats['days_above_threshold'] = sum(1 for v in volume_ratios if v >= params['daily_volume_ratio']['min'])
        stats['max_volume_ratio'] = max(volume_ratios) if volume_ratios else 0

    return stats

def main():
    # 加载样本数据
    print("加载样本数据...")
    special_samples = load_samples('special_samples.json')
    classic_samples = load_samples('classic_samples_stat.json')

    # 加载模式定义
    with open('classic_patterns.json', 'r', encoding='utf-8') as f:
        patterns_data = json.load(f)

    patterns = {p['pattern_id']: p for p in patterns_data['patterns']}

    print(f"Special样本数: {len(special_samples)}")
    print(f"Classic样本数: {len(classic_samples)}")

    # P001 诊断统计
    print("\n" + "="*80)
    print("P001 诊断分析 (缩量震荡后放量突破)")
    print("="*80)

    p001_stats = defaultdict(int)
    p001_examples = []

    for sample in special_samples[:50]:  # 取前50个样本深入分析
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        issues, stats = diagnose_p001_failure(df, patterns['P001']['parameters'])

        if stats.get('data_issue'):
            p001_stats['数据量不足'] += 1
        else:
            if stats.get('volume_issue'):
                p001_stats['最后一天未放量'] += 1
            if stats.get('rise_issue'):
                p001_stats['最后一天涨幅不足'] += 1
            if not stats.get('consolidation_found'):
                p001_stats['未找到横盘区间'] += 1

        if len(p001_examples) < 3:
            p001_examples.append({
                'sample_id': sample['sample_id'],
                'issues': issues,
                'stats': stats
            })

    print("\nP001失败原因统计 (前50个样本):")
    for reason, count in sorted(p001_stats.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count} ({count/50*100:.1f}%)")

    print("\nP001失败样本示例:")
    for ex in p001_examples:
        print(f"\n  样本 {ex['sample_id']}:")
        print(f"    数据天数: {ex['stats'].get('data_length', 'N/A')}")
        print(f"    最后一天量比: {ex['stats'].get('last_day_volume_ratio', 'N/A'):.2f}" if isinstance(ex['stats'].get('last_day_volume_ratio'), float) else f"    最后一天量比: N/A")
        print(f"    最后一天涨幅: {ex['stats'].get('last_day_pct_change', 0)*100:.2f}%")
        print(f"    最佳价格波动: {ex['stats'].get('best_price_range', 0)*100:.2f}%")
        print(f"    最佳量比: {ex['stats'].get('best_avg_volume_ratio', 0):.2f}")
        for issue in ex['issues']:
            print(f"    - {issue}")

    # P002 诊断统计
    print("\n" + "="*80)
    print("P002 诊断分析 (V型反转放量上攻)")
    print("="*80)

    p002_stats = defaultdict(int)
    p002_examples = []

    for sample in special_samples[:50]:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        issues, stats = diagnose_p002_failure(df, patterns['P002']['parameters'])

        if stats.get('data_issue'):
            p002_stats['数据量不足'] += 1
        elif stats.get('bottom_too_close'):
            p002_stats['底部太近'] += 1
        else:
            if stats.get('decline_days_issue'):
                p002_stats['下跌天数不足'] += 1
            if stats.get('decline_amplitude_issue'):
                p002_stats['下跌幅度不足'] += 1
            if stats.get('rebound_days_issue') == 'too_short':
                p002_stats['反弹天数不足'] += 1
            if stats.get('rebound_days_issue') == 'too_long':
                p002_stats['反弹天数过长'] += 1
            if stats.get('rebound_volume_issue'):
                p002_stats['反弹期未放量'] += 1
            if stats.get('rebound_rise_issue'):
                p002_stats['反弹涨幅不足'] += 1

        if len(p002_examples) < 3:
            p002_examples.append({
                'sample_id': sample['sample_id'],
                'issues': issues,
                'stats': stats
            })

    print("\nP002失败原因统计 (前50个样本):")
    for reason, count in sorted(p002_stats.items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count} ({count/50*100:.1f}%)")

    print("\nP002失败样本示例:")
    for ex in p002_examples:
        print(f"\n  样本 {ex['sample_id']}:")
        print(f"    底部位置: 倒数第{ex['stats'].get('bottom_distance', 'N/A')}天")
        print(f"    下跌天数: {ex['stats'].get('decline_days', 'N/A')}")
        print(f"    下跌幅度: {ex['stats'].get('decline_amplitude', 0)*100:.2f}%" if ex['stats'].get('decline_amplitude') else "    下跌幅度: N/A")
        print(f"    反弹天数: {ex['stats'].get('rebound_days', 'N/A')}")
        print(f"    反弹量比: {ex['stats'].get('rebound_volume_ratio', 0):.2f}" if ex['stats'].get('rebound_volume_ratio') else "    反弹量比: N/A")
        print(f"    反弹涨幅: {ex['stats'].get('rebound_rise', 0)*100:.2f}%" if ex['stats'].get('rebound_rise') else "    反弹涨幅: N/A")
        for issue in ex['issues']:
            print(f"    - {issue}")

    # P003 成功案例分析
    print("\n" + "="*80)
    print("P003 成功案例分析 (连续放量上攻)")
    print("="*80)

    # 加载成功的样本
    classic_sample_ids = {s['sample_id'] for s in classic_samples}

    # 从special_samples中找出被标记为special但实际可能是P003的样本
    # 以及分析为什么P003能成功

    print("\n分析P003成功的样本特征:")

    # 分析所有样本看哪些接近P003标准
    near_p003_count = 0
    p003_stats_list = []

    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        stats = diagnose_p003_success(df, patterns['P003']['parameters'])
        if stats and stats['continuous_days'] >= 2:  # 至少连续2天
            near_p003_count += 1
            p003_stats_list.append(stats)

    print(f"  接近P003标准(连续上涨>=2天)的样本: {near_p003_count}/{len(special_samples)}")

    if p003_stats_list:
        avg_continuous = np.mean([s['continuous_days'] for s in p003_stats_list])
        avg_total_rise = np.mean([s['total_rise'] for s in p003_stats_list])
        print(f"  平均连续上涨天数: {avg_continuous:.1f}")
        print(f"  平均累计涨幅: {avg_total_rise*100:.2f}%")

    # 关键数据统计
    print("\n" + "="*80)
    print("关键数据特征统计 (全部样本)")
    print("="*80)

    all_last_day_volume_ratios = []
    all_last_day_pct_changes = []
    all_data_lengths = []
    all_price_ranges = []

    for sample in special_samples:
        df = analyze_sample(sample['kline_data'])
        if df is None:
            continue

        all_data_lengths.append(len(df))

        last_idx = len(df) - 1
        if last_idx >= 0:
            all_last_day_volume_ratios.append(df.iloc[last_idx]['volume_ratio'])
            if not pd.isna(df.iloc[last_idx]['pct_change']):
                all_last_day_pct_changes.append(df.iloc[last_idx]['pct_change'])

        # 计算整体价格波动
        if len(df) >= 5:
            price_range = (df['high'].max() - df['low'].min()) / df['close'].mean()
            all_price_ranges.append(price_range)

    print(f"\n数据天数:")
    print(f"  范围: {min(all_data_lengths)} - {max(all_data_lengths)}")
    print(f"  中位数: {np.median(all_data_lengths):.0f}")

    print(f"\n最后一天成交量比率:")
    print(f"  中位数: {np.median(all_last_day_volume_ratios):.2f}")
    print(f"  75分位: {np.percentile(all_last_day_volume_ratios, 75):.2f}")
    print(f"  90分位: {np.percentile(all_last_day_volume_ratios, 90):.2f}")
    print(f"  >1.3倍的比例: {sum(1 for v in all_last_day_volume_ratios if v >= 1.3)/len(all_last_day_volume_ratios)*100:.1f}%")

    print(f"\n最后一天涨幅:")
    print(f"  中位数: {np.median(all_last_day_pct_changes)*100:.2f}%")
    print(f"  75分位: {np.percentile(all_last_day_pct_changes, 75)*100:.2f}%")
    print(f"  >2%的比例: {sum(1 for v in all_last_day_pct_changes if v >= 0.02)/len(all_last_day_pct_changes)*100:.1f}%")

    print(f"\n整体价格波动范围:")
    print(f"  中位数: {np.median(all_price_ranges)*100:.2f}%")
    print(f"  25分位: {np.percentile(all_price_ranges, 25)*100:.2f}%")
    print(f"  <10%的比例: {sum(1 for v in all_price_ranges if v < 0.10)/len(all_price_ranges)*100:.1f}%")

if __name__ == '__main__':
    main()
