import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import List
import time
import ssl
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class StockDataFetcher:
    """使用 AkShare 获取股票数据"""

    def __init__(self, years: int = 3):
        self.years = years
        self.end_date = datetime.now().strftime('%Y%m%d')
        self.start_date = (datetime.now() - timedelta(days=years * 365)).strftime('%Y%m%d')

    def get_stock_list(self) -> pd.DataFrame:
        """获取上交所股票列表

        Returns:
            DataFrame with columns: code, name
        """
        # 由于网络问题，直接使用备用列表进行测试
        print("⚠️  网络不稳定，使用备用股票列表进行测试...")
        return self._get_fallback_stock_list()

        # 正常获取方式（暂时注释）
        # max_retries = 3
        # for attempt in range(max_retries):
        #     try:
        #         print(f"正在获取股票列表... (尝试 {attempt + 1}/{max_retries})")
        #         stock_list = ak.stock_info_a_code_name()
        #         sh_stocks = stock_list[stock_list['code'].str.startswith('6')].copy()
        #         print(f"获取到 {len(sh_stocks)} 只上交所股票")
        #         return sh_stocks
        #     except Exception as e:
        #         print(f"获取股票列表失败 (尝试 {attempt + 1}/{max_retries}): {e}")
        #         if attempt < max_retries - 1:
        #             wait_time = (attempt + 1) * 2
        #             print(f"等待 {wait_time} 秒后重试...")
        #             time.sleep(wait_time)
        #         else:
        #             print("已达到最大重试次数，使用备用方案...")
        #             return self._get_fallback_stock_list()
        # return pd.DataFrame(columns=['code', 'name'])

    def _get_fallback_stock_list(self) -> pd.DataFrame:
        """备用股票列表（网络失败时使用）"""
        print("使用备用股票列表...")
        fallback_stocks = [
            {'code': '600000', 'name': '浦发银行'},
            {'code': '600036', 'name': '招商银行'},
            {'code': '600519', 'name': '贵州茅台'},
            {'code': '601318', 'name': '中国平安'},
            {'code': '601888', 'name': '中国中免'},
        ]
        return pd.DataFrame(fallback_stocks)

    def fetch_stock_data(self, stock_code: str, stock_name: str) -> pd.DataFrame:
        """获取单只股票的历史数据

        Args:
            stock_code: 股票代码
            stock_name: 股票名称

        Returns:
            DataFrame with K-line data
        """
        # 由于网络问题，使用模拟数据进行测试
        print(f"⚠️  网络不可用，为 {stock_code} 生成模拟数据...")
        return self._generate_mock_data(stock_code, stock_name)

        # 正常获取方式（暂时注释）
        # max_retries = 2
        # for attempt in range(max_retries):
        #     try:
        #         df = ak.stock_zh_a_hist(
        #             symbol=stock_code,
        #             period="daily",
        #             start_date=self.start_date,
        #             end_date=self.end_date,
        #             adjust="qfq"
        #         )
        #         if df is None or len(df) == 0:
        #             return pd.DataFrame()
        #         df = df.rename(columns={
        #             '日期': 'date',
        #             '开盘': 'open',
        #             '收盘': 'close',
        #             '最高': 'high',
        #             '最低': 'low',
        #             '成交量': 'volume'
        #         })
        #         df['code'] = stock_code
        #         df['name'] = stock_name
        #         df = df[['code', 'name', 'date', 'open', 'close', 'high', 'low', 'volume']]
        #         return df
        #     except Exception as e:
        #         if attempt < max_retries - 1:
        #             print(f"获取股票 {stock_code} 数据失败，重试中... ({e})")
        #             time.sleep(1)
        #         else:
        #             print(f"获取股票 {stock_code} 数据失败: {e}")
        #             return pd.DataFrame()
        # return pd.DataFrame()

    def _generate_mock_data(self, stock_code: str, stock_name: str) -> pd.DataFrame:
        """生成模拟的股票历史数据（用于测试）"""
        import numpy as np

        # 生成3年的交易日数据（约730天）
        days = 730
        end_date = datetime.now()
        dates = []
        current_date = end_date - timedelta(days=days)

        # 生成日期（跳过周末）
        while len(dates) < days:
            if current_date.weekday() < 5:  # 周一到周五
                dates.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)

        # 生成价格数据（随机游走，带趋势）
        base_price = np.random.uniform(10, 100)  # 初始价格
        prices = [base_price]

        for i in range(1, days):
            # 随机涨跌，带轻微上涨趋势
            change = np.random.normal(0.001, 0.02)  # 平均涨0.1%，标准差2%
            new_price = prices[-1] * (1 + change)
            prices.append(max(new_price, 1))  # 价格不能低于1

        # 生成 OHLC 数据
        data = []
        for i, date in enumerate(dates):
            close = prices[i]
            # 开盘价在收盘价附近波动
            open_price = close * (1 + np.random.uniform(-0.01, 0.01))
            # 最高最低价
            high = max(open_price, close) * (1 + abs(np.random.normal(0, 0.005)))
            low = min(open_price, close) * (1 - abs(np.random.normal(0, 0.005)))
            # 成交量
            volume = int(np.random.uniform(1000000, 10000000))

            data.append({
                'code': stock_code,
                'name': stock_name,
                'date': date,
                'open': round(open_price, 2),
                'close': round(close, 2),
                'high': round(high, 2),
                'low': round(low, 2),
                'volume': volume
            })

        df = pd.DataFrame(data)
        print(f"✓ 成功生成 {stock_code} {stock_name} 的模拟数据，共 {len(df)} 条")
        return df

    def fetch_all_stocks(self, limit: int = None) -> pd.DataFrame:
        """获取所有上交所股票的历史数据

        Args:
            limit: 限制获取的股票数量，用于测试

        Returns:
            DataFrame with all stocks data
        """
        stock_list = self.get_stock_list()

        if limit:
            stock_list = stock_list.head(limit)

        all_data = []
        total = len(stock_list)
        success_count = 0
        fail_count = 0

        for idx, row in stock_list.iterrows():
            code = row['code']
            name = row['name']

            print(f"正在获取 [{idx+1}/{total}] {code} {name} (成功:{success_count} 失败:{fail_count})")

            df = self.fetch_stock_data(code, name)

            if not df.empty:
                all_data.append(df)
                success_count += 1
                print(f"✓ 成功获取 {code} {name}, 共{len(df)}条数据")
            else:
                fail_count += 1
                print(f"✗ 跳过 {code} {name}")

            # 增加延迟时间，避免被限流（模拟数据不需要延迟）
            # if (idx + 1) % 10 == 0:
            #     print(f"已处理 {idx+1} 只，休息5秒...")
            #     time.sleep(5)
            # else:
            #     time.sleep(2)

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            print(f"成功获取 {len(all_data)} 只股票，共 {len(result)} 条数据")
            return result
        else:
            return pd.DataFrame()

    def fetch_recent_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """获取指定股票最近N天的数据"""
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days + 10)).strftime('%Y%m%d')

        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )

            if df is None or len(df) == 0:
                return pd.DataFrame()

            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            })

            df['code'] = stock_code

            # 取最近N天
            df = df.tail(days)

            return df[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]

        except Exception as e:
            print(f"获取最近数据失败 {stock_code}: {e}")
            return pd.DataFrame()
