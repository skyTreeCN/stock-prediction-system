"""定时任务调度器 - 每日模式验证和准确率统计"""
import schedule
import time
from datetime import datetime
import os
from .database import StockDatabase
from .analyzer import StockAnalyzer
from .pattern_matcher import load_classic_patterns
import json

class PatternScheduler:
    """模式识别定时任务"""

    def __init__(self, db_path: str = "../data/stocks.db", api_key: str = None):
        self.db = StockDatabase(db_path)
        self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')

        if not self.api_key:
            raise ValueError("未设置 ANTHROPIC_API_KEY 环境变量")

        self.analyzer = StockAnalyzer(self.api_key)

    def daily_prediction(self):
        """每日预测任务（场景二）"""
        print(f"\n{'='*60}")
        print(f"每日预测任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        try:
            # 获取股票池最近30天数据
            print("\n1. 加载股票池数据...")
            stock_data = self.db.get_recent_data_all_stocks(days=30)
            print(f"   获取到 {len(stock_data)} 条数据")

            # 加载模式
            print("\n2. 加载模式...")
            patterns = self._load_patterns()
            print(f"   加载了 {len(patterns)} 个模式")

            # 预测（启用程序预筛选）
            print("\n3. 开始预测...")
            predictions = self.analyzer.predict_stock_probability(
                stock_data,
                patterns,
                batch_size=30,
                use_pre_screening=True,
                pattern_file='classic_patterns.json'
            )

            print(f"\n4. 预测完成，共 {len(predictions)} 只股票")

            # 保存结果
            output_file = f"predictions_{datetime.now().strftime('%Y%m%d')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'predictions': predictions
                }, f, ensure_ascii=False, indent=2)

            print(f"   结果已保存: {output_file}")

            # 显示Top10
            print("\n📊 Top 10 预测:")
            for i, pred in enumerate(predictions[:10], 1):
                print(f"   {i}. {pred['code']} ({pred['name']}): {pred['probability']:.1f}%")
                print(f"      {pred['reason']}")

        except Exception as e:
            print(f"❌ 每日预测失败: {e}")

    def weekly_accuracy_update(self):
        """每周准确率更新任务"""
        print(f"\n{'='*60}")
        print(f"每周准确率更新任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        try:
            # 运行回测脚本
            print("\n运行回测脚本...")
            import subprocess
            result = subprocess.run(
                ['python', 'backend/scripts/backtest_patterns.py'],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print("✓ 回测完成")
                print(result.stdout)
            else:
                print("❌ 回测失败")
                print(result.stderr)

            # 淘汰低准确率模式
            print("\n淘汰低准确率模式...")
            self._deactivate_low_accuracy_patterns(threshold=40.0)

        except Exception as e:
            print(f"❌ 准确率更新失败: {e}")

    def monthly_pattern_discovery(self):
        """每月模式发现任务（场景一，$3.30）"""
        print(f"\n{'='*60}")
        print(f"每月模式发现任务开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        try:
            print("\n依次运行：")
            print("1. filter_classic_samples.py")
            print("2. classify_special_samples.py")
            print("3. extract_new_patterns.py")
            print("4. merge_patterns.py")

            scripts = [
                'backend/scripts/filter_classic_samples.py',
                'backend/scripts/classify_special_samples.py',
                'backend/scripts/extract_new_patterns.py',
                'backend/scripts/merge_patterns.py'
            ]

            for script in scripts:
                print(f"\n执行: {script}")
                import subprocess
                result = subprocess.run(
                    ['python', script],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    print("✓ 完成")
                else:
                    print(f"❌ 失败: {result.stderr}")
                    break

        except Exception as e:
            print(f"❌ 模式发现失败: {e}")

    def _load_patterns(self):
        """从数据库加载激活的模式"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT pattern_id, pattern_name, description, characteristics,
                   validated_success_rate, validation_sample_count
            FROM rising_patterns
            WHERE is_active = 1
        ''')

        patterns = []
        for row in cursor.fetchall():
            pattern = {
                'pattern_id': row[0],
                'pattern_name': row[1],
                'description': row[2],
                'characteristics': eval(row[3]) if row[3] else [],
                'validated_success_rate': row[4],
                'validation_sample_count': row[5]
            }
            patterns.append(pattern)

        conn.close()

        if len(patterns) == 0:
            # 降级：使用经典模式
            print("   数据库无激活模式，使用经典模式文件")
            classic_patterns = load_classic_patterns('classic_patterns.json')
            for p in classic_patterns:
                patterns.append({
                    'pattern_name': p['pattern_name'],
                    'description': p['description'],
                    'characteristics': []
                })

        return patterns

    def _deactivate_low_accuracy_patterns(self, threshold: float = 40.0):
        """淘汰低准确率模式"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE rising_patterns
            SET is_active = 0
            WHERE validated_success_rate < ?
                AND validated_success_rate IS NOT NULL
        ''', (threshold,))

        deactivated_count = cursor.rowcount

        conn.commit()
        conn.close()

        print(f"   淘汰了 {deactivated_count} 个低准确率模式（<{threshold}%）")

    def start(self):
        """启动定时任务"""
        print("🚀 启动模式识别定时任务")
        print("\n任务配置:")
        print("  - 每日预测: 每天 16:00")
        print("  - 准确率更新: 每周一 09:00")
        print("  - 模式发现: 每月1日 08:00")

        # 配置定时任务
        schedule.every().day.at("16:00").do(self.daily_prediction)
        schedule.every().monday.at("09:00").do(self.weekly_accuracy_update)
        schedule.every().month.at("08:00").do(self.monthly_pattern_discovery)

        print("\n⏰ 定时任务已配置，等待执行...")

        # 运行循环
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

def run_once_test():
    """运行一次测试"""
    print("测试模式 - 运行一次每日预测")
    scheduler = PatternScheduler()
    scheduler.daily_prediction()

if __name__ == '__main__':
    # 测试运行
    run_once_test()
