"""阶段三': 程序化聚类（替代Haiku分类）
使用K-means对106个特殊样本进行聚类分组
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import json
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

def find_optimal_clusters(features_df, max_clusters=8):
    """使用肘部法则和轮廓系数找到最优簇数

    Args:
        features_df: 标准化后的特征DataFrame
        max_clusters: 最大簇数

    Returns:
        最优簇数
    """
    inertias = []
    silhouette_scores = []

    for k in range(2, min(max_clusters + 1, len(features_df))):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(features_df)

        inertias.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(features_df, labels))

    # 找到轮廓系数最高的k
    best_k = silhouette_scores.index(max(silhouette_scores)) + 2

    print("\nCluster evaluation:")
    for i, k in enumerate(range(2, min(max_clusters + 1, len(features_df)))):
        print(f"  k={k}: inertia={inertias[i]:.2f}, silhouette={silhouette_scores[i]:.4f}")

    print(f"\nOptimal k (by silhouette score): {best_k}")

    return best_k


def main():
    # 加载特征向量
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, '..', '..', 'feature_vectors.json')

    print("Loading feature vectors...")
    with open(input_file, 'r', encoding='utf-8') as f:
        sample_features = json.load(f)

    print(f"Total samples: {len(sample_features)}")

    # 转换为DataFrame
    features_list = []
    for sample in sample_features:
        features_list.append(sample['features'])

    features_df = pd.DataFrame(features_list)
    print(f"\nFeatures: {list(features_df.columns)}")

    # 标准化特征
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features_df)
    features_scaled_df = pd.DataFrame(features_scaled, columns=features_df.columns)

    # 找到最优簇数
    optimal_k = find_optimal_clusters(features_scaled_df, max_clusters=8)

    # 用最优k进行聚类
    print(f"\nClustering with k={optimal_k}...")
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    labels = kmeans.fit_predict(features_scaled_df)

    # 添加簇标签到样本
    for i, sample in enumerate(sample_features):
        sample['cluster'] = int(labels[i])

    # 统计每个簇的样本数
    cluster_counts = pd.Series(labels).value_counts().sort_index()
    print("\nCluster distribution:")
    for cluster_id, count in cluster_counts.items():
        pct = count / len(sample_features) * 100
        print(f"  Cluster {cluster_id}: {count} samples ({pct:.1f}%)")

    # 分析每个簇的特征
    print("\nCluster characteristics:")
    for cluster_id in range(optimal_k):
        cluster_samples = [s for s in sample_features if s['cluster'] == cluster_id]
        cluster_features = pd.DataFrame([s['features'] for s in cluster_samples])

        print(f"\nCluster {cluster_id} ({len(cluster_samples)} samples):")
        print(f"  Volatility: {cluster_features['volatility'].mean():.4f}")
        print(f"  Volume trend: {cluster_features['volume_trend'].mean():.4f}")
        print(f"  Momentum: {cluster_features['momentum'].mean():.4f}")
        print(f"  Total rise: {cluster_features['total_rise'].mean():.4f}")

    # 按簇重新组织数据
    clustered_data = {}
    for cluster_id in range(optimal_k):
        cluster_samples = [s for s in sample_features if s['cluster'] == cluster_id]

        clustered_data[f"cluster_{cluster_id}"] = {
            "cluster_id": cluster_id,
            "sample_count": len(cluster_samples),
            "samples": [
                {
                    'sample_id': s['sample_id'],
                    'code': s['code'],
                    'date': s['date']
                }
                for s in cluster_samples
            ]
        }

    # 保存聚类结果
    output_file = os.path.join(script_dir, '..', '..', 'clustered_samples.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(clustered_data, f, ensure_ascii=False, indent=2)

    print(f"\nClustered samples saved to: {output_file}")
    print("\nClustering completed!")
    print(f"Cost: $0 (programmatic clustering)")


if __name__ == '__main__':
    main()
