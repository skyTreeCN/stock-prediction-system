# 股票预测系统

基于 Claude AI 的上交所股票上涨概率预测系统

## 📋 系统概述

本系统通过分析上交所股票的历史K线数据，使用 Claude AI 识别上涨模式，并预测未来3天内上涨概率最高的股票（前100名）。

### 功能特点

- **区域1：数据获取** - 一键获取上交所所有股票最近3年的日K线数据
- **区域2：数据分析** - 使用 Claude AI 分析历史上涨案例，提取共性特征
- **区域3：相似性分析** - 基于最近1个月数据进行模式匹配，预测上涨概率

### 技术栈

- **后端**: Python 3.10+ | FastAPI | SQLite | AkShare | Claude API
- **前端**: Next.js 14 | React | TypeScript | TailwindCSS
- **数据**: SQLite（本地文件数据库）

## 🚀 快速开始

### 前置要求

确保您的系统已安装：
- Python 3.10+ （必需）
- Node.js 18+ （必需）
- Git Bash（Windows）
- Claude API Key（从 Anthropic 获取）
- Miniconda/Conda （可选，如果使用 conda 方式）

### 第一步：配置后端

#### 1.1 创建 Python 虚拟环境

**方式 A：使用 venv（推荐）**

```bash
cd backend
python -m venv venv
source venv/Scripts/activate
```

**方式 B：使用 conda**

```bash
cd backend
# 如果遇到服务条款问题，先执行：
# conda config --remove-key channels
# conda config --add channels conda-forge
# conda config --set channel_priority strict

conda create -n stock-prediction python=3.10 -y
conda activate stock-prediction
```

#### 1.2 安装 Python 依赖

```bash
pip install -r requirements.txt
```

#### 1.3 配置环境变量

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的 Claude API Key：

```
ANTHROPIC_API_KEY=your_actual_api_key_here
DATABASE_PATH=../data/stocks.db
YEARS_OF_DATA=3
```

### 第二步：配置前端

#### 2.1 安装 Node 依赖

```bash
cd ../frontend
npm install
```

### 第三步：启动系统

#### 3.1 启动后端服务（第一个终端）

**如果使用 venv**：
```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**如果使用 conda**：
```bash
cd backend
conda activate stock-prediction
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**或使用启动脚本（自动检测）**：
```bash
cd backend
start.bat  # Windows
```

后端服务将在 `http://localhost:8000` 启动

#### 3.2 启动前端服务（第二个终端）

```bash
cd frontend
npm run dev
```

前端界面将在 `http://localhost:3000` 启动

#### 3.3 访问系统

打开浏览器访问：**http://localhost:3000**

## 📖 使用指南

### 完整使用流程

#### 步骤1：获取数据（首次使用必需）

1. 在浏览器中打开系统界面
2. 点击 **区域1** 的「获取上交所股票数据」按钮
3. 等待数据获取完成（约10-30分钟）
   - 系统会显示进度和状态
   - 完成后会显示数据统计信息

**注意**：
- 首次运行需要获取约3年的历史数据
- 数据量约2000只股票 × 750天 = 150万条记录
- 数据会保存在 `data/stocks.db` 文件中
- 后续使用无需重复获取

#### 步骤2：分析上涨模式

1. 数据获取完成后，点击 **区域2** 的「分析上涨模式」按钮
2. 系统会：
   - 从数据库中提取50个历史上涨案例（连续3天上涨的股票）
   - 调用 Claude AI 分析这些案例的共性特征
   - 识别出5-10种上涨模式
3. 等待1-3分钟，完成后会显示识别出的模式

**成本**：约 $0.15-$0.30（一次性）

#### 步骤3：预测股票

1. 点击 **区域3** 的「开始预测」按钮
2. 系统会：
   - 获取所有股票最近30天的K线数据
   - 使用 Claude AI 与上涨模式进行相似度匹配
   - 计算每只股票的上涨概率（0-100）
3. 等待3-10分钟，完成后显示前100只概率最高的股票

**成本**：约 $0.10-$0.20 每次运行

#### 结果解读

预测结果表格包含：
- **排名**：按上涨概率从高到低排序
- **股票代码/名称**：上交所股票信息
- **当前价格**：最新收盘价
- **上涨概率**：0-100的评分
  - 90以上：红色（非常高）
  - 80-90：橙色（高）
  - 70-80：黄色（中等）
  - 60-70：绿色（较低）
- **原因**：简要说明匹配的特征

## 💰 成本估算

### API 使用成本（Claude 3.5 Sonnet）

- **首次模式分析**：$0.15 - $0.30（一次性）
- **每次预测**：$0.10 - $0.20
- **每月成本**（假设每天运行一次）：约 $3-$6

### 数据获取成本

- **完全免费**（使用 AkShare 公开数据）

## 🗂️ 项目结构

```
stock-prediction-system/
├── backend/                    # Python 后端
│   ├── app/
│   │   ├── main.py            # FastAPI 主程序
│   │   ├── data_fetcher.py    # 数据获取（AkShare）
│   │   ├── database.py        # SQLite 数据库操作
│   │   ├── analyzer.py        # Claude AI 分析
│   │   └── models.py          # 数据模型
│   ├── requirements.txt       # Python 依赖
│   ├── .env.example          # 环境变量模板
│   └── .env                  # 环境变量（需创建）
│
├── frontend/                  # Next.js 前端
│   ├── app/
│   │   ├── page.tsx          # 主页面
│   │   ├── layout.tsx        # 布局
│   │   └── globals.css       # 全局样式
│   ├── components/
│   │   ├── DataFetcher.tsx   # 区域1组件
│   │   ├── DataAnalyzer.tsx  # 区域2组件
│   │   └── SimilarityAnalysis.tsx  # 区域3组件
│   └── package.json          # Node 依赖
│
├── data/                     # 数据目录
│   └── stocks.db            # SQLite 数据库（自动创建）
│
└── README.md                # 本文档
```

## 🔧 API 接口文档

后端提供以下 RESTful API：

### 基础接口

- `GET /` - 健康检查
- `GET /api/statistics` - 获取数据统计信息

### 功能接口

- `POST /api/fetch-data` - 启动数据获取任务
  ```json
  {
    "years": 3
  }
  ```

- `POST /api/analyze` - 启动模式分析任务
  ```json
  {
    "pattern_count": 50
  }
  ```

- `POST /api/predict` - 启动预测任务

### 查询接口

- `GET /api/task-status/{task_name}` - 查询任务状态
  - task_name: fetch_data | analyze | predict

- `GET /api/patterns` - 获取已识别的上涨模式

- `GET /api/predictions` - 获取预测结果

### API 文档

启动后端后，访问 `http://localhost:8000/docs` 查看 Swagger 交互式文档

## 🛠️ 故障排除

### 常见问题

#### 1. 后端启动失败

**问题**：`ModuleNotFoundError: No module named 'fastapi'`

**解决**：
```bash
# 如果使用 venv
source venv/Scripts/activate
pip install -r requirements.txt

# 如果使用 conda
conda activate stock-prediction
pip install -r requirements.txt
```

#### 2. 前端无法连接后端

**问题**：前端显示「网络错误」

**解决**：
- 确认后端已启动（http://localhost:8000）
- 检查防火墙设置
- 确认 CORS 配置正确

#### 3. 数据获取失败

**问题**：AkShare 获取数据超时

**解决**：
- 检查网络连接
- 稍后重试（可能是数据源临时问题）
- 在 `data_fetcher.py` 中增加 `time.sleep()` 延迟

#### 4. Claude API 调用失败

**问题**：`AuthenticationError` 或 `RateLimitError`

**解决**：
- 检查 `.env` 中的 API Key 是否正确
- 确认 API Key 有足够的额度
- 等待 Rate Limit 重置

#### 5. 数据库锁定

**问题**：`database is locked`

**解决**：
```bash
# 关闭所有数据库连接
# 删除数据库文件重新开始
rm data/stocks.db
```

## 🔐 安全注意事项

1. **API Key 保护**
   - 不要将 `.env` 文件提交到 Git
   - 不要在代码中硬编码 API Key

2. **数据隐私**
   - 所有数据本地存储
   - 不会上传到云端

3. **投资风险**
   - ⚠️ **免责声明**：本系统预测结果仅供学习研究
   - 不构成任何投资建议
   - 投资有风险，请谨慎决策

## 📊 系统优化建议

### 提升性能

1. **数据获取优化**
   - 只获取需要的股票（修改 `data_fetcher.py` 中的 `limit` 参数）
   - 缩短时间范围（1-2年数据）

2. **预测优化**
   - 减少 batch_size（降低单次 API 调用的数据量）
   - 增加缓存机制

3. **成本优化**
   - 使用更便宜的 Claude 模型（如 Haiku）
   - 减少分析样本数量
   - 只在收盘后运行一次预测

## 🔄 更新数据

### 定期更新策略

建议每周更新一次数据：

```bash
# 1. 清空旧数据（可选）
rm data/stocks.db

# 2. 重新获取数据
# 在界面上点击「获取数据」按钮

# 3. 重新分析模式
# 点击「分析上涨模式」按钮
```

## 📝 开发说明

### 本地开发

修改代码后：

- **后端**：FastAPI 会自动重载（--reload 模式）
- **前端**：Next.js 会自动热更新

### 添加新功能

扩展建议：
- 添加更多技术指标（MACD、RSI等）
- 支持深市股票
- 添加回测功能
- 导出预测结果到 Excel
- 发送预测结果到邮件/微信

## 📄 许可证

本项目仅供学习研究使用。

## 🙏 致谢

- [AkShare](https://github.com/akfamily/akshare) - 开源金融数据接口
- [Anthropic Claude](https://www.anthropic.com/) - AI 分析引擎
- [FastAPI](https://fastapi.tiangolo.com/) - 高性能 Web 框架
- [Next.js](https://nextjs.org/) - React 应用框架

---

**祝您使用愉快！如有问题，请检查上述故障排除章节。**
