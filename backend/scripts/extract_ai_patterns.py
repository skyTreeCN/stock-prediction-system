"""阶段四：AI提取模式
使用Sonnet 4.5分析每个簇,提取共性特征定义新模式
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import anthropic
from dotenv import load_dotenv

# 加载.env文件
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def analyze_cluster_with_ai(cluster_samples, cluster_id, cluster_stats):
    """使用Claude Sonnet 4.5分析簇样本,提取模式

    Args:
        cluster_samples: 簇样本列表（包含完整K线数据）
        cluster_id: 簇ID
        cluster_stats: 簇的统计特征

    Returns:
        提取的模式定义字典
    """
    # Prepare prompt in English to avoid encoding issues
    prompt = f"""You are a senior quantitative analyst. Analyze the following {len(cluster_samples)} stock rise samples and extract common patterns.

**Cluster Statistics**:
- Volatility: {cluster_stats['volatility']:.4f}
- Volume Trend: {cluster_stats['volume_trend']:.2f}x
- Momentum: {cluster_stats['momentum']:.2%}
- Total Rise: {cluster_stats['total_rise']:.2%}

**Sample Data** (first 5 samples with K-line data):
{json.dumps(cluster_samples[:5], ensure_ascii=False, indent=2)}

**Requirements**:
1. Analyze the common K-line patterns in these samples
2. Identify key price and volume characteristics
3. Define a programmatically implementable rise pattern
4. Output in JSON format with:
   - pattern_name: Pattern name (concise Chinese)
   - description: Pattern description (Chinese)
   - parameters: Key parameters (thresholds, ratios, days, etc.)
   - match_rules: Matching rules (step-by-step description in Chinese)

**Notes**:
- Pattern must be reproducible and programmatically implementable
- Parameters should be based on actual data statistics
- Avoid overfitting, maintain moderate generalization

Please output the pattern definition in JSON format directly, no other text.
"""

    # 调用Claude API
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    # 解析响应
    response_text = message.content[0].text

    # 提取JSON（可能包含在markdown代码块中）
    if "```json" in response_text:
        json_start = response_text.find("```json") + 7
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()
    elif "```" in response_text:
        json_start = response_text.find("```") + 3
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()

    pattern = json.loads(response_text)

    # 添加元数据
    pattern["pattern_id"] = f"AI{cluster_id:03d}"
    pattern["pattern_type"] = "ai_discovered"
    pattern["is_active"] = True
    pattern["cluster_id"] = cluster_id
    pattern["cluster_size"] = len(cluster_samples)
    pattern["cluster_stats"] = cluster_stats

    return pattern


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 加载聚类结果
    clustered_file = os.path.join(script_dir, '..', '..', 'clustered_samples.json')
    with open(clustered_file, 'r', encoding='utf-8') as f:
        clustered_data = json.load(f)

    # 加载特殊样本（包含完整K线数据）
    special_file = os.path.join(script_dir, '..', '..', 'special_samples.json')
    with open(special_file, 'r', encoding='utf-8') as f:
        special_samples = json.load(f)

    # 加载特征向量（用于统计信息）
    features_file = os.path.join(script_dir, '..', '..', 'feature_vectors.json')
    with open(features_file, 'r', encoding='utf-8') as f:
        features_data = json.load(f)

    # 创建样本ID到完整数据的映射
    sample_map = {s['sample_id']: s for s in special_samples}
    feature_map = {f['sample_id']: f['features'] for f in features_data}

    print("Starting AI pattern extraction...")
    print(f"API Key configured: {'ANTHROPIC_API_KEY' in os.environ}")

    new_patterns = []
    total_cost = 0

    # 分析每个簇
    for cluster_key, cluster_info in clustered_data.items():
        cluster_id = cluster_info['cluster_id']
        sample_count = cluster_info['sample_count']

        print(f"\nAnalyzing Cluster {cluster_id} ({sample_count} samples)...")

        # 获取簇内样本的完整数据
        cluster_samples = []
        for sample_ref in cluster_info['samples']:
            sample_id = sample_ref['sample_id']
            if sample_id in sample_map:
                cluster_samples.append(sample_map[sample_id])

        # 计算簇的统计特征
        cluster_features = [feature_map[s['sample_id']] for s in cluster_samples if s['sample_id'] in feature_map]
        cluster_stats = {
            'volatility': sum(f['volatility'] for f in cluster_features) / len(cluster_features),
            'volume_trend': sum(f['volume_trend'] for f in cluster_features) / len(cluster_features),
            'momentum': sum(f['momentum'] for f in cluster_features) / len(cluster_features),
            'total_rise': sum(f['total_rise'] for f in cluster_features) / len(cluster_features),
        }

        # 用AI提取模式
        try:
            pattern = analyze_cluster_with_ai(cluster_samples, cluster_id, cluster_stats)
            new_patterns.append(pattern)

            print(f"  OK Pattern extracted: {pattern['pattern_name']}")
            print(f"    Description: {pattern['description']}")

            # 估算成本（Sonnet 4.5约$3/MTok输入，$15/MTok输出）
            # 每次约2K输入token，1K输出token
            cost_per_call = (2000 * 3 + 1000 * 15) / 1000000
            total_cost += cost_per_call

        except Exception as e:
            print(f"  X Extraction failed: {e}")

    # 保存新模式
    output_file = os.path.join(script_dir, '..', '..', 'new_patterns.json')
    output_data = {
        "patterns": new_patterns,
        "metadata": {
            "version": "1.0",
            "created_date": "2025-12-11",
            "method": "AI extraction with Claude Sonnet 4.5",
            "cluster_count": len(clustered_data),
            "total_samples": sum(c['sample_count'] for c in clustered_data.values()),
            "estimated_cost": f"${total_cost:.2f}"
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nAI pattern extraction completed!")
    print(f"  Patterns extracted: {len(new_patterns)}")
    print(f"  Output file: {output_file}")
    print(f"  Estimated cost: ${total_cost:.2f}")


if __name__ == '__main__':
    main()
