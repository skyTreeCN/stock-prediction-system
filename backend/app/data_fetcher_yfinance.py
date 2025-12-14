"""
Yahoo Finance数据获取器
使用yfinance库获取A股数据
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time
import random


class YahooFinanceDataFetcher:
    """使用Yahoo Finance获取股票数据"""

    def __init__(self, years: int = 3):
        """
        初始化Yahoo Finance数据获取器

        Args:
            years: 获取多少年的历史数据
        """
        self.years = years
        print(f'✓ Yahoo Finance 数据获取器初始化成功')
        print(f'✓ 将获取最近 {years} 年的数据')
        print(f'✓ 数据来源：Yahoo Finance')

    def _generate_stock_codes(self, count: int = 1000):
        """
        生成A股股票代码列表（覆盖沪深主要股票）

        Args:
            count: 目标股票数量

        Returns:
            股票代码列表（Yahoo Finance格式）
        """
        stock_list = []

        # 上交所主板 (600000-605000) - 约400只
        for code in range(600000, 600000 + 400):
            stock_list.append(f'{code}.SS')

        # 上交所科创板 (688000-689000) - 约100只
        for code in range(688000, 688000 + 100):
            stock_list.append(f'{code}.SS')

        # 深交所主板 (000001-002000) - 约250只
        for code in range(1, 1 + 250):
            stock_list.append(f'{code:06d}.SZ')

        # 深交所中小板 (002001-003000) - 约150只
        for code in range(2001, 2001 + 150):
            stock_list.append(f'{code:06d}.SZ')

        # 深交所创业板 (300001-301000) - 约100只
        for code in range(300001, 300001 + 100):
            stock_list.append(f'{code:06d}.SZ')

        # 随机打乱顺序，然后取前count个
        random.shuffle(stock_list)
        return stock_list[:count]

    def get_stock_list(self, limit: int = None):
        """
        获取股票列表（使用预定义列表或生成列表）

        Args:
            limit: 限制返回的股票数量（用于测试）

        Returns:
            股票代码列表（Yahoo Finance格式）
        """
        print('正在获取股票列表...')

        # 如果需要1000只股票，使用生成器
        if limit and limit >= 500:
            print(f'✓ 生成 {limit} 只股票代码...')
            return self._generate_stock_codes(limit)

        # 否则使用精选列表（高质量股票）
        # Yahoo Finance A股格式：
        # 上交所：代码.SS (例如：600000.SS)
        # 深交所：代码.SZ (例如：000001.SZ)
        stock_list = [
            # === 银行股（15只）===
            '600000.SS',  # 浦发银行
            '601398.SS',  # 工商银行
            '601939.SS',  # 建设银行
            '600036.SS',  # 招商银行
            '601288.SS',  # 农业银行
            '601328.SS',  # 交通银行
            '600016.SS',  # 民生银行
            '601166.SS',  # 兴业银行
            '601988.SS',  # 中国银行
            '601818.SS',  # 光大银行
            '601009.SS',  # 南京银行
            '000001.SZ',  # 平安银行
            '002142.SZ',  # 宁波银行
            '002839.SZ',  # 张家港行
            '601229.SS',  # 上海银行

            # === 白酒食品（20只）===
            '600519.SS',  # 贵州茅台
            '000858.SZ',  # 五粮液
            '000568.SZ',  # 泸州老窖
            '600809.SS',  # 山西汾酒
            '000799.SZ',  # 酒鬼酒
            '603369.SS',  # 今世缘
            '000596.SZ',  # 古井贡酒
            '600779.SS',  # 水井坊
            '600887.SS',  # 伊利股份
            '600600.SS',  # 青岛啤酒
            '000895.SZ',  # 双汇发展
            '603288.SS',  # 海天味业
            '000333.SZ',  # 美的集团
            '000651.SZ',  # 格力电器
            '002511.SZ',  # 中顺洁柔
            '600298.SS',  # 安琪酵母
            '603517.SS',  # 绝味食品
            '603345.SS',  # 安井食品
            '002847.SZ',  # 盐津铺子
            '603613.SS',  # 国联水产

            # === 地产建筑（15只）===
            '000002.SZ',  # 万科A
            '600048.SS',  # 保利发展
            '001979.SZ',  # 招商蛇口
            '600340.SS',  # 华夏幸福
            '000069.SZ',  # 华侨城A
            '600383.SS',  # 金地集团
            '600606.SS',  # 绿地控股
            '600663.SS',  # 陆家嘴
            '002146.SZ',  # 荣盛发展
            '000656.SZ',  # 金科股份
            '600376.SS',  # 首开股份
            '001872.SZ',  # 招商港口
            '600585.SS',  # 海螺水泥
            '600438.SS',  # 通威股份
            '601668.SS',  # 中国建筑

            # === 科技通信（30只）===
            '600276.SS',  # 恒瑞医药
            '000063.SZ',  # 中兴通讯
            '002415.SZ',  # 海康威视
            '300059.SZ',  # 东方财富
            '000725.SZ',  # 京东方A
            '002230.SZ',  # 科大讯飞
            '002241.SZ',  # 歌尔股份
            '002475.SZ',  # 立讯精密
            '300015.SZ',  # 爱尔眼科
            '300142.SZ',  # 沃森生物
            '300122.SZ',  # 智飞生物
            '300760.SZ',  # 迈瑞医疗
            '688111.SS',  # 金山办公
            '600570.SS',  # 恒生电子
            '002352.SZ',  # 顺丰控股
            '002624.SZ',  # 完美世界
            '002027.SZ',  # 分众传媒
            '300033.SZ',  # 同花顺
            '300413.SZ',  # 芒果超媒
            '603259.SS',  # 药明康德
            '002714.SZ',  # 牧原股份
            '002460.SZ',  # 赣锋锂业
            '603486.SS',  # 科沃斯
            '603501.SS',  # 韦尔股份
            '688981.SS',  # 中芯国际
            '300124.SZ',  # 汇川技术
            '002049.SZ',  # 紫光国微
            '002236.SZ',  # 大华股份
            '300699.SZ',  # 光威复材
            '300347.SZ',  # 泰格医药

            # === 新能源汽车（25只）===
            '002594.SZ',  # 比亚迪
            '300750.SZ',  # 宁德时代
            '002594.SZ',  # 比亚迪
            '601633.SS',  # 长城汽车
            '600104.SS',  # 上汽集团
            '000625.SZ',  # 长安汽车
            '002466.SZ',  # 天齐锂业
            '600884.SS',  # 杉杉股份
            '300014.SZ',  # 亿纬锂能
            '002129.SZ',  # 中环股份
            '600522.SS',  # 中天科技
            '002074.SZ',  # 国轩高科
            '300037.SZ',  # 新宙邦
            '603659.SS',  # 璞泰来
            '002812.SZ',  # 恩捷股份
            '300750.SZ',  # 宁德时代
            '688005.SS',  # 容百科技
            '300618.SZ',  # 寒锐钴业
            '002709.SZ',  # 天赐材料
            '603087.SS',  # 甘李药业
            '688599.SS',  # 天合光能
            '688223.SS',  # 晶科能源
            '300274.SZ',  # 阳光电源
            '300316.SZ',  # 晶盛机电
            '601012.SS',  # 隆基绿能

            # === 券商保险（15只）===
            '601318.SS',  # 中国平安
            '600030.SS',  # 中信证券
            '601688.SS',  # 华泰证券
            '600999.SS',  # 招商证券
            '600837.SS',  # 海通证券
            '601788.SS',  # 光大证券
            '600109.SS',  # 国金证券
            '601901.SS',  # 方正证券
            '000776.SZ',  # 广发证券
            '000166.SZ',  # 申万宏源
            '600918.SS',  # 中泰证券
            '601336.SS',  # 新华保险
            '601601.SS',  # 中国太保
            '601628.SS',  # 中国人寿
            '601319.SS',  # 中国人保

            # === 消费零售（20只）===
            '601888.SS',  # 中国中免
            '600415.SS',  # 小商品城
            '603233.SS',  # 大参林
            '603883.SS',  #老百姓
            '600612.SS',  # 老凤祥
            '600690.SS',  # 海尔智家
            '000977.SZ',  # 浪潮信息
            '002032.SZ',  # 苏泊尔
            '600055.SS',  # 万东医疗
            '002032.SZ',  # 苏泊尔
            '603899.SS',  # 晨光文具
            '002563.SZ',  # 森马服饰
            '603658.SS',  # 安图生物
            '300122.SZ',  # 智飞生物
            '300529.SZ',  # 健帆生物
            '300015.SZ',  # 爱尔眼科
            '002508.SZ',  # 老板电器
            '603486.SS',  # 科沃斯
            '603127.SS',  # 昭衍新药
            '603392.SS',  # 万泰生物

            # === 工业制造（25只）===
            '600031.SS',  # 三一重工
            '000333.SZ',  # 美的集团
            '000651.SZ',  # 格力电器
            '601888.SS',  # 中国中免
            '600690.SS',  # 海尔智家
            '601012.SS',  # 隆基绿能
            '600406.SS',  # 国电南瑞
            '601668.SS',  # 中国建筑
            '600028.SS',  # 中国石化
            '601857.SS',  # 中国石油
            '600900.SS',  # 长江电力
            '600089.SS',  # 特变电工
            '600019.SS',  # 宝钢股份
            '600309.SS',  # 万华化学
            '601012.SS',  # 隆基绿能
            '002459.SZ',  # 晶澳科技
            '601877.SS',  # 正泰电器
            '600436.SS',  # 片仔癀
            '600519.SS',  # 贵州茅台
            '000538.SZ',  # 云南白药
            '600196.SS',  # 复星医药
            '603259.SS',  # 药明康德
            '300347.SZ',  # 泰格医药
            '688185.SS',  # 康希诺
            '688363.SS',  # 华熙生物

            # === 其他蓝筹（20只）===
            '601398.SS',  # 工商银行
            '600028.SS',  # 中国石化
            '601857.SS',  # 中国石油
            '601988.SS',  # 中国银行
            '600900.SS',  # 长江电力
            '601088.SS',  # 中国神华
            '600019.SS',  # 宝钢股份
            '601390.SS',  # 中国中铁
            '601186.SS',  # 中国铁建
            '600050.SS',  # 中国联通
            '600029.SS',  # 南方航空
            '600115.SS',  # 中国东航
            '600585.SS',  # 海螺水泥
            '601899.SS',  # 紫金矿业
            '600547.SS',  # 山东黄金
            '601111.SS',  # 中国国航
            '600795.SS',  # 国电电力
            '600362.SS',  # 江西铜业
            '600606.SS',  # 绿地控股
            '600637.SS',  # 东方明珠
        ]

        if limit:
            stock_list = stock_list[:limit]

        print(f'✓ 获取到 {len(stock_list)} 只股票')
        print(f'  准备获取以下股票数据：')
        for i, code in enumerate(stock_list[:5]):
            print(f'  {i+1}. {code}')

        if len(stock_list) > 5:
            print(f'  ... 还有 {len(stock_list) - 5} 只股票')

        return stock_list

    def fetch_stock_data(self, stock_code: str, start_from: str = None):
        """
        获取单个股票的历史数据

        Args:
            stock_code: Yahoo Finance格式的股票代码 (例如: '600000.SS')
            start_from: 起始日期 (YYYY-MM-DD)，如果指定则从该日期开始获取，否则获取最近N年

        Returns:
            包含历史数据的字典
        """
        max_retries = 2
        for attempt in range(max_retries):
            try:
                # 计算日期范围
                end_date = datetime.now()
                if start_from:
                    # 增量更新：从指定日期开始
                    start_date = datetime.strptime(start_from, '%Y-%m-%d') + timedelta(days=1)
                else:
                    # 全量获取：获取最近N年
                    start_date = end_date - timedelta(days=self.years * 365)

                # 使用yfinance下载数据
                ticker = yf.Ticker(stock_code)
                df = ticker.history(
                    start=start_date,
                    end=end_date,
                    interval='1d'
                )

                if df is None or df.empty:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    print(f'  ✗ {stock_code}: 未获取到数据')
                    return None

                # 重置索引，使日期成为列
                df = df.reset_index()

                # 转换为标准格式
                # Yahoo Finance返回的列名：Date, Open, High, Low, Close, Volume
                stock_data = {
                    'code': stock_code.split('.')[0],  # 去掉.SS/.SZ后缀
                    'name': stock_code.split('.')[0],  # 简化处理
                    'dates': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
                    'open': df['Open'].tolist(),
                    'high': df['High'].tolist(),
                    'low': df['Low'].tolist(),
                    'close': df['Close'].tolist(),
                    'volume': df['Volume'].tolist(),
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

            # 避免请求过快
            if i < len(stock_codes):
                time.sleep(0.3)  # 每次延迟0.3秒

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
            stock_code: Yahoo Finance格式的股票代码
            days: 天数

        Returns:
            最近的数据
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            ticker = yf.Ticker(stock_code)
            df = ticker.history(start=start_date, end=end_date, interval='1d')

            if df is None or df.empty:
                return None

            df = df.reset_index()

            return {
                'code': stock_code.split('.')[0],
                'dates': df['Date'].dt.strftime('%Y-%m-%d').tolist(),
                'close': df['Close'].tolist(),
                'volume': df['Volume'].tolist(),
            }

        except Exception as e:
            print(f'获取 {stock_code} 最近数据失败: {e}')
            return None
