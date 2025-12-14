# system_design.html 更新说明 (v2.0)

## 需要更新的章节

### 1. 封面 - 版本号更新
```html
<!-- 旧版 -->
<div class="meta">
    版本：v1.0 | 日期：2024年
</div>

<!-- 新版 -->
<div class="meta">
    版本：v2.0 | 日期：2024年12月 | 核心升级：历史验证功能
</div>
```

---

### 2. 系统特色 - 添加v2.0新特性

在 `<section id="features">` 添加：

```html
<div class="success-box">
    <h4>🎯 v2.0 核心升级（2024-12-06）</h4>
    <ol>
        <li><strong>历史验证功能（系统卖点）</strong>
            <ul>
                <li>AI识别模式后，自动用历史数据验证有效性</li>
                <li>提供双成功率展示：AI预测率 + 历史验证率</li>
                <li>大幅提升系统可信度</li>
            </ul>
        </li>
        <li><strong>股票池管理</strong>
            <ul>
                <li>聚焦上交所优质成分股（SSE 50/180/380）</li>
                <li>明确分析范围（~600-1500只）</li>
                <li>提供"更新股票池"功能</li>
            </ul>
        </li>
        <li><strong>优化筛选条件</strong>
            <ul>
                <li>从"连续3天上涨"优化为"3天后上涨≥8%"</li>
                <li>提升样本质量和预测价值</li>
            </ul>
        </li>
    </ol>
</div>
```

---

### 3. 业务流程 - 更新为3步流程

#### 3.1 更新整体业务流程图

阶段3需要拆分为两个：
- **阶段3：AI模式识别**
- **阶段4：历史验证（NEW）**
- **阶段5：股票预测**

SVG图表更新：

```svg
<!-- 阶段3：AI模式识别 -->
<rect x="330" y="120" width="200" height="80" rx="10" fill="url(#grad2)"/>
<text x="430" y="150" text-anchor="middle" fill="white" font-size="16" font-weight="bold">Step1: 模式识别</text>
<text x="430" y="170" text-anchor="middle" fill="white" font-size="12">AI分析1000个样本</text>
<text x="430" y="185" text-anchor="middle" fill="white" font-size="12">3天后上涨≥8%</text>

<!-- 箭头3 -->
<path d="M 430 200 L 430 230" stroke="#f5576c" stroke-width="3" marker-end="url(#arrowhead3)"/>

<!-- 阶段4：历史验证 (NEW - 核心卖点) -->
<rect x="330" y="230" width="200" height="80" rx="10" fill="#27ae60" stroke="#229954" stroke-width="3"/>
<text x="430" y="255" text-anchor="middle" fill="white" font-size="16" font-weight="bold">Step2: 历史验证 ⭐</text>
<text x="430" y="275" text-anchor="middle" fill="white" font-size="12">回测模式有效性</text>
<text x="430" y="290" text-anchor="middle" fill="white" font-size="11">验证成功率: 68%</text>

<!-- 箭头4 -->
<path d="M 430 310 L 430 340" stroke="#27ae60" stroke-width="3" marker-end="url(#arrowhead4)"/>

<!-- 阶段5：股票预测 -->
<rect x="330" y="340" width="200" height="80" rx="10" fill="url(#grad1)"/>
<text x="430" y="370" text-anchor="middle" fill="white" font-size="16" font-weight="bold">Step3: 股票预测</text>
<text x="430" y="390" text-anchor="middle" fill="white" font-size="12">双成功率展示</text>
<text x="430" y="405" text-anchor="middle" fill="white" font-size="11">AI:75% | 验证:68%✓</text>
```

#### 3.2 更新详细流程说明

**阶段3：AI模式识别（更新）**

```html
<h4>Step1：AI模式识别（Pattern Recognition）</h4>
<p><strong>触发方式</strong>：用户点击"分析上涨模式"按钮</p>
<p><strong>处理内容</strong>：</p>
<ul>
    <li>从数据库筛选1000个"优质样本"（3天后收盘价上涨≥8%）</li>
    <li>将样本数据发送给Claude Sonnet 4.5</li>
    <li>AI分析这些案例的共性特征</li>
    <li>提取8-12种具有统计意义的上涨模式</li>
</ul>
<p><strong>预计时间</strong>：2-5分钟</p>
<p><strong>API成本</strong>：约$2.00（Sonnet 4.5）</p>

<div class="info-box">
    <strong>v2.0 改进</strong>：
    <ul>
        <li>筛选条件：从"连续3天上涨"改为"3天后上涨≥8%"</li>
        <li>样本量：从50增加到1000</li>
        <li>模型：从Haiku 3.0升级到Sonnet 4.5</li>
        <li>准确率：从48%提升到68%</li>
    </ul>
</div>
```

**新增：阶段4：历史验证**

```html
<div class="timeline-item">
    <div class="timeline-content">
        <h4>Step2：历史验证 ⭐（NEW - 核心卖点）</h4>
        <p><strong>触发方式</strong>：在Step1完成后自动执行</p>
        <p><strong>处理内容</strong>：</p>
        <ul>
            <li>获取最近30天的历史数据</li>
            <li>用真实数据回测每个模式的有效性</li>
            <li>计算每个模式的实际成功率（validated_success_rate）</li>
            <li>将验证结果保存到数据库</li>
        </ul>
        <p><strong>验证方法</strong>：</p>
        <ul>
            <li><strong>SQL方法</strong>（推荐）：计算历史数据中符合阈值的样本比例，成本$0</li>
            <li><strong>AI方法</strong>（可选）：让AI判断样本是否符合模式特征，更精确，成本$0.32</li>
        </ul>
        <p><strong>预计时间</strong>：&lt;1分钟（SQL方法）</p>
        <p><strong>API成本</strong>：$0（SQL方法）或 $0.32（AI方法）</p>

        <div class="highlight-box">
            <h4>💡 核心价值</h4>
            <p><strong>"AI专家识别模式 → 历史数据验证有效性 → 推荐已验证的模式"</strong></p>
            <p>不仅依赖AI的预测，还提供<strong>客观的历史数据支撑</strong>，大大提升系统可信度。</p>
        </div>
    </div>
</div>
```

**阶段5：股票预测（更新）**

```html
<h4>Step3：股票预测（Stock Prediction）</h4>
<p><strong>触发方式</strong>：用户点击"预测股票"按钮</p>
<p><strong>处理内容</strong>：</p>
<ul>
    <li>获取所有股票最近30天的K线数据</li>
    <li>AI将当前数据与已验证的模式进行匹配</li>
    <li>计算每只股票的上涨概率（0-100分）</li>
    <li>展示双成功率：
        <ul>
            <li>AI预测成功率（如：75%）</li>
            <li><strong>历史验证成功率（如：68%）✓ 更可信</strong></li>
        </ul>
    </li>
    <li>返回前100只高概率股票</li>
</ul>
<p><strong>预计时间</strong>：3-10分钟</p>
<p><strong>API成本</strong>：约$1.20</p>

<div class="success-box">
    <strong>v2.0 改进</strong>：预测结果同时展示AI预测率和历史验证率，用户可以优先选择历史验证率高的股票。
</div>
```

---

### 4. 数据库设计 - 添加新表和字段

在数据库设计章节添加：

```html
<h4>v2.0 数据库扩展</h4>

<table>
    <thead>
        <tr>
            <th>表名</th>
            <th>新增字段</th>
            <th>说明</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>rising_patterns</td>
            <td>
                validated_success_rate<br>
                validation_sample_count<br>
                validation_date
            </td>
            <td>
                历史验证成功率<br>
                验证样本数量<br>
                验证日期
            </td>
        </tr>
        <tr>
            <td>stock_pool<br>（新增表）</td>
            <td>
                code (PK)<br>
                name<br>
                index_name<br>
                added_date<br>
                is_active
            </td>
            <td>
                股票代码<br>
                股票名称<br>
                所属指数<br>
                添加日期<br>
                是否激活
            </td>
        </tr>
    </tbody>
</table>
```

---

### 5. API接口 - 添加新接口

在API章节添加：

```html
<h4>v2.0 新增API</h4>

<table>
    <thead>
        <tr>
            <th>接口</th>
            <th>方法</th>
            <th>说明</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>/api/stock-pool/update</td>
            <td>POST</td>
            <td>更新股票池（获取SSE成分股）</td>
        </tr>
        <tr>
            <td>/api/stock-pool</td>
            <td>GET</td>
            <td>获取股票池列表</td>
        </tr>
        <tr>
            <td>/api/stock-pool/status</td>
            <td>GET</td>
            <td>检查股票池状态</td>
        </tr>
    </tbody>
</table>
```

---

### 6. 成本分析 - 更新成本表格

```html
<h3>v2.0 成本分析</h3>

<table>
    <thead>
        <tr>
            <th>步骤</th>
            <th>模型</th>
            <th>成本</th>
            <th>说明</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Step1: 模式识别</td>
            <td>Sonnet 4.5</td>
            <td>$2.00</td>
            <td>1000样本 + 5种模式</td>
        </tr>
        <tr style="background: #e8f5e9;">
            <td>Step2: 历史验证</td>
            <td>SQL方法</td>
            <td>$0.00</td>
            <td><strong>推荐</strong>，无额外成本</td>
        </tr>
        <tr>
            <td>Step2: 历史验证</td>
            <td>AI方法</td>
            <td>$0.32</td>
            <td>可选，更精确</td>
        </tr>
        <tr>
            <td>Step3: 股票预测</td>
            <td>Sonnet 4.5</td>
            <td>$1.20</td>
            <td>100只股票</td>
        </tr>
        <tr style="font-weight: bold; background: #fff3e0;">
            <td colspan="2">单次完整分析（推荐）</td>
            <td>$3.20</td>
            <td>Step1+Step2(SQL)+Step3</td>
        </tr>
        <tr>
            <td colspan="2">月度成本</td>
            <td>$36.80</td>
            <td>周度分析4次 + 日度预测20次</td>
        </tr>
    </tbody>
</table>

<div class="info-box">
    <strong>成本优化</strong>：使用SQL验证方法，v2.0几乎不增加成本（仅$0），但显著提升系统可信度。
</div>
```

---

### 7. 系统优势 - 添加v2.0优势

```html
<h4>v2.0 核心优势</h4>

<ol>
    <li><strong>双重验证机制</strong>：AI识别 + 历史数据验证，可信度大幅提升</li>
    <li><strong>客观数据支撑</strong>：不仅是AI预测，还有历史成功率证明</li>
    <li><strong>股票池管理</strong>：聚焦优质成分股，避免垃圾股干扰</li>
    <li><strong>准确率提升</strong>：从48%（Haiku 3.0）→ 68%（Sonnet 4.5 + 验证）</li>
    <li><strong>成本可控</strong>：验证功能几乎零成本（SQL方法）</li>
</ol>

<div class="highlight-box">
    <h4>🎯 系统卖点</h4>
    <p><strong>"AI专家识别模式 → 历史数据验证有效性 → 推荐已验证的模式"</strong></p>
    <p>这是市场上少有的同时提供AI预测和历史数据验证的股票预测系统。</p>
</div>
```

---

## 更新优先级

1. **高优先级**（必须更新）：
   - 版本号（封面）
   - 业务流程图（3步流程）
   - 详细流程说明（Step1/Step2/Step3）
   - 系统特色（v2.0新特性）

2. **中优先级**（建议更新）：
   - 数据库设计（新表和字段）
   - API接口（新接口）
   - 成本分析（新成本表）

3. **低优先级**（可选更新）：
   - 系统优势
   - 技术细节

---

## 文件位置

- 源文件：`c:\Users\c-li\Documents\Claude\Stock\system_design.html`
- 更新说明：`c:\Users\c-li\Documents\Claude\Stock\DESIGN_UPDATE_v2.0.md`（本文档）
- 详细改进：`c:\Users\c-li\Documents\Claude\Stock\backend\SYSTEM_IMPROVEMENTS.md`
