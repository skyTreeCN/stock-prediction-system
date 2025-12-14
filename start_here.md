# 🚀 开始使用 - 5分钟快速启动

## ⚡ 快速启动步骤

### 步骤 1：配置后端环境（5分钟）

打开 **Git Bash** 终端，选择以下任一方式：

#### 方式 A：使用 venv（推荐，更简单）⭐

```bash
# 进入后端目录
cd backend

# 创建 Python 虚拟环境
python -m venv venv

# 激活环境
source venv/Scripts/activate

# 安装依赖包
pip install -r requirements.txt
```

#### 方式 B：使用 conda

```bash
# 进入后端目录
cd backend

# 如果遇到 conda 服务条款问题，先执行：
conda config --remove-key channels
conda config --add channels conda-forge
conda config --set channel_priority strict

# 创建 Python 虚拟环境
conda create -n stock-prediction python=3.10 -y

# 激活环境
conda activate stock-prediction

# 安装依赖包
pip install -r requirements.txt
```

### 步骤 2：配置 API Key（1分钟）

```bash
# 复制环境变量模板
cp .env.example .env
```

然后用文本编辑器打开 `backend/.env` 文件，填入您的 Claude API Key：

```
ANTHROPIC_API_KEY=你的API密钥
DATABASE_PATH=../data/stocks.db
YEARS_OF_DATA=3
```

### 步骤 3：配置前端（3分钟）

```bash
# 返回项目根目录
cd ..

# 进入前端目录
cd frontend

# 安装 Node 依赖
npm install
```

### 步骤 4：启动系统（1分钟）

#### 打开第一个终端（后端）

**推荐方式（自动设置UTF-8编码）**：
```bash
cd backend
./start_api.bat
```

**如果使用 venv（手动启动）**：
```bash
cd backend
source venv/Scripts/activate
set PYTHONIOENCODING=utf-8 && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**如果使用 conda（手动启动）**：
```bash
cd backend
conda activate stock-prediction
set PYTHONIOENCODING=utf-8 && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

看到以下信息表示成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
✓ API Key 已加载: sk-ant-...
```

#### 打开第二个终端（前端）

**Windows 用户**：
```bash
cd frontend
start.bat
```

**或手动启动**：
```bash
cd frontend
npm run dev
```

看到以下信息表示成功：
```
- Local:        http://localhost:3000
```

### 步骤 5：开始使用 🎉

打开浏览器访问：**http://localhost:3000**

## 📝 使用流程

### 首次使用（完整流程）

1. **获取数据**（区域1）
   - 点击「获取上交所股票数据」按钮
   - 等待 10-30 分钟
   - 看到数据统计信息表示成功

2. **分析模式**（区域2）
   - 点击「分析上涨模式」按钮
   - 等待 1-3 分钟
   - 看到识别出的模式列表

3. **预测股票**（区域3）
   - 点击「开始预测」按钮
   - 等待 3-10 分钟
   - 查看前 100 只推荐股票

### 日常使用（已有数据）

直接从区域3开始预测即可！

## ✅ 验证安装

### 检查后端
访问：http://localhost:8000

应该看到：
```json
{"status": "ok", "message": "股票预测系统API运行中"}
```

### 检查前端
访问：http://localhost:3000

应该看到完整的三个区域界面

### 查看 API 文档
访问：http://localhost:8000/docs

可以看到所有 API 接口的交互式文档

## 🐛 遇到问题？

### 后端无法启动
```bash
# 如果使用 venv，确认已激活环境
source venv/Scripts/activate

# 如果使用 conda，确认已激活环境
conda activate stock-prediction

# 重新安装依赖
pip install -r requirements.txt
```

### 前端无法启动
```bash
# 清除缓存重装
npm cache clean --force
npm install
```

### API Key 错误
- 检查 `backend/.env` 文件是否存在
- 确认 API Key 填写正确
- 确认 API Key 有足够的额度

## 📖 详细文档

遇到其他问题？查看完整文档：

- [README.md](README.md) - 完整使用手册
- [INSTALL.md](INSTALL.md) - 详细安装指南
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 项目架构说明

## 💰 成本提醒

- 首次模式分析：约 $0.15-$0.30
- 每次预测：约 $0.10-$0.20
- 数据获取：完全免费

## ⚠️ 重要提醒

1. ✅ 首次使用必须先获取数据
2. ✅ 必须先分析模式才能预测
3. ⚠️ 预测结果仅供学习研究
4. ⚠️ 不构成任何投资建议

---

## 🎯 目标

使用本系统，您可以：
- ✅ 学习 FastAPI + Next.js 开发
- ✅ 体验 Claude AI 能力
- ✅ 了解股票技术分析
- ✅ 获得学习研究数据

**准备好了吗？开始您的股票预测之旅！** 🚀
