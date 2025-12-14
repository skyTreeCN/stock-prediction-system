"""使用Sonnet从最大类别中提取新模式"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import anthropic

def format_full_kline(kline_data):
    """格式化完整20天K线数据"""
    lines = []
    for i, day in enumerate(kline_data):
        lines.append(f"Day{i+1} {day['date']}: 开{day['open']:.2f} 高{day['high']:.2f} 低{day['low']:.2f} 收{day['close']:.2f} 量{day['volume']:.0f}")
    return "\n".join(lines)

def extract_patterns(category_samples, category_name, api_key):
    """用Sonnet从样本中提取模式"""
    client = anthropic.Anthropic(api_key=api_key)

    # 准备样本数据（最多50个）
    samples_text = []
    for i, sample in enumerate(category_samples[:50]):
        kline_text = format_full_kline(sample['kline_data'])
        samples_text.append(f"\n=== 样本{i+1}: {sample['code']} {sample['date']} ===\n{kline_text}")

    prompt = f"""你是高级股票技术分析专家。以下是{len(samples_text)}个属于"{category_name}"类别的上涨样本，每个样本包含20天完整K线数据。

{chr(10).join(samples_text)}

请深度分析这些样本，提取1-2个可程序化验证的上涨模式。

要求：
1. 模式必须有清晰的量化参数（天数、涨跌幅、成交量倍数等）
2. 必须可通过程序代码验证
3. 模式应该与经典的"缩量震荡突破"、"V型反转"、"连续放量"明显不同
4. 给出每个模式的关键特征和匹配规则

请输出JSON格式：
{{
  "patterns": [
    {{
      "pattern_id": "P004",
      "pattern_name": "模式名称",
      "pattern_type": "ai_discovered",
      "description": "模式描述",
      "parameters": {{
        "param1": {{"min": 值, "max": 值}},
        "param2": {{"min": 值}}
      }},
      "match_rules": {{
        "step1": "规则1",
        "step2": "规则2"
      }},
      "is_active": true
    }}
  ]
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text

def main():
    # 读取分类结果
    with open('../../sample_categories.json', 'r', encoding='utf-8') as f:
        categories_data = json.load(f)

    categories = categories_data['categories']
    print(f"读取到 {len(categories)} 个类别")

    # 找到样本数最多的类别
    largest_category = max(categories, key=lambda x: x['sample_count'])
    print(f"\n最大类别: {largest_category['category_name']}")
    print(f"样本数量: {largest_category['sample_count']}")
    print(f"描述: {largest_category['description']}")

    # 获取API密钥
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("错误：未设置 ANTHROPIC_API_KEY 环境变量")
        return

    print("\n开始使用Sonnet提取新模式...")
    result_text = extract_patterns(
        largest_category['samples'],
        largest_category['category_name'],
        api_key
    )

    print("\nSonnet提取结果：")
    print(result_text)

    # 解析JSON结果
    try:
        # 提取JSON部分
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_text = result_text[json_start:json_end]

        result = json.loads(json_text)

        # 保存新模式
        output_file = '../../new_patterns.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n新模式已保存到: {output_file}")
        print(f"提取了 {len(result['patterns'])} 个新模式:")
        for pattern in result['patterns']:
            print(f"  - {pattern['pattern_id']}: {pattern['pattern_name']}")

        # 自动合并模式到数据库
        print("\n自动合并模式到数据库...")
        try:
            import merge_patterns
            merge_patterns.main()
        except Exception as merge_error:
            print(f"⚠️  自动合并失败: {merge_error}")
            print("请手动运行: python merge_patterns.py")

    except Exception as e:
        print(f"解析结果失败: {e}")
        # 保存原始响应
        with open('../../extraction_raw.txt', 'w', encoding='utf-8') as f:
            f.write(result_text)

if __name__ == '__main__':
    main()
