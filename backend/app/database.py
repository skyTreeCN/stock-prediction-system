import sqlite3
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta
import os
import json

class StockDatabase:
    """SQLite 数据库操作类"""

    def __init__(self, db_path: str = "../data/stocks.db"):
        self.db_path = db_path
        # 确保数据目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 创建股票K线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                close REAL,
                high REAL,
                low REAL,
                volume REAL,
                UNIQUE(code, date)
            )
        ''')

        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_code_date
            ON stock_data(code, date)
        ''')

        # 创建上涨模式表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rising_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_name TEXT NOT NULL,
                description TEXT,
                characteristics TEXT,
                example_stock_code TEXT,
                key_days TEXT,
                key_features TEXT,
                validated_success_rate REAL,
                validation_sample_count INTEGER,
                validation_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                pattern_id TEXT,
                pattern_type TEXT,
                parameters TEXT,
                match_rules TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # 创建股票池表 (SSE成分股等)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_pool (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                index_name TEXT,
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        # 创建股票池索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_stock_pool_active
            ON stock_pool(is_active)
        ''')

        # 创建预测结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_code TEXT NOT NULL,
                stock_name TEXT,
                prediction_date TEXT NOT NULL,
                matched_patterns TEXT,
                probability REAL,
                reasoning TEXT,
                actual_rise REAL,
                verified_date TEXT,
                is_success BOOLEAN,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建预测结果索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_predictions_date
            ON predictions(prediction_date)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_predictions_stock
            ON predictions(stock_code, prediction_date)
        ''')

        conn.commit()
        conn.close()

    def save_stock_data(self, df: pd.DataFrame):
        """批量保存股票数据"""
        conn = self.get_connection()
        df.to_sql('stock_data', conn, if_exists='append', index=False)
        conn.close()

    def save_single_stock_data(self, stock_data: dict):
        """保存单只股票的数据

        Args:
            stock_data: 字典格式的股票数据
                {
                    'code': 股票代码,
                    'name': 股票名称,
                    'dates': 日期列表,
                    'open': 开盘价列表,
                    'close': 收盘价列表,
                    'high': 最高价列表,
                    'low': 最低价列表,
                    'volume': 成交量列表
                }
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        code = stock_data['code']
        name = stock_data.get('name', code)

        # 批量插入数据
        for i in range(len(stock_data['dates'])):
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_data
                    (code, name, date, open, close, high, low, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    name,
                    stock_data['dates'][i],
                    stock_data['open'][i],
                    stock_data['close'][i],
                    stock_data['high'][i],
                    stock_data['low'][i],
                    stock_data['volume'][i]
                ))
            except Exception as e:
                print(f'保存数据失败 {code} {stock_data["dates"][i]}: {e}')

        conn.commit()
        conn.close()

    def get_stock_last_date(self, code: str) -> Optional[str]:
        """获取指定股票的最后日期

        Args:
            code: 股票代码

        Returns:
            最后日期字符串 (YYYY-MM-DD)，如果没有数据返回None
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT MAX(date) FROM stock_data WHERE code = ?
        ''', (code,))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result and result[0] else None

    def get_all_stock_codes(self) -> List[str]:
        """获取所有股票代码"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT code FROM stock_data')
        codes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return codes

    def get_stock_data(self, code: str, days: Optional[int] = None) -> pd.DataFrame:
        """获取指定股票的数据

        Args:
            code: 股票代码
            days: 获取最近多少天的数据，None表示全部
        """
        conn = self.get_connection()

        if days:
            query = '''
                SELECT * FROM stock_data
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            '''
            df = pd.read_sql_query(query, conn, params=(code, days))
        else:
            query = 'SELECT * FROM stock_data WHERE code = ? ORDER BY date DESC'
            df = pd.read_sql_query(query, conn, params=(code,))

        conn.close()
        return df

    def get_recent_data_all_stocks(self, days: int = 30) -> pd.DataFrame:
        """获取所有股票最近N天的数据"""
        conn = self.get_connection()

        # 获取每只股票最近N天的数据
        query = '''
            SELECT * FROM (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) as rn
                FROM stock_data
            )
            WHERE rn <= ?
            ORDER BY code, date DESC
        '''

        df = pd.read_sql_query(query, conn, params=(days,))
        conn.close()
        return df

    def get_rising_samples(self, sample_count: int = 50, rise_threshold: float = 0.08) -> pd.DataFrame:
        """获取历史上涨样本

        找出3个交易日后收盘价上涨≥指定阈值的案例（使用实际交易日，自动跳过周末和节假日）

        Args:
            sample_count: 样本数量
            rise_threshold: 上涨阈值，默认0.08 (8%)
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 获取所有候选基准日期（最近180天内，排除最近3个交易日）
        cursor.execute('''
            SELECT DISTINCT code, date, close, open, name
            FROM stock_data
            WHERE date >= date('now', '-180 days')
                AND date <= (
                    SELECT date FROM stock_data
                    ORDER BY date DESC
                    LIMIT 1 OFFSET 3
                )
                AND name NOT LIKE '%ST%'
                AND (close - open) / open > 0.01
            ORDER BY RANDOM()
        ''')

        candidates = cursor.fetchall()
        samples = []

        # 对每个候选日期，检查T+2交易日的涨幅
        for code, base_date, base_close, base_open, name in candidates:
            if len(samples) >= sample_count:
                break

            # 获取该股票在基准日之后的第2个交易日的收盘价
            cursor.execute('''
                SELECT date, close FROM stock_data
                WHERE code = ? AND date > ?
                ORDER BY date ASC
                LIMIT 2
            ''', (code, base_date))

            future_results = cursor.fetchall()

            # 检查是否有足够的未来交易日数据
            if len(future_results) >= 2:
                day2_date, day2_close = future_results[1]
                rise_ratio = (day2_close - base_close) / base_close

                # 如果涨幅符合要求，加入样本集
                if rise_ratio >= rise_threshold:
                    samples.append({
                        'code': code,
                        'date': base_date,
                        'close': base_close,
                        'open': base_open,
                        'name': name,
                        'day2_close': future_results[0][1] if len(future_results) > 0 else None,
                        'day3_close': day2_close,
                        'rise_pct': round(rise_ratio * 100, 2)
                    })

        conn.close()

        # 转换为DataFrame
        df = pd.DataFrame(samples)
        return df

    def get_validation_samples(self, days_back: int = 30, rise_threshold: float = 0.08) -> pd.DataFrame:
        """获取用于验证的历史样本（上个月的数据，使用实际交易日计算）

        Args:
            days_back: 往前推多少天，默认30天（约1个月）
            rise_threshold: 上涨阈值，默认0.08 (8%)

        Returns:
            包含完整3天数据的样本集
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 获取最近的日期
        cursor.execute('SELECT MAX(date) FROM stock_data')
        latest_date = cursor.fetchone()[0]

        if not latest_date:
            conn.close()
            return pd.DataFrame()

        # 获取验证日期范围内的候选数据
        cursor.execute('''
            SELECT code, date, close, open, high, low, volume, name
            FROM stock_data
            WHERE date BETWEEN date(?, '-{} days') AND date(?, '-30 days')
            ORDER BY code, date
        '''.format(days_back + 30), (latest_date, latest_date))

        candidates = cursor.fetchall()
        samples = []

        # 对每个候选日期，使用交易日逻辑计算T-1, T+1, T+2
        for code, base_date, base_close, base_open, base_high, base_low, base_volume, name in candidates:
            # 获取T-1交易日（前一个交易日）
            cursor.execute('''
                SELECT close FROM stock_data
                WHERE code = ? AND date < ?
                ORDER BY date DESC
                LIMIT 1
            ''', (code, base_date))
            prev_result = cursor.fetchone()
            prev_close = prev_result[0] if prev_result else None

            # 获取T+1和T+2交易日
            cursor.execute('''
                SELECT date, close, open FROM stock_data
                WHERE code = ? AND date > ?
                ORDER BY date ASC
                LIMIT 2
            ''', (code, base_date))

            future_results = cursor.fetchall()

            # 确保有足够的未来交易日数据
            if len(future_results) >= 2:
                day2_date, day2_close, day2_open = future_results[0]
                day3_date, day3_close, day3_open = future_results[1]

                rise_ratio = (day3_close - base_close) / base_close
                rise_pct = round(rise_ratio * 100, 2)
                amplitude = round((base_high - base_low) / base_low * 100, 2) if base_low > 0 else 0
                day_change_pct = round((base_close - base_open) / base_open * 100, 2) if base_open > 0 else 0
                is_success = 1 if rise_ratio >= rise_threshold else 0

                samples.append({
                    'code': code,
                    'date': base_date,
                    'close': base_close,
                    'open': base_open,
                    'high': base_high,
                    'low': base_low,
                    'volume': base_volume,
                    'name': name,
                    'prev_close': prev_close,
                    'day2_close': day2_close,
                    'day2_open': day2_open,
                    'day3_close': day3_close,
                    'rise_pct': rise_pct,
                    'amplitude': amplitude,
                    'day_change_pct': day_change_pct,
                    'is_success': is_success
                })

        conn.close()

        # 转换为DataFrame并按日期降序排列
        df = pd.DataFrame(samples)
        if not df.empty:
            df = df.sort_values('date', ascending=False)
        return df

    def get_future_rise(self, code: str, date: str, days: int = 3) -> Optional[float]:
        """
        查询指定股票在指定日期后N个交易日的涨幅（使用实际交易日，不包含周末和节假日）

        Args:
            code: 股票代码
            date: 基准日期
            days: 未来交易日天数(默认3个交易日,即T+3)

        Returns:
            涨幅百分比(如0.05表示5%),如果没有数据返回None（数据无效）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 步骤1：获取基准日的收盘价
        cursor.execute('''
            SELECT close FROM stock_data
            WHERE code = ? AND date = ?
        ''', (code, date))
        base_result = cursor.fetchone()

        if not base_result:
            conn.close()
            return None  # 数据无效

        base_close = float(base_result[0])

        # 步骤2：获取该股票在基准日之后的第N个交易日的日期和收盘价
        # 通过实际数据库中存在的交易日期来确定（自动跳过周末和节假日）
        cursor.execute('''
            SELECT date, close FROM stock_data
            WHERE code = ? AND date > ?
            ORDER BY date ASC
            LIMIT ?
        ''', (code, date, days))

        future_results = cursor.fetchall()
        conn.close()

        # 步骤3：如果有足够的未来交易日数据，取第N个交易日
        if len(future_results) >= days:
            future_close = float(future_results[days - 1][1])
            rise_ratio = (future_close - base_close) / base_close
            return rise_ratio

        return None  # 数据不足

    def save_patterns(self, patterns: List[dict]):
        """保存上涨模式"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 清空旧模式
        cursor.execute('DELETE FROM rising_patterns')

        # 插入新模式
        for pattern in patterns:
            # 提取 highlight_description 字段
            highlight = pattern.get('highlight_description', {})
            key_days = highlight.get('key_days', '')
            key_features = str(highlight.get('key_features', []))

            cursor.execute('''
                INSERT INTO rising_patterns (pattern_name, description, characteristics,
                                            example_stock_code, key_days, key_features,
                                            validated_success_rate, validation_sample_count, validation_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern['pattern_name'],
                pattern['description'],
                str(pattern['characteristics']),
                pattern.get('example_stock_code', ''),
                key_days,
                key_features,
                pattern.get('validated_success_rate'),
                pattern.get('validation_sample_count'),
                pattern.get('validation_date')
            ))

        conn.commit()
        conn.close()

    def get_patterns(self) -> List[dict]:
        """获取保存的上涨模式"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT pattern_name, description, characteristics,
                   example_stock_code, key_days, key_features,
                   validated_success_rate, validation_sample_count, validation_date
            FROM rising_patterns
            WHERE is_active = 1
        ''')

        patterns = []
        for row in cursor.fetchall():
            example_stock_code = row[3] if row[3] else None

            # 如果有示例股票代码，获取该股票的K线数据
            kline_data = []
            if example_stock_code:
                kline_data = self._get_stock_kline_data(cursor, example_stock_code, days=90)

            # 兜底逻辑：如果示例代码没有数据，或者没有示例代码，则随机获取
            if not kline_data:
                kline_data = self._get_sample_kline_data(cursor)

            # 安全解析characteristics和key_features
            try:
                characteristics = eval(row[2]) if row[2] and row[2].strip() else []
            except:
                characteristics = []

            try:
                key_features = eval(row[5]) if row[5] and row[5].strip() else []
            except:
                key_features = []

            patterns.append({
                'pattern_name': row[0],
                'description': row[1],
                'characteristics': characteristics,
                'example_stock_code': example_stock_code,
                'key_days': row[4],
                'key_features': key_features,
                'validated_success_rate': row[6],
                'validation_sample_count': row[7],
                'validation_date': row[8],
                'kline_data': kline_data,
                'annotations': None  # 修复：使用None而不是空列表
            })

        conn.close()
        return patterns

    def _get_sample_kline_data(self, cursor, days=90):
        """获取示例K线数据（随机股票的最近N天）"""
        cursor.execute('''
            SELECT DISTINCT code FROM stock_data
            ORDER BY RANDOM() LIMIT 1
        ''')
        stock = cursor.fetchone()
        if not stock:
            return []

        return self._get_stock_kline_data(cursor, stock[0], days)

    def _get_stock_kline_data(self, cursor, stock_code: str, days=90):
        """获取指定股票的K线数据（最近N天）"""
        cursor.execute('''
            SELECT date, open, high, low, close, volume
            FROM stock_data
            WHERE code = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (stock_code, days))

        rows = cursor.fetchall()
        return [{
            'date': r[0],
            'open': r[1],
            'high': r[2],
            'low': r[3],
            'close': r[4],
            'volume': r[5]
        } for r in reversed(rows)]  # 按时间正序

    def get_data_statistics(self) -> dict:
        """获取数据统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 股票数量
        cursor.execute('SELECT COUNT(DISTINCT code) FROM stock_data')
        stock_count = cursor.fetchone()[0]

        # 数据记录数
        cursor.execute('SELECT COUNT(*) FROM stock_data')
        record_count = cursor.fetchone()[0]

        # 日期范围
        cursor.execute('SELECT MIN(date), MAX(date) FROM stock_data')
        date_range = cursor.fetchone()

        # 股票池统计
        cursor.execute('SELECT COUNT(*) FROM stock_pool WHERE is_active = 1')
        pool_count = cursor.fetchone()[0]

        conn.close()

        return {
            'stock_count': stock_count,
            'record_count': record_count,
            'date_from': date_range[0],
            'date_to': date_range[1],
            'pool_count': pool_count
        }

    # ===== 股票池管理方法 =====

    def update_stock_pool(self, stocks: List[dict]):
        """更新股票池

        Args:
            stocks: 股票列表 [{'code': '600000', 'name': '浦发银行', 'index_name': 'SSE50'}, ...]
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 先标记所有为非激活
        cursor.execute('UPDATE stock_pool SET is_active = 0')

        # 批量插入或更新
        for stock in stocks:
            cursor.execute('''
                INSERT OR REPLACE INTO stock_pool (code, name, index_name, is_active)
                VALUES (?, ?, ?, 1)
            ''', (
                stock['code'],
                stock['name'],
                stock.get('index_name', 'SSE')
            ))

        conn.commit()
        conn.close()

    def get_stock_pool(self, active_only: bool = True) -> List[dict]:
        """获取股票池列表

        Args:
            active_only: 是否只返回激活的股票

        Returns:
            股票列表
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        if active_only:
            cursor.execute('''
                SELECT code, name, index_name, added_date
                FROM stock_pool
                WHERE is_active = 1
                ORDER BY code
            ''')
        else:
            cursor.execute('''
                SELECT code, name, index_name, added_date
                FROM stock_pool
                ORDER BY code
            ''')

        stocks = []
        for row in cursor.fetchall():
            stocks.append({
                'code': row[0],
                'name': row[1],
                'index_name': row[2],
                'added_date': row[3]
            })

        conn.close()
        return stocks

    def is_stock_pool_empty(self) -> bool:
        """检查股票池是否为空"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM stock_pool WHERE is_active = 1')
        count = cursor.fetchone()[0]
        conn.close()
        return count == 0

    def get_stock_pool_codes(self) -> List[str]:
        """获取股票池中的所有代码（仅激活的）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT code FROM stock_pool WHERE is_active = 1')
        codes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return codes

    def save_classic_patterns(self, patterns: List[dict]):
        """保存经典模式到数据库

        Args:
            patterns: 经典模式列表（来自classic_patterns.json）
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        for pattern in patterns:
            cursor.execute('''
                INSERT INTO rising_patterns
                (pattern_id, pattern_name, pattern_type, description,
                 parameters, match_rules, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                pattern['pattern_id'],
                pattern['pattern_name'],
                pattern['pattern_type'],
                pattern['description'],
                json.dumps(pattern['parameters'], ensure_ascii=False),
                json.dumps(pattern['match_rules'], ensure_ascii=False),
                pattern.get('is_active', True)
            ))

        conn.commit()
        conn.close()

    def get_samples_with_context(self, sample_ids: List[int] = None, days_before: int = 20) -> List[dict]:
        """获取样本及其前N天K线上下文

        Args:
            sample_ids: 样本ID列表，None表示获取所有
            days_before: 前N天数据

        Returns:
            样本列表，每个样本包含完整K线上下文
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        # 如果没有指定sample_ids，从rising_samples获取
        if sample_ids is None:
            cursor.execute('SELECT id, code, date FROM stock_data LIMIT 100')
        else:
            placeholders = ','.join('?' * len(sample_ids))
            cursor.execute(f'SELECT id, code, date FROM stock_data WHERE id IN ({placeholders})', sample_ids)

        samples = cursor.fetchall()
        result = []

        for sample_id, code, sample_date in samples:
            # 获取样本日前N天的K线数据
            cursor.execute('''
                SELECT date, open, high, low, close, volume
                FROM stock_data
                WHERE code = ?
                    AND date <= ?
                    AND date > date(?, '-{} days')
                ORDER BY date ASC
            '''.format(days_before), (code, sample_date, sample_date))

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

            if len(kline_data) >= min(10, days_before):  # 至少10天数据即可
                result.append({
                    'sample_id': sample_id,
                    'code': code,
                    'date': sample_date,
                    'kline_data': kline_data
                })

        conn.close()
        return result

    # ===== 预测结果管理方法 =====

    def save_prediction(self, prediction: dict):
        """保存预测结果
        
        Args:
            prediction: {
                'stock_code': str,
                'stock_name': str,
                'prediction_date': str,
                'matched_patterns': list,
                'probability': float,
                'reasoning': str
            }
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO predictions (
                stock_code, stock_name, prediction_date,
                matched_patterns, probability, reasoning
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            prediction['stock_code'],
            prediction.get('stock_name', ''),
            prediction['prediction_date'],
            str(prediction.get('matched_patterns', [])),
            prediction.get('probability', 0),
            prediction.get('reasoning', '')
        ))
        
        conn.commit()
        conn.close()
    
    def get_predictions(self, days: int = 30, verified_only: bool = False):
        """获取预测结果
        
        Args:
            days: 获取最近N天的预测
            verified_only: 是否只返回已验证的预测
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT id, stock_code, stock_name, prediction_date,
                   matched_patterns, probability, reasoning,
                   actual_rise, verified_date, is_success
            FROM predictions
            WHERE prediction_date >= date('now', '-{} days')
        '''.format(days)
        
        if verified_only:
            query += ' AND verified_date IS NOT NULL'
        
        query += ' ORDER BY prediction_date DESC, probability DESC'
        
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'stock_code': row[1],
                'stock_name': row[2],
                'prediction_date': row[3],
                'matched_patterns': eval(row[4]) if row[4] else [],
                'probability': row[5],
                'reasoning': row[6],
                'actual_rise': row[7],
                'verified_date': row[8],
                'is_success': row[9]
            })
        
        conn.close()
        return results
    
    def verify_prediction(self, prediction_id: int, actual_rise: float, verified_date: str):
        """验证预测结果
        
        Args:
            prediction_id: 预测ID
            actual_rise: 实际涨幅
            verified_date: 验证日期
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 判断是否成功(涨幅≥5%视为成功)
        is_success = 1 if actual_rise >= 0.05 else 0
        
        cursor.execute('''
            UPDATE predictions
            SET actual_rise = ?,
                verified_date = ?,
                is_success = ?
            WHERE id = ?
        ''', (actual_rise, verified_date, is_success, prediction_id))
        
        conn.commit()
        conn.close()
