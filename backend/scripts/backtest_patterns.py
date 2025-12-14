"""历史回测验证 - 验证模式的准确率（纯程序验证，无AI成本）"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import StockDatabase
from app.pattern_matcher import load_classic_patterns, match_classic_patterns
import json
from datetime import datetime, timedelta
import pandas as pd

def get_historical_dates(db, days_back=90):
    """获取历史回测日期列表"""
    conn = db.get_connection()
    cursor = conn.cursor()

    # 获取最近的日期
    cursor.execute('SELECT MAX(date) FROM stock_data')
    latest_date = cursor.fetchone()[0]

    if not latest_date:
        conn.close()
        return []

    # 获取过去N天的所有交易日期
    cursor.execute('''
        SELECT DISTINCT date
        FROM stock_data
        WHERE date <= ?
            AND date >= date(?, '-{} days')
        ORDER BY date DESC
    '''.format(days_back), (latest_date, latest_date))

    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates

def backtest_single_day(db, test_date, patterns):
    """回测单个交易日"""
    conn = db.get_connection()
    cursor = conn.cursor()

    # 获取该日期前30天的所有股票数据
    cursor.execute('''
        SELECT DISTINCT code FROM stock_data
        WHERE date = ?
    ''', (test_date,))

    codes = [row[0] for row in cursor.fetchall()]

    predictions = []

    for code in codes:
        # 获取该股票在测试日期前30天的K线数据
        cursor.execute('''
            SELECT date, open, high, low, close, volume
            FROM stock_data
            WHERE code = ?
                AND date <= ?
                AND date > date(?, '-30 days')
            ORDER BY date ASC
        ''', (code, test_date, test_date))

        kline_data = []
        for row in cursor.fetchall():
            kline_data.append({
                'date': row[0],
                'open': row[1],
                'high': row[2],
                'low': row[3],
                'close': row[4],
                'volume': row[5]
            })

        if len(kline_data) < 20:
            continue

        # 程序匹配模式
        matched = match_classic_patterns(kline_data, patterns)

        if len(matched) > 0:
            # 获取T+2日的收盘价验证结果
            cursor.execute('''
                SELECT t1.close, t2.close
                FROM stock_data t1
                LEFT JOIN stock_data t2 ON t1.code = t2.code
                    AND date(t2.date) = date(t1.date, '+2 days')
                WHERE t1.code = ? AND t1.date = ?
            ''', (code, test_date))

            result = cursor.fetchone()
            if result and result[0] and result[1]:
                base_price = result[0]
                future_price = result[1]
                rise_pct = (future_price - base_price) / base_price * 100

                predictions.append({
                    'code': code,
                    'date': test_date,
                    'matched_patterns': [m['pattern_id'] for m in matched],
                    'base_price': base_price,
                    'future_price': future_price,
                    'rise_pct': rise_pct,
                    'is_success': rise_pct >= 6.0  # 6%阈值
                })

    conn.close()
    return predictions

def main():
    # 初始化数据库
    db = StockDatabase(db_path='../data/stocks.db')

    # 加载模式（经典+AI新模式）
    print("加载模式...")
    try:
        # 尝试从数据库读取
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pattern_id, pattern_name, pattern_type, parameters, match_rules
            FROM rising_patterns
            WHERE is_active = 1
        ''')

        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'pattern_id': row[0],
                'pattern_name': row[1],
                'pattern_type': row[2],
                'parameters': json.loads(row[3]),
                'match_rules': json.loads(row[4]),
                'is_active': True
            })
        conn.close()

        if len(patterns) == 0:
            # 降级：只用经典模式
            print("数据库无模式，使用classic_patterns.json")
            patterns = load_classic_patterns('../../classic_patterns.json')
    except Exception as e:
        print(f"从数据库加载失败: {e}")
        patterns = load_classic_patterns('../../classic_patterns.json')

    print(f"加载了 {len(patterns)} 个模式")

    # 获取历史日期（过去3个月）
    print("\n获取历史回测日期...")
    historical_dates = get_historical_dates(db, days_back=90)
    print(f"回测日期数: {len(historical_dates)} 天")

    if len(historical_dates) == 0:
        print("没有历史数据可供回测")
        return

    # 回测
    print("\n开始历史回测...")
    all_predictions = []

    for i, test_date in enumerate(historical_dates[:60]):  # 最多回测60天
        if i % 10 == 0:
            print(f"  进度: {i+1}/{min(60, len(historical_dates))}")

        day_predictions = backtest_single_day(db, test_date, patterns)
        all_predictions.extend(day_predictions)

    print(f"\n回测完成，共 {len(all_predictions)} 个预测")

    # 统计每个模式的准确率
    pattern_stats = {}

    for pred in all_predictions:
        for pattern_id in pred['matched_patterns']:
            if pattern_id not in pattern_stats:
                pattern_stats[pattern_id] = {
                    'total': 0,
                    'success': 0,
                    'pattern_name': next((p['pattern_name'] for p in patterns if p['pattern_id'] == pattern_id), pattern_id)
                }

            pattern_stats[pattern_id]['total'] += 1
            if pred['is_success']:
                pattern_stats[pattern_id]['success'] += 1

    # 计算准确率
    print("\n模式准确率统计:")
    results = []
    for pattern_id, stats in pattern_stats.items():
        accuracy = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
        results.append({
            'pattern_id': pattern_id,
            'pattern_name': stats['pattern_name'],
            'total_predictions': stats['total'],
            'success_count': stats['success'],
            'accuracy': round(accuracy, 2)
        })
        print(f"  {pattern_id} ({stats['pattern_name']}): {accuracy:.1f}% ({stats['success']}/{stats['total']})")

    # 保存结果
    output = {
        'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'days_tested': len(historical_dates[:60]),
        'total_predictions': len(all_predictions),
        'pattern_results': results,
        'predictions': all_predictions[:100]  # 保存前100个样例
    }

    output_file = '../../backtest_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n回测结果已保存到: {output_file}")

    # 更新数据库中的准确率
    print("\n更新数据库中的模式准确率...")
    conn = db.get_connection()
    cursor = conn.cursor()

    for result in results:
        try:
            cursor.execute('''
                UPDATE rising_patterns
                SET validated_success_rate = ?,
                    validation_sample_count = ?,
                    validation_date = ?
                WHERE pattern_id = ?
            ''', (
                result['accuracy'],
                result['total_predictions'],
                datetime.now().strftime('%Y-%m-%d'),
                result['pattern_id']
            ))
        except Exception as e:
            print(f"  更新 {result['pattern_id']} 失败: {e}")

    conn.commit()
    conn.close()
    print("✓ 数据库已更新")

if __name__ == '__main__':
    main()
