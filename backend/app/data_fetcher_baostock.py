import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from typing import List
import time

class BaoStockDataFetcher:
    """使用 BaoStock 获取股票数据"""

    def __init__(self, years: int = 3):
        self.years = years
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        start = datetime.now() - timedelta(days=years * 365)
        self.start_date = start.strftime('%Y-%m-%d')
        self.logged_in = False

    def login(self, retries=3):
        """登录BaoStock，带重试机制"""
        if self.logged_in:
            return True

        for attempt in range(retries):
            try:
                print(f'正在登录 BaoStock... (尝试 {attempt + 1}/{retries})')
                lg = bs.login()
                if lg.error_code == '0':
                    print('✓ BaoStock 登录成功')
                    self.logged_in = True
                    return True
                else:
                    print(f'✗ BaoStock 登录失败: {lg.error_msg}')
                    if attempt < retries - 1:
                        print(f'等待3秒后重试...')
                        time.sleep(3)
            except Exception as e:
                print(f'登录异常: {e}')
                if attempt < retries - 1:
                    print(f'等待3秒后重试...')
                    time.sleep(3)

        print('❌ 多次尝试后仍无法连接到 BaoStock 服务器')
        return False

    def logout(self):
        """登出BaoStock"""
        if self.logged_in:
            bs.logout()
            self.logged_in = False
            print('✓ BaoStock 登出')

    def get_stock_list(self) -> pd.DataFrame:
        """获取上交所股票列表

        Returns:
            DataFrame with columns: code, name
        """
        if not self.login():
            return pd.DataFrame(columns=['code', 'name'])

        try:
            print("正在获取上交所股票列表...")

            # 获取证券基本资料
            rs = bs.query_stock_basic(code_name="")

            if rs.error_code != '0':
                print(f'获取股票列表失败: {rs.error_msg}')
                return pd.DataFrame(columns=['code', 'name'])

            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            result = pd.DataFrame(data_list, columns=rs.fields)

            # 筛选上交所股票（代码以sh.6开头）
            sh_stocks = result[result['code'].str.startswith('sh.6')].copy()

            # 重命名列并格式化
            sh_stocks['code'] = sh_stocks['code'].str.replace('sh.', '')
            sh_stocks = sh_stocks[['code', 'code_name']].rename(columns={'code_name': 'name'})

            print(f"✓ 获取到 {len(sh_stocks)} 只上交所股票")
            return sh_stocks

        except Exception as e:
            print(f"获取股票列表异常: {e}")
            return pd.DataFrame(columns=['code', 'name'])

    def fetch_stock_data(self, stock_code: str, stock_name: str) -> pd.DataFrame:
        """获取单只股票的历史数据

        Args:
            stock_code: 股票代码（如600000）
            stock_name: 股票名称

        Returns:
            DataFrame with K-line data
        """
        if not self.login():
            return pd.DataFrame()

        try:
            # BaoStock需要加上前缀
            bs_code = f"sh.{stock_code}"

            # 获取日K线数据
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=self.start_date,
                end_date=self.end_date,
                frequency="d",  # 日线
                adjustflag="2"  # 前复权
            )

            if rs.error_code != '0':
                print(f'获取 {stock_code} 数据失败: {rs.error_msg}')
                return pd.DataFrame()

            # 转换为DataFrame
            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return pd.DataFrame()

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 数据类型转换
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

            # 删除缺失数据
            df = df.dropna()

            # 添加股票信息
            df['code'] = stock_code
            df['name'] = stock_name

            # 调整列顺序
            df = df[['code', 'name', 'date', 'open', 'close', 'high', 'low', 'volume']]

            return df

        except Exception as e:
            print(f"获取股票 {stock_code} 数据异常: {e}")
            return pd.DataFrame()

    def fetch_all_stocks(self, limit: int = None) -> pd.DataFrame:
        """获取所有上交所股票的历史数据

        Args:
            limit: 限制获取的股票数量，用于测试

        Returns:
            DataFrame with all stocks data
        """
        stock_list = self.get_stock_list()

        if stock_list.empty:
            print("未获取到股票列表")
            return pd.DataFrame()

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

            # 适当延迟，避免请求过快
            if (idx + 1) % 10 == 0:
                print(f"已处理 {idx+1} 只，休息2秒...")
                time.sleep(2)
            else:
                time.sleep(0.5)

        # 登出
        self.logout()

        if all_data:
            result = pd.concat(all_data, ignore_index=True)
            print(f"✓ 成功获取 {len(all_data)} 只股票，共 {len(result)} 条数据")
            return result
        else:
            return pd.DataFrame()

    def fetch_recent_data(self, stock_code: str, days: int = 30) -> pd.DataFrame:
        """获取指定股票最近N天的数据"""
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days + 10)).strftime('%Y-%m-%d')

        if not self.login():
            return pd.DataFrame()

        try:
            bs_code = f"sh.{stock_code}"

            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="2"
            )

            if rs.error_code != '0':
                return pd.DataFrame()

            data_list = []
            while (rs.error_code == '0') & rs.next():
                data_list.append(rs.get_row_data())

            if not data_list:
                return pd.DataFrame()

            df = pd.DataFrame(data_list, columns=rs.fields)

            # 数据类型转换
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

            df = df.dropna()
            df['code'] = stock_code

            # 取最近N天
            df = df.tail(days)

            return df[['code', 'date', 'open', 'close', 'high', 'low', 'volume']]

        except Exception as e:
            print(f"获取最近数据失败 {stock_code}: {e}")
            return pd.DataFrame()
        finally:
            self.logout()
