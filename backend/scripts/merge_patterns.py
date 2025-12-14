"""合并经典模式和AI发现的新模式到数据库"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import StockDatabase
import json

def main():
    # 初始化数据库
    db = StockDatabase(db_path='../data/stocks.db')

    # 读取经典模式
    print("读取经典模式...")
    with open('../../classic_patterns.json', 'r', encoding='utf-8') as f:
        classic_data = json.load(f)
    classic_patterns = classic_data['patterns']
    print(f"读取到 {len(classic_patterns)} 个经典模式")

    # 读取AI发现的新模式
    print("\n读取AI新模式...")
    try:
        with open('../../new_patterns.json', 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        new_patterns = new_data['patterns']
        print(f"读取到 {len(new_patterns)} 个AI新模式")
    except FileNotFoundError:
        print("未找到new_patterns.json，只保存经典模式")
        new_patterns = []

    # 合并所有模式
    all_patterns = classic_patterns + new_patterns
    print(f"\n总共 {len(all_patterns)} 个模式待保存")

    # 保存到数据库
    print("\n保存模式到数据库...")
    try:
        db.save_classic_patterns(all_patterns)
        print("✓ 保存成功")

        print("\n模式列表:")
        for pattern in all_patterns:
            print(f"  - {pattern['pattern_id']}: {pattern['pattern_name']} ({pattern['pattern_type']})")

    except Exception as e:
        print(f"✗ 保存失败: {e}")

if __name__ == '__main__':
    main()
