"""
AkShare数据获取器
使用AkShare免费获取A股数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import warnings
import ssl

# 忽略SSL警告
warnings.filterwarnings('ignore')

# 解决SSL证书验证问题
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AkShareDataFetcher:
    """使用AkShare获取免费股票数据"""

    def __init__(self, years: int = 3):
        """
        初始化AkShare数据获取器

        Args:
            years: 获取多少年的历史数据
        """
        self.years = years
        print(f'✓ AkShare 数据获取器初始化成功')
        print(f'✓ 将获取最近 {years} 年的数据')
        print(f'✓ 数据来源：东方财富、新浪财经、同花顺')

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

            # 尝试获取股票列表，带重试机制
            max_retries = 3
            df = None

            for attempt in range(max_retries):
                try:
                    print(f'  尝试 {attempt + 1}/{max_retries}...')
                    # 使用AkShare获取沪深A股列表
                    df = ak.stock_zh_a_spot_em()
                    if df is not None and not df.empty:
                        break
                except Exception as e:
                    print(f'  ✗ 获取失败: {str(e)[:100]}')
                    if attempt < max_retries - 1:
                        print(f'  等待2秒后重试...')
                        time.sleep(2)
                    else:
                        print(f'  ⚠️ 所有尝试都失败，使用预定义股票列表')
                        # 使用备用股票列表
                        return self._get_backup_stock_list(limit)

            if df is None or df.empty:
                print('✗ 未获取到股票列表，使用预定义列表')
                return self._get_backup_stock_list(limit)

            # 提取股票代码（AkShare返回的是6位代码，需要添加交易所后缀）
            stock_codes = []
            for _, row in df.iterrows():
                code = row['代码']
                name = row['名称']

                # 过滤ST股票
                if 'ST' in name or '退' in name:
                    continue

                # 添加交易所后缀
                # 6开头是上交所，0/3开头是深交所
                if code.startswith('6'):
                    stock_codes.append(code)  # 上交所，AkShare用6位代码
                elif code.startswith('0') or code.startswith('3'):
                    stock_codes.append(code)  # 深交所，AkShare用6位代码
                else:
                    continue

            if limit:
                stock_codes = stock_codes[:limit]
                print(f'✓ 获取到 {len(stock_codes)} 只股票（限制数量）')
            else:
                print(f'✓ 获取到 {len(stock_codes)} 只股票')

            # 显示前几个股票
            print(f'  准备获取以下股票数据：')
            for i in range(min(5, len(stock_codes))):
                code = stock_codes[i]
                # 获取股票名称
                stock_info = df[df['代码'] == code].iloc[0]
                print(f'  {i+1}. {code} - {stock_info["名称"]}')

            if len(stock_codes) > 5:
                print(f'  ... 还有 {len(stock_codes) - 5} 只股票')

            return stock_codes

        except Exception as e:
            print(f'✗ 获取股票列表失败: {e}')
            return self._get_backup_stock_list(limit)

    def _get_backup_stock_list(self, limit: int = None):
        """
        备用股票列表（当API获取失败时使用）

        Returns:
            预定义的优质股票代码列表
        """
        print('✓ 使用备用股票列表（优质蓝筹股）')

        # 精选的优质股票列表
        backup_stocks = [
            # 银行股（10只）
            '600000', '601398', '601939', '600036', '601288',
            '601328', '600016', '601166', '000001', '002142',

            # 白酒股（4只）
            '600519', '000858', '000568', '600809',

            # 地产股（3只）
            '000002', '600048', '001979',

            # 科技股（5只）
            '600276', '000063', '002415', '300059', '000725',

            # 新能源（3只）
            '600438', '002594', '300750',

            # 其他蓝筹（5只）
            '601318', '600030', '601888', '600887', '601857',
        ]

        if limit:
            backup_stocks = backup_stocks[:limit]

        print(f'  共 {len(backup_stocks)} 只备用股票')
        return backup_stocks

    def fetch_stock_data(self, stock_code: str):
        """
        获取单个股票的历史数据

        Args:
            stock_code: 6位股票代码 (例如: '600000')

        Returns:
            包含历史数据的字典
        """
        # 重试机制
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=self.years * 365)

                # 转换为字符串格式 YYYYMMDD
                start_date_str = start_date.strftime('%Y%m%d')
                end_date_str = end_date.strftime('%Y%m%d')

                # 使用AkShare获取日线数据
                # stock_zh_a_hist() 获取个股历史行情
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date_str,
                    end_date=end_date_str,
                    adjust="qfq"  # 前复权
                )

                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    print(f'  ✗ {stock_code}: 未获取到数据')
                    return None

                # AkShare返回的列名是中文，需要转换
                # 列名：日期、开盘、收盘、最高、最低、成交量、成交额、振幅、涨跌幅、涨跌额、换手率
                stock_data = {
                    'code': stock_code,
                    'name': stock_code,  # 简化处理，实际可以从股票列表获取
                    'dates': df['日期'].astype(str).tolist(),
                    'open': df['开盘'].tolist(),
                    'high': df['最高'].tolist(),
                    'low': df['最低'].tolist(),
                    'close': df['收盘'].tolist(),
                    'volume': df['成交量'].tolist(),
                }

                print(f'  ✓ {stock_code}: {len(df)} 条数据')
                return stock_data

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f'  ⚠️ {stock_code} 第{attempt+1}次尝试失败，重试中...')
                    time.sleep(1)
                else:
                    print(f'  ✗ {stock_code} 获取失败: {str(e)[:80]}')
                    return None

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

            # 避免请求过快，稍微延迟
            if i < len(stock_codes):
                time.sleep(0.5)  # 每次延迟0.5秒

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
            stock_code: 6位股票代码
            days: 天数

        Returns:
            最近的数据
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            start_date_str = start_date.strftime('%Y%m%d')
            end_date_str = end_date.strftime('%Y%m%d')

            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period="daily",
                start_date=start_date_str,
                end_date=end_date_str,
                adjust="qfq"
            )

            if df is None or df.empty:
                return None

            return {
                'code': stock_code,
                'dates': df['日期'].astype(str).tolist(),
                'close': df['收盘'].tolist(),
                'volume': df['成交量'].tolist(),
            }

        except Exception as e:
            print(f'获取 {stock_code} 最近数据失败: {e}')
            return None


def fetch_sse_component_stocks():
    """获取上交所成分股列表（SSE 50, SSE 180, SSE 380等）

    Returns:
        股票列表 [{'code': '600000', 'name': '浦发银行', 'index_name': 'SSE50'}, ...]
    """
    try:
        print('\n📊 开始获取上交所成分股...')
        all_stocks = []

        # 获取上证50成分股
        try:
            print('  获取上证50成分股...')
            df_sse50 = ak.index_stock_cons(symbol="000016")  # 上证50
            if df_sse50 is not None and not df_sse50.empty:
                for _, row in df_sse50.iterrows():
                    all_stocks.append({
                        'code': row['品种代码'],
                        'name': row['品种名称'],
                        'index_name': 'SSE50'
                    })
                print(f'    ✓ 上证50: {len(df_sse50)} 只')
            time.sleep(1)
        except Exception as e:
            print(f'    ✗ 获取上证50失败: {e}')

        # 获取上证180成分股
        try:
            print('  获取上证180成分股...')
            df_sse180 = ak.index_stock_cons(symbol="000010")  # 上证180
            if df_sse180 is not None and not df_sse180.empty:
                for _, row in df_sse180.iterrows():
                    code = row['品种代码']
                    # 避免重复（上证50的股票不重复添加）
                    if not any(s['code'] == code for s in all_stocks):
                        all_stocks.append({
                            'code': code,
                            'name': row['品种名称'],
                            'index_name': 'SSE180'
                        })
                print(f'    ✓ 上证180: {len(df_sse180)} 只')
            time.sleep(1)
        except Exception as e:
            print(f'    ✗ 获取上证180失败: {e}')

        # 获取上证380成分股（中小盘）
        try:
            print('  获取上证380成分股...')
            df_sse380 = ak.index_stock_cons(symbol="000009")  # 上证380
            if df_sse380 is not None and not df_sse380.empty:
                for _, row in df_sse380.iterrows():
                    code = row['品种代码']
                    if not any(s['code'] == code for s in all_stocks):
                        all_stocks.append({
                            'code': code,
                            'name': row['品种名称'],
                            'index_name': 'SSE380'
                        })
                print(f'    ✓ 上证380: {len(df_sse380)} 只')
            time.sleep(1)
        except Exception as e:
            print(f'    ✗ 获取上证380失败: {e}')

        # 如果以上都失败，使用备选方案：沪深300
        if len(all_stocks) == 0:
            try:
                print('  备选方案：获取沪深300成分股...')
                df_hs300 = ak.index_stock_cons(symbol="000300")  # 沪深300
                if df_hs300 is not None and not df_hs300.empty:
                    for _, row in df_hs300.iterrows():
                        code = row['品种代码']
                        # 只取上海的股票（6开头）
                        if code.startswith('6'):
                            all_stocks.append({
                                'code': code,
                                'name': row['品种名称'],
                                'index_name': 'HS300'
                            })
                    print(f'    ✓ 沪深300（上海）: {len(all_stocks)} 只')
            except Exception as e:
                print(f'    ✗ 获取沪深300失败: {e}')

        print(f'\n✅ 成功获取 {len(all_stocks)} 只上交所成分股')
        return all_stocks

    except Exception as e:
        print(f'❌ 获取上交所成分股失败: {e}')
        return []
