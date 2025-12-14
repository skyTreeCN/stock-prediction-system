"""使用Haiku快速分类特殊样本"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import anthropic
from collections import defaultdict

def format_kline_for_prompt(kline_data):
    """格式化K线数据为简洁文本"""
    lines = []
    for i, day in enumerate(kline_data[-10:]):  # 只用最后10天
        lines.append(f"Day{i+1}: 开{day['open']:.2f} 高{day['high']:.2f} 低{day['low']:.2f} 收{day['close']:.2f} 量{day['volume']:.0f}")
    return "\n".join(lines)

def classify_samples(samples, api_key):
    """用Haiku对样本进行分类"""
    client = anthropic.Anthropic(api_key=api_key)

    # 准备分类prompt
    samples_text = []
    for i, sample in enumerate(samples[:100]):  # 限制100个样本
        kline_text = format_kline_for_prompt(sample['kline_data'])
        samples_text.append(f"\n样本{i+1} ({sample['code']} {sample['date']}):\n{kline_text}")

    prompt = f"""你是股票技术分析专家。以下是{len(samples_text)}个特殊上涨样本（已排除经典模式）。

请将这些样本分为2-3大类，每类应该有明显的共同特征。

{chr(10).join(samples_text)}

请输出JSON格式：
{{
  "categories": [
    {{
      "category_name": "类别名称",
      "description": "类别描述",
      "sample_indices": [样本序号列表]
    }}
  ]
}}"""

    message = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return message.content[0].text

def main():
    # 读取特殊样本
    with open('../../special_samples.json', 'r', encoding='utf-8') as f:
        special_samples = json.load(f)

    print(f"读取到 {len(special_samples)} 个特殊样本")

    if len(special_samples) == 0:
        print("没有特殊样本需要分类")
        return

    # 获取API密钥
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("错误：未设置 ANTHROPIC_API_KEY 环境变量")
        return

    print("开始使用Haiku进行分类...")
    result_text = classify_samples(special_samples, api_key)

    print("\nHaiku分类结果：")
    print(result_text)

    # 解析JSON结果
    try:
        # 提取JSON部分
        json_start = result_text.find('{')
        json_end = result_text.rfind('}') + 1
        json_text = result_text[json_start:json_end]

        result = json.loads(json_text)

        # 构建分类结果
        categories = []
        for cat in result['categories']:
            sample_list = []
            for idx in cat['sample_indices']:
                if 0 <= idx-1 < len(special_samples):
                    sample_list.append(special_samples[idx-1])

            categories.append({
                'category_name': cat['category_name'],
                'description': cat['description'],
                'sample_count': len(sample_list),
                'samples': sample_list
            })

        # 保存分类结果
        output = {
            'total_samples': len(special_samples),
            'categories': categories,
            'raw_response': result_text
        }

        output_file = '../../sample_categories.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n分类结果已保存到: {output_file}")
        print(f"共分为 {len(categories)} 类:")
        for cat in categories:
            print(f"  - {cat['category_name']}: {cat['sample_count']} 个样本")

    except Exception as e:
        print(f"解析结果失败: {e}")
        # 保存原始响应
        with open('../../classification_raw.txt', 'w', encoding='utf-8') as f:
            f.write(result_text)

if __name__ == '__main__':
    main()
