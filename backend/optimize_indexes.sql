-- SQLite索引优化脚本
-- 基于代码分析和查询模式，添加必要的索引以提升性能

-- ========== stock_data表优化 ==========

-- 1. 优化get_recent_data_all_stocks() - 按code和date倒序查询
-- 当前已有: idx_code_date (code, date)
-- 优化: 添加date列的单独索引，用于全局日期范围查询
CREATE INDEX IF NOT EXISTS idx_stock_data_date
ON stock_data(date DESC);

-- 2. 优化RANDOM()查询 - get_rising_samples使用ORDER BY RANDOM()
-- 说明：SQLite的RANDOM()无法用索引优化，但可以通过DISTINCT code加速
CREATE INDEX IF NOT EXISTS idx_stock_data_code
ON stock_data(code);

-- 3. 优化name模糊查询 - 排除ST股票的查询
-- 虽然LIKE查询通常不能用索引，但可以通过覆盖索引优化
CREATE INDEX IF NOT EXISTS idx_stock_data_name
ON stock_data(name);

-- 4. 优化按日期范围查询 - get_validation_samples使用BETWEEN date
-- 复合索引优化：(date, code) 用于日期范围 + 分组查询
CREATE INDEX IF NOT EXISTS idx_stock_data_date_code
ON stock_data(date, code);


-- ========== rising_patterns表优化 ==========

-- 5. 优化模式查询 - get_patterns按is_active过滤
-- 当前没有索引，添加is_active索引
CREATE INDEX IF NOT EXISTS idx_patterns_active
ON rising_patterns(is_active);

-- 6. 优化模式按类型和ID查询 - 前端可能按pattern_id/pattern_type查询
CREATE INDEX IF NOT EXISTS idx_patterns_type
ON rising_patterns(pattern_type);

CREATE INDEX IF NOT EXISTS idx_patterns_id
ON rising_patterns(pattern_id);

-- 7. 覆盖索引优化 - 常用字段组合
-- 包含is_active + pattern_name用于快速过滤和排序
CREATE INDEX IF NOT EXISTS idx_patterns_active_name
ON rising_patterns(is_active, pattern_name);


-- ========== predictions表优化 ==========

-- 当前已有:
--   idx_predictions_date (prediction_date)
--   idx_predictions_stock (stock_code, prediction_date)

-- 8. 优化验证状态查询 - get_predictions按verified_date过滤
CREATE INDEX IF NOT EXISTS idx_predictions_verified
ON predictions(verified_date);

-- 9. 优化成功率统计 - 按is_success聚合查询
CREATE INDEX IF NOT EXISTS idx_predictions_success
ON predictions(is_success);

-- 10. 覆盖索引优化 - prediction_date + is_success组合
CREATE INDEX IF NOT EXISTS idx_predictions_date_success
ON predictions(prediction_date, is_success);


-- ========== stock_pool表优化 ==========

-- 当前已有: idx_stock_pool_active (is_active)

-- 11. 优化按index_name查询 - 前端可能按指数筛选
CREATE INDEX IF NOT EXISTS idx_stock_pool_index
ON stock_pool(index_name);

-- 12. 覆盖索引优化 - is_active + index_name组合查询
CREATE INDEX IF NOT EXISTS idx_stock_pool_active_index
ON stock_pool(is_active, index_name);


-- ========== 性能优化建议 ==========

-- 运行ANALYZE以更新统计信息，帮助查询优化器选择最佳索引
ANALYZE;

-- 清理数据库碎片，减少文件大小
VACUUM;
