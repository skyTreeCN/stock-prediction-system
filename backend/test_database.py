"""
数据库模块基础单元测试
"""
import pytest
import os
import tempfile
from app.database import StockDatabase


class TestStockDatabase:
    """测试StockDatabase类"""

    @pytest.fixture
    def temp_db(self):
        """创建临时测试数据库"""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        db = StockDatabase(db_path=path)
        yield db
        # 清理
        try:
            os.unlink(path)
        except:
            pass

    def test_database_initialization(self, temp_db):
        """测试数据库初始化"""
        assert temp_db is not None
        conn = temp_db.get_connection()
        assert conn is not None
        conn.close()

    def test_save_and_get_stock_data(self, temp_db):
        """测试保存和获取股票数据"""
        # 准备测试数据
        test_data = {
            'code': '600000',
            'name': '测试股票',
            'dates': ['2025-01-01', '2025-01-02'],
            'open': [10.0, 10.5],
            'close': [10.2, 10.8],
            'high': [10.5, 11.0],
            'low': [9.8, 10.3],
            'volume': [1000000, 1200000]
        }

        # 保存数据
        temp_db.save_stock_data(test_data)

        # 获取数据
        df = temp_db.get_stock_data('600000', days=10)

        # 验证
        assert len(df) == 2
        assert df['code'].iloc[0] == '600000'
        assert df['close'].iloc[0] == 10.2

    def test_get_stock_last_date(self, temp_db):
        """测试获取股票最后日期"""
        # 无数据时应返回None
        last_date = temp_db.get_stock_last_date('600000')
        assert last_date is None

        # 保存数据后应返回最后日期
        test_data = {
            'code': '600000',
            'name': '测试股票',
            'dates': ['2025-01-01', '2025-01-02'],
            'open': [10.0, 10.5],
            'close': [10.2, 10.8],
            'high': [10.5, 11.0],
            'low': [9.8, 10.3],
            'volume': [1000000, 1200000]
        }
        temp_db.save_stock_data(test_data)

        last_date = temp_db.get_stock_last_date('600000')
        assert last_date == '2025-01-02'

    def test_get_future_rise(self, temp_db):
        """测试获取未来涨幅"""
        # 准备连续数据
        test_data = {
            'code': '600000',
            'name': '测试股票',
            'dates': ['2025-01-01', '2025-01-02', '2025-01-03', '2025-01-06', '2025-01-07'],
            'open': [10.0, 10.5, 10.8, 11.0, 11.2],
            'close': [10.2, 10.8, 11.0, 11.5, 11.8],
            'high': [10.5, 11.0, 11.2, 11.8, 12.0],
            'low': [9.8, 10.3, 10.5, 10.8, 11.0],
            'volume': [1000000, 1200000, 1100000, 1300000, 1400000]
        }
        temp_db.save_stock_data(test_data)

        # 获取3天后涨幅
        rise = temp_db.get_future_rise('600000', '2025-01-01', days=3)

        # 验证（11.0 - 10.2) / 10.2 = 0.0784...
        assert rise is not None
        assert abs(rise - 0.0784) < 0.001

        # 数据不足时应返回None
        rise = temp_db.get_future_rise('600000', '2025-01-07', days=3)
        assert rise is None


def test_import():
    """测试模块导入"""
    from app import database
    assert database is not None
