from anthropic import Anthropic
import pandas as pd
from typing import List, Dict, Optional
import json
import os
import time
from datetime import datetime
from .config import get_model_id, get_active_model
from .pattern_matcher import load_classic_patterns, match_classic_patterns, pre_screen_stocks

class StockAnalyzer:
    """使用 Claude AI 进行股票分析"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, db=None):
        """初始化StockAnalyzer

        Args:
            api_key: Anthropic API密钥（可选，无密钥时仅支持非AI功能）
            model: 模型ID（可选）
            db: StockDatabase实例（可选，用于保存预测结果）
        """
        # 数据库依赖注入
        self.db = db

        # API密钥处理：无密钥时不崩溃，而是延迟初始化
        self.api_key = api_key
        self.client = None
        self.ai_enabled = False

        if api_key:
            try:
                self.client = Anthropic(api_key=api_key)
                self.ai_enabled = True
            except Exception as e:
                print(f"⚠️  Claude API初始化失败: {e}")
                print(f"   AI功能将不可用，但基础功能仍可正常运行")

        # API调用统计
        self.api_calls = 0
        self.api_errors = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        # 从配置文件获取模型ID
        if model is None:
            self.model = get_model_id()
            model_config = get_active_model()
            if self.ai_enabled:
                print(f"✅ 初始化 StockAnalyzer (AI模式)")
                print(f"   模型: {model_config['name']} ({self.model})")
                print(f"   预期准确率: {model_config.get('accuracy_5p', 'N/A')}% (5种模式)")
                print(f"   适用场景: {model_config['use_case']}")
            else:
                print(f"⚠️  初始化 StockAnalyzer (无AI模式)")
                print(f"   仅支持基础数据处理功能")
        else:
            self.model = model
            if self.ai_enabled:
                print(f"⚠️  使用自定义模型: {self.model}")

    def _check_ai_available(self) -> bool:
        """检查AI功能是否可用"""
        if not self.ai_enabled or not self.client:
            print("❌ AI功能不可用：未配置ANTHROPIC_API_KEY")
            return False
        return True

    def _call_claude_with_retry(
        self,
        prompt: str,
        max_tokens: int = 4096,
        max_retries: int = 3,
        timeout: int = 60
    ) -> Optional[str]:
        """带重试和超时机制的Claude API调用

        Args:
            prompt: 提示词
            max_tokens: 最大token数
            max_retries: 最大重试次数
            timeout: 超时时间（秒）

        Returns:
            API响应文本，失败返回None
        """
        for attempt in range(max_retries):
            try:
                print(f"   Claude API调用 (尝试 {attempt + 1}/{max_retries})...")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    timeout=timeout,  # 设置超时
                    messages=[{"role": "user", "content": prompt}]
                )

                # 更新API统计
                self.api_calls += 1
                self.total_input_tokens += message.usage.input_tokens
                self.total_output_tokens += message.usage.output_tokens

                response_text = message.content[0].text
                print(f"   ✅ API调用成功 (输入:{message.usage.input_tokens} 输出:{message.usage.output_tokens})")
                return response_text

            except Exception as e:
                self.api_errors += 1
                error_msg = str(e)

                # 检查是否是限流错误
                is_rate_limit = "rate_limit" in error_msg.lower() or "429" in error_msg

                if attempt < max_retries - 1:
                    # 指数退避：2^attempt 秒，限流错误等待更久
                    wait_time = (2 ** attempt) * (5 if is_rate_limit else 1)
                    print(f"   ⚠️  API调用失败: {error_msg}")
                    print(f"   等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"   ❌ API调用最终失败: {error_msg}")
                    print(f"   错误类型: {type(e).__name__}")
                    if hasattr(e, 'response'):
                        print(f"   响应: {e.response}")
                    return None

        return None

    def analyze_rising_patterns(self, sample_data: pd.DataFrame) -> List[Dict]:
        """分析上涨模式

        Args:
            sample_data: 历史上涨样本数据

        Returns:
            List of pattern dictionaries
        """
        # 检查AI是否可用
        if not self._check_ai_available():
            return []

        # 准备数据摘要
        data_summary = self._prepare_data_summary(sample_data)

        prompt = f"""你是一位专业的股票技术分析师。我给你提供了{len(sample_data)}个历史上涨案例（3天后收盘价上涨≥8%的股票数据）。

请深入分析这些数据，总结出8-12种具有代表性的上涨模式特征。由于样本量很大，请尽量识别出更多细分的模式类型。

数据示例（前20条）：
{data_summary}

请从以下角度分析：
1. K线形态特征（如阳线连续、实体大小、影线特征等）
2. 价格变化幅度特征（温和上涨、加速上涨、爆发上涨等）
3. 成交量变化特征（放量、缩量、温和放量等）
4. 技术指标特征（如均线、MACD、趋势线等可以从价格计算）
5. 市场环境特征（突破、反弹、趋势延续等）

**重要：对于每个模式，请提供一个最典型的示例股票代码，以及该模式的量化特征。**

请以JSON格式返回，格式如下：
[
    {{
        "pattern_name": "模式名称",
        "description": "模式描述",
        "characteristics": ["特征1", "特征2", "特征3"],
        "example_stock_code": "示例股票代码（从数据中选择最典型的）",
        "highlight_description": {{
            "key_days": "关键K线的相对位置描述，如'最近3天'、'第85-89天'",
            "key_features": ["需要在K线图上标注的关键点，如'连续3根阳线'、'成交量放大2倍'"]
        }}
    }}
]

注意：
- 请至少返回8种模式，最多12种
- 每种模式应有明确区分度
- 模式名称要简洁专业
- example_stock_code必须从提供的数据中选择
- highlight_description要具体，便于在K线图上可视化
- 只返回JSON数组，不要其他文字"""

        # 使用带重试的API调用
        response_text = self._call_claude_with_retry(prompt, max_tokens=4096)

        if not response_text:
            print("❌ Claude API调用失败，无法分析模式")
            return []

        try:
            print(f"[DEBUG] Claude 响应: {response_text[:200]}...")

            # 清理 markdown 代码块标记
            if response_text.strip().startswith('```'):
                # 移除 ```json 和 ```
                lines = response_text.strip().split('\n')
                response_text = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_text

            # 解析JSON
            patterns = json.loads(response_text)
            return patterns

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"   响应内容: {response_text[:500]}")
            return []

    def predict_stock_probability(
        self,
        stock_data: pd.DataFrame,
        patterns: List[Dict],
        batch_size: int = 50,
        use_pre_screening: bool = True,
        pattern_file: str = 'classic_patterns.json'
    ) -> List[Dict]:
        """批量预测股票上涨概率（支持程序预筛选）

        Args:
            stock_data: 股票最近的K线数据（按股票分组）
            patterns: 已识别的上涨模式
            batch_size: 每批处理的股票数量
            use_pre_screening: 是否使用程序预筛选（降低成本）
            pattern_file: 经典模式定义文件路径

        Returns:
            List of predictions with probability
        """
        # 按股票代码分组
        grouped = stock_data.groupby('code')
        codes = list(grouped.groups.keys())

        # 程序预筛选阶段
        if use_pre_screening:
            print(f"\n🔍 程序预筛选阶段")
            print(f"   总股票数: {len(codes)}")

            try:
                # 加载经典模式
                classic_patterns = load_classic_patterns(pattern_file)

                # 准备股票K线数据
                stocks_kline_data = {}
                for code in codes:
                    df = grouped.get_group(code).sort_values('date')
                    recent = df.tail(30)  # 最近30天
                    kline_data = recent[['date', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')
                    stocks_kline_data[code] = kline_data

                # 程序预筛选
                candidate_codes = pre_screen_stocks(stocks_kline_data, classic_patterns)
                print(f"   筛选后候选: {len(candidate_codes)} 只")

                # 如果筛选后太少，取前50个
                if len(candidate_codes) < 10:
                    print(f"   ⚠️  候选太少，使用全部股票")
                    codes = codes[:50]
                else:
                    codes = candidate_codes[:50]  # 最多50只

            except Exception as e:
                print(f"   ⚠️  预筛选失败，使用全部股票: {e}")
                codes = codes[:50]
        else:
            print(f"\n🔍 直接AI分析（未使用预筛选）")
            codes = codes[:50]

        all_predictions = []

        # 分批处理
        for i in range(0, len(codes), batch_size):
            batch_codes = codes[i:i + batch_size]
            batch_data = {code: grouped.get_group(code) for code in batch_codes}

            predictions = self._predict_batch(batch_data, patterns)
            all_predictions.extend(predictions)

        # 按概率排序
        all_predictions.sort(key=lambda x: x['probability'], reverse=True)

        # 保存预测结果到数据库（如果有DB依赖）
        if self.db:
            from datetime import datetime
            prediction_date = datetime.now().strftime('%Y-%m-%d')

            for pred in all_predictions[:100]:
                try:
                    self.db.save_prediction({
                        'stock_code': pred['code'],
                        'stock_name': pred.get('name', ''),
                        'prediction_date': prediction_date,
                        'matched_patterns': pred.get('matched_patterns', []),
                        'probability': pred['probability'],
                        'reasoning': pred.get('reasoning', '')
                    })
                except Exception as e:
                    print(f"保存预测结果失败 {pred['code']}: {e}")
        else:
            print("⚠️  未配置数据库，预测结果仅保存在内存中")

        return all_predictions[:100]  # 返回前100个

    def _predict_batch(self, batch_data: Dict[str, pd.DataFrame], patterns: List[Dict]) -> List[Dict]:
        """预测一批股票"""
        # 检查AI是否可用
        if not self._check_ai_available():
            return []

        # 准备批量数据摘要和元数据字典
        batch_summary = []
        stock_metadata = {}  # 存储每个股票的元数据

        for code, df in batch_data.items():
            df_sorted = df.sort_values('date')
            recent = df_sorted.tail(30)  # 最近30天（约1个月）

            stock_name = df['name'].iloc[0] if 'name' in df.columns else code
            current_price = float(recent['close'].iloc[-1])
            last_date = str(recent['date'].iloc[-1])

            # 保存元数据
            stock_metadata[code] = {
                'name': stock_name,
                'current_price': current_price,
                'last_date': last_date
            }

            summary = {
                'code': code,
                'name': stock_name,
                'current_price': current_price,
                'last_date': last_date,
                'recent_data': recent[['date', 'open', 'close', 'high', 'low', 'volume']].to_dict('records')
            }
            batch_summary.append(summary)

        # 准备模式描述
        patterns_text = "\n".join([
            f"{i+1}. {p['pattern_name']}: {p['description']}"
            for i, p in enumerate(patterns)
        ])

        prompt = f"""你是专业的股票预测分析师。

已知的上涨模式：
{patterns_text}

现在有{len(batch_summary)}只股票的最近数据，请根据上涨模式分析每只股票在未来3天上涨的概率。

股票数据：
{json.dumps(batch_summary[:10], ensure_ascii=False, indent=2)}
{'...(还有更多股票)' if len(batch_summary) > 10 else ''}

请对每只股票进行分析，评估其与上涨模式的相似度，给出0-100的上涨概率评分。

返回JSON格式：
[
    {{
        "code": "股票代码",
        "name": "股票名称",
        "probability": 85.5,
        "reason": "简要说明符合哪些特征"
    }}
]

注意：
- 只返回概率大于60的股票
- probability 是0-100的数值
- reason 简短说明（不超过50字）
- 只返回JSON数组，不要其他文字"""

        # 使用带重试的API调用
        response_text = self._call_claude_with_retry(prompt, max_tokens=4096)

        if not response_text:
            print("❌ Claude API调用失败，跳过该批次")
            return []

        try:
            # 提取JSON（可能有markdown代码块）
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            predictions = json.loads(response_text.strip())

            # 合并元数据和量化指标到预测结果
            for pred in predictions:
                code = pred.get('code')
                if code in stock_metadata:
                    pred['current_price'] = stock_metadata[code]['current_price']
                    pred['last_date'] = stock_metadata[code]['last_date']
                    # 确保name一致
                    if 'name' not in pred or not pred['name']:
                        pred['name'] = stock_metadata[code]['name']

                    # 计算量化匹配度特征
                    if code in batch_data:
                        quant_data = self._calculate_quantitative_features(batch_data[code])
                        pred['matched_quantitative_data'] = quant_data

            return predictions

        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"   响应内容: {response_text[:500]}")
            return []

    def validate_patterns_sql(
        self,
        patterns: List[Dict],
        validation_data: pd.DataFrame,
        rise_threshold: float = 0.08
    ) -> List[Dict]:
        """使用SQL方法验证模式（基于特征匹配，无额外成本）

        Args:
            patterns: AI识别的模式列表
            validation_data: 验证数据集（包含is_success字段）
            rise_threshold: 上涨阈值

        Returns:
            更新后的模式列表，包含validated_success_rate字段
        """
        print(f"\n📊 开始验证模式（SQL方法）")
        print(f"   验证样本数: {len(validation_data)}")

        for pattern in patterns:
            pattern_name = pattern['pattern_name']
            characteristics = pattern.get('characteristics', [])

            # 根据模式特征筛选匹配样本
            matched_data = self._filter_by_characteristics(validation_data, characteristics)

            if len(matched_data) > 0:
                total_samples = len(matched_data)
                success_samples = matched_data['is_success'].sum()
                success_rate = (success_samples / total_samples) * 100
            else:
                total_samples = 0
                success_samples = 0
                success_rate = 0

            pattern['validated_success_rate'] = round(success_rate, 2)
            pattern['validation_sample_count'] = total_samples
            pattern['validation_date'] = datetime.now().strftime('%Y-%m-%d')

            print(f"   ✓ {pattern_name}: {success_rate:.1f}% ({success_samples}/{total_samples})")

        return patterns

    def validate_patterns_ai(
        self,
        patterns: List[Dict],
        validation_data: pd.DataFrame,
        rise_threshold: float = 0.08
    ) -> List[Dict]:
        """使用AI方法验证模式（更精确，有成本）

        Args:
            patterns: AI识别的模式列表
            validation_data: 验证数据集
            rise_threshold: 上涨阈值

        Returns:
            更新后的模式列表，包含validated_success_rate字段
        """
        # 检查AI是否可用
        if not self._check_ai_available():
            print("⚠️  AI不可用，降级到SQL验证方法")
            return self.validate_patterns_sql(patterns, validation_data, rise_threshold)

        print(f"\n📊 开始验证模式（AI方法）")
        print(f"   验证样本数: {len(validation_data)}")

        # 准备验证数据摘要（使用全部验证样本）
        validation_summary = self._prepare_data_summary(validation_data, limit=len(validation_data))

        for i, pattern in enumerate(patterns):
            pattern_name = pattern['pattern_name']
            description = pattern['description']
            characteristics = pattern['characteristics']

            prompt = f"""你是专业的股票模式验证分析师。

已识别的模式:
- 名称: {pattern_name}
- 描述: {description}
- 特征: {', '.join(characteristics)}

验证数据（最近1个月的历史样本，共{len(validation_data)}条）:
{validation_summary}

请分析这些验证数据中，有多少比例的样本符合上述模式特征。

返回JSON格式:
{{
    "matched_count": 匹配该模式的样本数量,
    "total_count": 总样本数,
    "success_rate": 成功率百分比（0-100）,
    "analysis": "简要分析"
}}

只返回JSON，不要其他文字。"""

            # 使用带重试的API调用
            response_text = self._call_claude_with_retry(prompt, max_tokens=500, timeout=30)

            if not response_text:
                print(f"   ✗ {pattern_name} API调用失败，设置为0")
                pattern['validated_success_rate'] = 0
                pattern['validation_sample_count'] = 0
                pattern['validation_date'] = datetime.now().strftime('%Y-%m-%d')
                continue

            try:
                # 提取JSON
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]

                result = json.loads(response_text.strip())

                pattern['validated_success_rate'] = round(result['success_rate'], 2)
                pattern['validation_sample_count'] = result['total_count']
                pattern['validation_date'] = datetime.now().strftime('%Y-%m-%d')

                print(f"   ✓ {pattern_name}: {result['success_rate']:.1f}% ({result['matched_count']}/{result['total_count']})")

            except (json.JSONDecodeError, KeyError) as e:
                print(f"   ✗ {pattern_name} 解析失败: {e}")
                pattern['validated_success_rate'] = 0
                pattern['validation_sample_count'] = 0
                pattern['validation_date'] = datetime.now().strftime('%Y-%m-%d')

        return patterns

    def _prepare_data_summary(self, df: pd.DataFrame, limit: int = 20) -> str:
        """准备数据摘要用于提示词"""
        sample = df.head(limit)

        summary_lines = []
        for _, row in sample.iterrows():
            line = f"代码:{row['code']} 日期:{row['date']} 开:{row['open']:.2f} 收:{row['close']:.2f} 高:{row['high']:.2f} 低:{row['low']:.2f} 量:{row['volume']}"
            if 'day2_close' in row:
                line += f" → 次日收:{row['day2_close']:.2f} → 第3日收:{row['day3_close']:.2f}"
            if 'rise_pct' in row:
                line += f" (涨幅:{row['rise_pct']:.1f}%)"
            summary_lines.append(line)

        return "\n".join(summary_lines)

    def _filter_by_characteristics(self, data: pd.DataFrame, characteristics: List[str]) -> pd.DataFrame:
        """根据特征筛选样本"""
        import re

        filtered = data.copy()

        # 预计算常用字段（如果SQL查询没有提供）
        if 'day_change_pct' not in filtered.columns and 'open' in filtered.columns and 'close' in filtered.columns:
            filtered['day_change_pct'] = ((filtered['close'] - filtered['open']) / filtered['open'] * 100)

        if 'is_yang' not in filtered.columns and 'open' in filtered.columns and 'close' in filtered.columns:
            filtered['is_yang'] = filtered['close'] > filtered['open']
            filtered['is_yin'] = filtered['close'] < filtered['open']

        if 'amplitude' not in filtered.columns and 'high' in filtered.columns and 'low' in filtered.columns:
            filtered['amplitude'] = ((filtered['high'] - filtered['low']) / filtered['low'] * 100)

        for char in characteristics:
            try:
                char_lower = char.lower()

                # 阳线特征
                if '阳线' in char and 'is_yang' in filtered.columns:
                    # 提取连续天数
                    nums = re.findall(r'连续(\d+)', char)
                    if nums:
                        # 连续阳线暂时简化为单日阳线
                        filtered = filtered[filtered['is_yang'] == True]
                    else:
                        filtered = filtered[filtered['is_yang'] == True]

                # 阴线特征
                elif '阴线' in char and 'is_yin' in filtered.columns:
                    filtered = filtered[filtered['is_yin'] == True]

                # 涨幅特征
                elif ('涨幅' in char or '上涨' in char) and 'day_change_pct' in filtered.columns:
                    nums = re.findall(r'(\d+\.?\d*)[%\-](\d+\.?\d*)', char)
                    if nums:  # 范围：2-4%
                        low, high = float(nums[0][0]), float(nums[0][1])
                        filtered = filtered[(filtered['day_change_pct'] >= low) & (filtered['day_change_pct'] <= high)]
                    else:
                        nums = re.findall(r'[>=<超]+\s*(\d+\.?\d*)', char)
                        if nums:
                            threshold = float(nums[0])
                            if '超过' in char or '>' in char or '>=' in char:
                                filtered = filtered[filtered['day_change_pct'] >= threshold]
                            elif '<' in char:
                                filtered = filtered[filtered['day_change_pct'] < threshold]

                # 振幅特征
                elif '振幅' in char and 'amplitude' in filtered.columns:
                    nums = re.findall(r'(\d+\.?\d*)', char)
                    if nums:
                        threshold = float(nums[0])
                        if '超过' in char or '>' in char or '>=' in char:
                            filtered = filtered[filtered['amplitude'] > threshold]
                        elif '<' in char or '小于' in char:
                            filtered = filtered[filtered['amplitude'] < threshold]

                # 涨停特征
                elif '涨停' in char or '一字板' in char:
                    if 'day_change_pct' in filtered.columns:
                        filtered = filtered[filtered['day_change_pct'] >= 9.5]

                # 放量特征
                elif '放量' in char and 'volume' in filtered.columns:
                    nums = re.findall(r'(\d+\.?\d*)[%倍]', char)
                    if nums:
                        multiplier = float(nums[0])
                        if '%' in char:
                            multiplier = multiplier / 100 + 1
                        vol_median = filtered['volume'].median()
                        if vol_median > 0:
                            filtered = filtered[filtered['volume'] >= vol_median * multiplier]
                    else:
                        vol_median = filtered['volume'].median()
                        if vol_median > 0:
                            filtered = filtered[filtered['volume'] > vol_median * 1.2]

                # 缩量特征
                elif '缩量' in char and 'volume' in filtered.columns:
                    vol_median = filtered['volume'].median()
                    if vol_median > 0:
                        filtered = filtered[filtered['volume'] < vol_median * 0.8]

                # 收盘价/开盘价关系
                elif ('收盘价接近开盘价' in char or '收盘接近开盘' in char) and 'day_change_pct' in filtered.columns:
                    filtered = filtered[filtered['day_change_pct'] < 0.5]  # 涨跌幅<0.5%

                elif ('收盘价高于开盘价' in char or '收盘高于开盘' in char):
                    if 'is_yang' in filtered.columns:
                        nums = re.findall(r'(\d+\.?\d*)[%]', char)
                        if nums:
                            threshold = float(nums[0])
                            filtered = filtered[(filtered['is_yang'] == True) & (filtered['day_change_pct'] >= threshold)]
                        else:
                            filtered = filtered[filtered['is_yang'] == True]

                # 低开特征
                elif ('低开' in char or '开盘价低于' in char) and 'prev_close' in filtered.columns and 'open' in filtered.columns:
                    nums = re.findall(r'(\d+\.?\d*)[%]', char)
                    if nums:
                        threshold = float(nums[0]) / 100
                        # 开盘价 < 前收 * (1 - threshold)
                        filtered = filtered[filtered['open'] < filtered['prev_close'] * (1 - threshold)]
                    else:
                        # 简单低开
                        filtered = filtered[filtered['open'] < filtered['prev_close']]

            except Exception as e:
                print(f"   [警告] 特征'{char[:30]}'筛选失败: {e}")
                continue

        return filtered


    def get_api_statistics(self) -> dict:
        """获取API调用统计信息"""
        return {
            'total_calls': self.api_calls,
            'total_errors': self.api_errors,
            'success_rate': (self.api_calls - self.api_errors) / self.api_calls * 100 if self.api_calls > 0 else 0,
            'input_tokens': self.total_input_tokens,
            'output_tokens': self.total_output_tokens,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'estimated_cost_usd': self._estimate_cost()
        }

    def _estimate_cost(self) -> float:
        """估算API调用成本(美元)
        
        基于Claude API定价:
        - Sonnet: $3/M input, $15/M output
        - Haiku: $0.25/M input, $1.25/M output
        """
        if 'haiku' in self.model.lower():
            input_cost = (self.total_input_tokens / 1_000_000) * 0.25
            output_cost = (self.total_output_tokens / 1_000_000) * 1.25
        elif 'sonnet' in self.model.lower():
            input_cost = (self.total_input_tokens / 1_000_000) * 3
            output_cost = (self.total_output_tokens / 1_000_000) * 15
        else:  # opus或其他
            input_cost = (self.total_input_tokens / 1_000_000) * 15
            output_cost = (self.total_output_tokens / 1_000_000) * 75
        
        return round(input_cost + output_cost, 4)

    def _calculate_quantitative_features(self, df: pd.DataFrame) -> dict:
        """计算股票的量化特征

        分析最近30天的K线数据，提取量化指标用于前端展示

        Args:
            df: 股票K线数据（已按日期排序）

        Returns:
            量化特征字典
        """
        df_sorted = df.sort_values('date')
        recent = df_sorted.tail(30)  # 最近30天

        if len(recent) < 5:
            return {}

        # 计算成交量相关指标
        volumes = recent['volume'].values
        avg_volume = float(volumes.mean())
        recent_5_avg = float(volumes[-5:].mean())
        volume_ratio = recent_5_avg / avg_volume if avg_volume > 0 else 1.0

        # 计算价格波动指标
        closes = recent['close'].values
        highs = recent['high'].values
        lows = recent['low'].values

        # 振幅：(最高-最低)/最低
        amplitude = float(((highs.max() - lows.min()) / lows.min() * 100))

        # 检测横盘整理期（连续N天波动<3%）
        consolidation_days = 0
        for i in range(len(closes) - 1, 0, -1):
            daily_change = abs((closes[i] - closes[i-1]) / closes[i-1])
            if daily_change < 0.03:
                consolidation_days += 1
            else:
                break

        # 检测缺口（今日最低 > 昨日最高）
        gap_size = 0.0
        gap_days_ago = 0
        for i in range(len(recent) - 1, 0, -1):
            if lows[i] > highs[i-1]:
                gap_size = float(((lows[i] - highs[i-1]) / highs[i-1] * 100))
                gap_days_ago = len(recent) - 1 - i
                break

        # 计算前期和当前平均成交量（用于缩量整理判断）
        if len(volumes) >= 15:
            avg_volume_before = float(volumes[:15].mean())
            avg_volume_during = float(volumes[15:].mean())
        else:
            avg_volume_before = avg_volume
            avg_volume_during = avg_volume

        # 返回量化特征（使用驼峰命名匹配前端）
        quant_features = {
            'consolidationDays': consolidation_days if consolidation_days >= 3 else 0,
            'avgVolumeBefore': round(avg_volume_before, 2),
            'avgVolumeDuring': round(avg_volume_during, 2),
            'volumeRatio': round(volume_ratio, 2),
            'gapSize': round(gap_size, 2) if gap_size > 0 else 0,
            'daysAfterGap': gap_days_ago if gap_size > 0 else 0,
            'amplitude': round(amplitude, 2),
            'recent5DaysAvgVolume': round(recent_5_avg, 2)
        }

        return quant_features
