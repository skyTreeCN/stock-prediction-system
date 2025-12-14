"""
测试 Claude Sonnet 4.5 模型是否可用
运行方式: python test_model.py
"""
import os
from anthropic import Anthropic
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_model(model_name: str):
    """测试指定模型"""
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("❌ 错误: 未找到 ANTHROPIC_API_KEY 环境变量")
        return False

    print(f"\n{'='*60}")
    print(f"测试模型: {model_name}")
    print(f"{'='*60}")

    try:
        client = Anthropic(api_key=api_key)

        print("发送测试请求...")
        message = client.messages.create(
            model=model_name,
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "请用一句话介绍你自己,并说明你的模型名称"
                }
            ]
        )

        response = message.content[0].text

        print(f"✅ 成功! 模型响应:\n{response}")
        print(f"\n使用tokens: 输入={message.usage.input_tokens}, 输出={message.usage.output_tokens}")

        return True

    except Exception as e:
        print(f"❌ 失败! 错误信息:\n{str(e)}")
        return False


def main():
    print("\n" + "🔍 Claude 模型可用性测试".center(60, "="))

    # 测试模型列表
    models_to_test = [
        {
            "name": "claude-sonnet-4-5-20250929",
            "description": "Sonnet 4.5 (最佳平衡点 - 推荐)"
        },
        {
            "name": "claude-3-5-haiku-20241022",
            "description": "Haiku 3.5 (高性价比备选)"
        },
        {
            "name": "claude-3-haiku-20240307",
            "description": "Haiku 3.0 (当前使用)"
        }
    ]

    results = {}

    for model_info in models_to_test:
        model_name = model_info["name"]
        description = model_info["description"]

        print(f"\n📌 {description}")
        success = test_model(model_name)
        results[model_name] = success

    # 总结
    print(f"\n{'='*60}")
    print("测试总结".center(60))
    print(f"{'='*60}\n")

    for model_info in models_to_test:
        model_name = model_info["name"]
        description = model_info["description"]
        status = "✅ 可用" if results.get(model_name) else "❌ 不可用"
        print(f"{status} - {description}")
        print(f"   模型ID: {model_name}")

    # 推荐建议
    print(f"\n{'='*60}")
    print("推荐配置".center(60))
    print(f"{'='*60}\n")

    if results.get("claude-sonnet-4-5-20250929"):
        print("🏆 推荐: claude-sonnet-4-5-20250929 (Sonnet 4.5)")
        print("   - 准确率: 68% (1000样本 + 5种模式)")
        print("   - 成本: $2.00/次")
        print("   - 性价比: 34.0")
        print("   - 适用: 生产环境,深度分析")
        print("\n   ✅ Sonnet 4.5 可用! 建议立即切换")
    elif results.get("claude-3-5-haiku-20241022"):
        print("⚡ 备选: claude-3-5-haiku-20241022 (Haiku 3.5)")
        print("   - 准确率: 53% (1000样本)")
        print("   - 成本: $0.53/次")
        print("   - 性价比: 100.0")
        print("   - 适用: 批量初筛")
        print("\n   ⚠️  Sonnet 4.5 不可用,可使用 Haiku 3.5 作为升级选项")
    else:
        print("📌 保持当前: claude-3-haiku-20240307 (Haiku 3.0)")
        print("   - 当前稳定运行的模型")
        print("\n   ⚠️  新版模型暂不可用,建议稍后重试或联系 Anthropic 支持")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    main()
