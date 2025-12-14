"""
AI 模型配置文件
根据测试结果选择最优模型
"""

# AI 模型配置选项
AI_MODELS = {
    # 最佳平衡点 - 推荐用于生产环境
    "sonnet_4_5": {
        "model_id": "claude-sonnet-4-5-20250929",
        "name": "Sonnet 4.5",
        "accuracy_5p": 68,  # 5种模式准确率 (%)
        "accuracy_8p": 63,  # 8种模式准确率 (%)
        "cost_500": 1.02,   # 500样本成本 ($)
        "cost_1000": 2.00,  # 1000样本成本 ($)
        "cost_2000": 3.91,  # 2000样本成本 ($)
        "value_ratio": 34.0, # 性价比 (准确率/成本)
        "use_case": "生产环境,深度分析,高频交易"
    },

    # 高性价比备选
    "haiku_3_5": {
        "model_id": "claude-3-5-haiku-20241022",
        "name": "Haiku 3.5",
        "accuracy_5p": 53,
        "accuracy_8p": 48,
        "cost_500": 0.27,
        "cost_1000": 0.53,
        "cost_2000": 1.04,
        "value_ratio": 100.0,
        "use_case": "批量初筛,日常监控,成本敏感场景"
    },

    # 当前稳定版本 (回退选项)
    "haiku_3_0": {
        "model_id": "claude-3-haiku-20240307",
        "name": "Haiku 3.0",
        "accuracy_5p": 48,
        "accuracy_8p": 42,
        "cost_500": 0.27,
        "cost_1000": 0.53,
        "cost_2000": 1.04,
        "value_ratio": 177.8,
        "use_case": "稳定运行,测试通过"
    },

    # 高精度选项 (仅研发用)
    "opus_4_5": {
        "model_id": "claude-opus-4-5-20251101",
        "name": "Opus 4.5",
        "accuracy_5p": 78,
        "accuracy_8p": 73,
        "cost_500": 5.10,
        "cost_1000": 10.11,
        "cost_2000": 19.95,
        "value_ratio": 7.7,
        "use_case": "算法研发,策略验证"
    }
}

# 当前激活的模型 (修改此处切换模型)
# 选项: "sonnet_4_5" (推荐) | "haiku_3_5" | "haiku_3_0" (当前) | "opus_4_5"
ACTIVE_MODEL = "haiku_3_5"  # 测试 Haiku 3.5 (省钱)

# 样本量配置
SAMPLE_SIZES = {
    "test": 5,      # 测试模式
    "test50": 50,   # 测试: 50样本
    "test100": 100, # 阶段2测试: 100样本
    "small": 500,   # 成本优先,性价比最高
    "medium": 1000, # 平衡点,准确率提升明显
    "large": 2000   # 高准确率,边际收益低
}

# 推荐的样本量
RECOMMENDED_SAMPLE_SIZE = "medium"  # 实验3: 1000样本

# 模式数量配置
PATTERN_COUNTS = {
    "focused": 5,   # 推荐: 准确率更高,泛化能力强
    "detailed": 8   # 可选: 更细分,但准确率降低5-8%
}

# 推荐的模式数量
RECOMMENDED_PATTERN_COUNT = "focused"  # 5种模式

# 上涨样本筛选条件
RISE_THRESHOLD = 0.08  # 3天后收盘价上涨阈值: 8% (可调整为 0.06 或 0.10)


def get_active_model():
    """获取当前激活的模型配置"""
    return AI_MODELS.get(ACTIVE_MODEL)


def get_model_id():
    """获取当前模型ID"""
    model_config = get_active_model()
    if model_config:
        return model_config["model_id"]
    # 降级到 Haiku 3.0
    return AI_MODELS["haiku_3_0"]["model_id"]


def get_sample_size():
    """获取推荐的样本量"""
    return SAMPLE_SIZES.get(RECOMMENDED_SAMPLE_SIZE, 1000)


def get_pattern_count():
    """获取推荐的模式数量"""
    return PATTERN_COUNTS.get(RECOMMENDED_PATTERN_COUNT, 5)


def get_rise_threshold():
    """获取上涨阈值"""
    return RISE_THRESHOLD


def print_config_summary():
    """打印当前配置摘要"""
    model = get_active_model()
    sample_size = get_sample_size()
    pattern_count = get_pattern_count()
    rise_threshold = get_rise_threshold()

    cost_key = f"cost_{sample_size}"
    accuracy_key = f"accuracy_{pattern_count}p"

    print("\n" + "="*60)
    print("当前 AI 配置".center(60))
    print("="*60)
    print(f"\n模型: {model['name']} ({model['model_id']})")
    print(f"样本量: {sample_size} 条")
    print(f"模式数: {pattern_count} 种")
    print(f"上涨阈值: {rise_threshold*100}% (3天后)")
    print(f"\n预期性能:")
    print(f"  - 准确率: {model.get(accuracy_key, 'N/A')}%")
    print(f"  - 单次成本: ${model.get(cost_key, 'N/A')}")
    print(f"  - 性价比: {model['value_ratio']}")
    print(f"\n适用场景: {model['use_case']}")
    print(f"\n样本筛选: 3天后收盘价上涨 ≥ {rise_threshold*100}%")
    print("="*60 + "\n")


if __name__ == "__main__":
    # 测试配置
    print_config_summary()
