"""阶段2.5：数据验证与特征工程
从106个特殊样本中提取数值特征,为K-means聚类做准备
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import pandas as pd
import numpy as np
from typing import List, Dict

def extract_features(kline_data: List[Dict]) -> Dict[str, float]:
    """从K线数据中提取数值特征

    Returns:
        特征字典,包含:
        - volatility: 价格波动率
        - volume_trend: 成交量趋势
        - momentum: 动量指标
        - price_position: 价格位置（相对高低点）
        - volume_surge_max: 最大成交量放大倍数
        - consecutive_rise_ratio: 连续上涨比例
        - max_single_rise: 最大单日涨幅
        - total_rise: 总涨幅
    """
    df = pd.DataFrame(kline_data)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 计算日间涨跌幅
    df['pct_change'] = df['close'].pct_change()

    # 计算成交量比率
    avg_volume = df['volume'].mean()
    df['volume_ratio'] = df['volume'] / avg_volume

    features = {}

    # 特征1: 价格波动率（标准差 / 均值）
    features['volatility'] = df['close'].std() / df['close'].mean()

    # 特征2: 成交量趋势（后5天均量 / 前5天均量）
    if len(df) >= 10:
        first_half_vol = df.iloc[:len(df)//2]['volume'].mean()
        second_half_vol = df.iloc[len(df)//2:]['volume'].mean()
        features['volume_trend'] = second_half_vol / first_half_vol if first_half_vol > 0 else 1.0
    else:
        features['volume_trend'] = 1.0

    # 特征3: 动量指标（最近5天平均涨幅）
    if len(df) >= 5:
        features['momentum'] = df['pct_change'].tail(5).mean()
    else:
        features['momentum'] = df['pct_change'].mean()

    # 特征4: 价格位置（当前价格 - 最低价）/ (最高价 - 最低价）
    price_high = df['high'].max()
    price_low = df['low'].min()
    if price_high > price_low:
        features['price_position'] = (df['close'].iloc[-1] - price_low) / (price_high - price_low)
    else:
        features['price_position'] = 0.5

    # 特征5: 最大成交量放大倍数
    features['volume_surge_max'] = df['volume_ratio'].max()

    # 特征6: 连续上涨比例（上涨天数 / 总天数）
    rise_days = (df['pct_change'] > 0).sum()
    features['consecutive_rise_ratio'] = rise_days / len(df) if len(df) > 0 else 0

    # 特征7: 最大单日涨幅
    features['max_single_rise'] = df['pct_change'].max()

    # 特征8: 总涨幅（期间收益率）
    features['total_rise'] = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]

    return features


def main():
    # 加载特殊样本
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, '..', '..', 'special_samples.json')

    print("Loading special samples...")
    with open(input_file, 'r', encoding='utf-8') as f:
        samples = json.load(f)

    print(f"Total samples: {len(samples)}")

    # 数据质量检查
    print("\nData quality check:")
    kline_lengths = [len(s['kline_data']) for s in samples]
    print(f"  K-line lengths: min={min(kline_lengths)}, max={max(kline_lengths)}, avg={sum(kline_lengths)/len(kline_lengths):.1f}")

    # 提取特征
    print("\nExtracting features...")
    sample_features = []

    for sample in samples:
        features = extract_features(sample['kline_data'])

        sample_features.append({
            'sample_id': sample['sample_id'],
            'code': sample['code'],
            'date': sample['date'],
            'features': features
        })

    # 保存特征向量
    output_file = os.path.join(script_dir, '..', '..', 'feature_vectors.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(sample_features, f, ensure_ascii=False, indent=2)

    print(f"\nFeature vectors saved to: {output_file}")

    # 输出特征统计
    print("\nFeature statistics:")
    df_features = pd.DataFrame([s['features'] for s in sample_features])
    print(df_features.describe())

    print("\nFeature extraction completed!")


if __name__ == '__main__':
    main()
