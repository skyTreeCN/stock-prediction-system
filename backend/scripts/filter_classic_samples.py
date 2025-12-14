"""过滤经典样本 - 找出不符合经典模式的特殊样本"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import StockDatabase
from app.pattern_matcher import load_classic_patterns, match_classic_patterns
import json

def main():
    # 初始化数据库（使用绝对路径）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', '..', 'data', 'stocks.db')
    db = StockDatabase(db_path=db_path)

    # 加载经典模式
    patterns = load_classic_patterns('../../classic_patterns.json')
    print(f"Loaded {len(patterns)} classic patterns")

    # 获取300个高质量样本
    print("Fetching 300 training samples...")
    samples_df = db.get_rising_samples(sample_count=300, rise_threshold=0.06)
    print(f"Got {len(samples_df)} samples")

    if len(samples_df) == 0:
        print("No samples found")
        return

    # 获取样本ID列表
    sample_ids = samples_df['id'].tolist()

    # 获取每个样本的20天K线上下文
    print("Fetching K-line context for samples...")
    samples_with_context = db.get_samples_with_context(sample_ids, days_before=20)
    print(f"Got {len(samples_with_context)} complete samples")

    # 过滤：找出不匹配经典模式的样本
    special_samples = []
    classic_samples = []

    print("Matching classic patterns...")
    for sample in samples_with_context:
        matched = match_classic_patterns(sample['kline_data'], patterns)

        if len(matched) == 0:
            # 不匹配任何经典模式
            special_samples.append({
                'sample_id': sample['sample_id'],
                'code': sample['code'],
                'date': sample['date'],
                'kline_data': sample['kline_data']
            })
        else:
            # 匹配到经典模式
            classic_samples.append({
                'sample_id': sample['sample_id'],
                'code': sample['code'],
                'date': sample['date'],
                'matched_patterns': [m['pattern_name'] for m in matched]
            })

    print(f"\nResults:")
    print(f"  Classic samples: {len(classic_samples)}")
    print(f"  Special samples: {len(special_samples)}")

    # 保存特殊样本
    output_file = '../../special_samples.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(special_samples, f, ensure_ascii=False, indent=2)
    print(f"\nSpecial samples saved to: {output_file}")

    # 保存经典样本统计
    classic_file = '../../classic_samples_stat.json'
    with open(classic_file, 'w', encoding='utf-8') as f:
        json.dump(classic_samples, f, ensure_ascii=False, indent=2)
    print(f"Classic samples stat saved to: {classic_file}")

if __name__ == '__main__':
    main()
