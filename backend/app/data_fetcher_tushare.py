"""
Tushare数据获取器
使用Tushare API获取真实的A股数据
"""
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
import os
import time


class TushareDataFetcher:
    """使用Tushare获取真实股票数据"""

    def __init__(self, years: int = 3):
        """
        初始化Tushare数据获取器

        Args:
            years: 获取多少年的历史数据
        """
        self.years = years
        self.token = os.getenv("TUSHARE_TOKEN")

        if not self.token:
            raise ValueError("未找到TUSHARE_TOKEN环境变量，请在.env文件中配置")

        # 设置token
        ts.set_token(self.token)
        self.pro = ts.pro_api()

        print(f'✓ Tushare API 初始化成功')
        print(f'✓ 将获取最近 {years} 年的数据')

    def get_stock_list(self, limit: int = None):
        """
        获取股票列表

        Args:
            limit: 限制返回的股票数量（用于测试）

        Returns:
            股票代码列表
        """
        try:
            print('正在获取股票列表...')

            # 使用预定义的常用股票列表（不需要stock_basic接口权限）
            # 包含：银行、地产、白酒、科技、新能源等主流股票
            common_stocks = [
                # 银行股
                '600000.SH',  # 浦发银行
                '601398.SH',  # 工商银行
                '601939.SH',  # 建设银行
                '600036.SH',  # 招商银行
                '601288.SH',  # 农业银行
                '601328.SH',  # 交通银行
                '600016.SH',  # 民生银行
                '601166.SH',  # 兴业银行
                '000001.SZ',  # 平安银行
                '002142.SZ',  # 宁波银行

                # 白酒股
                '600519.SH',  # 贵州茅台
                '000858.SZ',  # 五粮液
                '000568.SZ',  # 泸州老窖
                '600809.SH',  # 山西汾酒

                # 地产股
                '000002.SZ',  # 万科A
                '600048.SH',  # 保利发展
                '001979.SZ',  # 招商蛇口

                # 科技股
                '600276.SH',  # 恒瑞医药
                '000063.SZ',  # 中兴通讯
                '002415.SZ',  # 海康威视
                '300059.SZ',  # 东方财富
                '000725.SZ',  # 京东方A

                # 新能源
                '600438.SH',  # 通威股份
                '002594.SZ',  # 比亚迪
                '300750.SZ',  # 宁德时代

                # 其他蓝筹
                '601318.SH',  # 中国平安
                '600030.SH',  # 中信证券
                '601888.SH',  # 中国中免
                '600887.SH',  # 伊利股份
            ]

            stock_codes = common_stocks

            if limit:
                stock_codes = stock_codes[:limit]
                print(f'✓ 使用预定义股票列表，共 {len(stock_codes)} 只股票（限制数量）')
            else:
                print(f'✓ 使用预定义股票列表，共 {len(stock_codes)} 只股票')

            # 显示前几个股票
            print(f'  准备获取以下股票数据：')
            for i, code in enumerate(stock_codes[:5]):
                print(f'  {i+1}. {code}')

            if len(stock_codes) > 5:
                print(f'  ... 还有 {len(stock_codes) - 5} 只股票')

            return stock_codes

        except Exception as e:
            print(f'✗ 获取股票列表失败: {e}')
            return []

    def fetch_stock_data(self, stock_code: str):
        """
        获取单个股票的历史数据

        Args:
            stock_code: Tushare格式的股票代码 (例如: '600000.SH')

        Returns:
            包含历史数据的字典
        """
        try:
            # 计算日期范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.years * 365)

            # 转换为Tushare日期格式 YYYYMMDD
            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')

            # 获取日线数据
            df = self.pro.daily(
                ts_code=stock_code,
                start_date=start_date_str,
                end_date=end_date_str
            )

            if df is None or df.empty:
                print(f'  ✗ {stock_code}: 未获取到数据')
                return None

            # 按日期升序排序
            df = df.sort_values('trade_date')

            # 转换为标准格式
            stock_data = {
                'code': stock_code,
                'name': stock_code.split('.')[0],  # 简化处理
                'dates': df['trade_date'].tolist(),
                'open': df['open'].tolist(),
                'high': df['high'].tolist(),
                'low': df['low'].tolist(),
                'close': df['close'].tolist(),
                'volume': df['vol'].tolist(),  # Tushare中是vol字段（单位：手）
            }

            print(f'  ✓ {stock_code}: {len(df)} 条数据')
            return stock_data

        except Exception as e:
            print(f'  ✗ {stock_code} 获取失败: {e}')
            return None

    def fetch_all_stocks(self, limit: int = None):
        """
        获取所有股票的历史数据

        Args:
            limit: 限制股票数量（用于测试）

        Returns:
            股票数据列表
        """
        stock_codes = self.get_stock_list(limit=limit)

        if not stock_codes:
            print('✗ 没有可获取的股票')
            return []

        print(f'\n开始获取 {len(stock_codes)} 只股票的历史数据...')
        print('=' * 50)

        all_data = []
        success_count = 0
        fail_count = 0

        for i, code in enumerate(stock_codes, 1):
            print(f'[{i}/{len(stock_codes)}] 获取 {code}...')

            data = self.fetch_stock_data(code)

            if data:
                all_data.append(data)
                success_count += 1
            else:
                fail_count += 1

            # Tushare有调用频率限制，普通用户200次/分钟
            # 为了安全起见，每次请求后稍微延迟
            if i < len(stock_codes):  # 最后一个不需要延迟
                time.sleep(0.35)  # 约170次/分钟，留有余量

        print('=' * 50)
        print(f'✓ 数据获取完成')
        print(f'  成功: {success_count} 只')
        print(f'  失败: {fail_count} 只')
        print(f'  总计: {len(all_data)} 只股票数据')

        return all_data

    def fetch_recent_data(self, stock_code: str, days: int = 30):
        """
        获取股票最近N天的数据

        Args:
            stock_code: Tushare格式的股票代码
            days: 天数

        Returns:
            最近的数据
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')

            df = self.pro.daily(
                ts_code=stock_code,
                start_date=start_date_str,
                end_date=end_date_str
            )

            if df is None or df.empty:
                return None

            df = df.sort_values('trade_date')

            return {
                'code': stock_code,
                'dates': df['trade_date'].tolist(),
                'close': df['close'].tolist(),
                'volume': df['vol'].tolist(),
            }

        except Exception as e:
            print(f'获取 {stock_code} 最近数据失败: {e}')
            return None
