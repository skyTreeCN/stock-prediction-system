import anthropic
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('backend/.env')

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

prompt = """我正在开发一个股票模式识别系统，现在需要优化"模式验证"功能。

## 当前方案

**目标**：验证提取的上涨模式在历史数据上的准确率

**现有方案C（最优）**：
1. 从历史数据随机采样500个K线快照（30天K线/快照）
2. 用量化参数程序预筛选 → 筛出50个候选
3. 将50个候选一次性提交给Haiku 3.5批量匹配
4. 查询匹配样本的T+3日实际涨幅
5. 计算每个模式的准确率

**费用**: ~$0.02（单次Haiku调用）
**验证样本数**: ~50-100个

## 步骤1的成功经验

在"模式提取"阶段，我们用了这个优化思路：
- **不是逐个样本调用AI**（需要2000次调用，费用$20+）
- **而是批量提交500个样本给Sonnet 4.5归纳总结**（1次调用，费用$0.30）
- 降低费用99%

## 问题

现在的方案C虽然便宜（$0.02），但验证样本只有50-100个，统计可靠性可能不够。

请分析：
1. **如何进一步优化验证流程**？能否复用步骤1的批量思想？
2. **如何在低成本下获得更多验证样本**？
3. **是否有更聪明的验证方法**？（例如：让AI直接从大量历史数据中找匹配样本）
4. **当前方案的潜在问题是什么**？

请给出具体的优化建议和实现思路。"""

message = client.messages.create(
    model="claude-opus-4-20250514",
    max_tokens=8000,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print("=" * 80)
print("Opus 4.5 分析结果：")
print("=" * 80)
print(message.content[0].text)
print("=" * 80)
