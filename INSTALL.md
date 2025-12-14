# 快速安装指南

## 📦 一键安装脚本

### Windows 用户

#### 第一步：准备工作

1. 打开 Git Bash 终端
2. 确保已安装：
   - Python 3.10+ （必需）
   - Node.js （必需）
   - Git （必需）
   - Miniconda/Conda （可选，如果使用 conda）

#### 第二步：配置后端

**选择方式 A 或 B 其中一种即可**

**方式 A：使用 venv（推荐，更简单）⭐**

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv

# 激活环境
source venv/Scripts/activate

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 然后用文本编辑器打开 .env，填入您的 Claude API Key
```

**方式 B：使用 conda**

```bash
# 进入后端目录
cd backend

# 如果遇到 conda 服务条款错误，先执行：
conda config --remove-key channels
conda config --add channels conda-forge
conda config --set channel_priority strict

# 创建虚拟环境
conda create -n stock-prediction python=3.10 -y

# 激活环境
conda activate stock-prediction

# 安装依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 然后用文本编辑器打开 .env，填入您的 Claude API Key
```

#### 第三步：配置前端

```bash
# 返回上级目录
cd ..

# 进入前端目录
cd frontend

# 安装依赖
npm install
```

#### 第四步：启动系统

**方法1：使用启动脚本（推荐）**

打开两个终端窗口：

终端1（后端）：
```bash
cd backend
start.bat
```

终端2（前端）：
```bash
cd frontend
start.bat
```

**方法2：手动启动**

终端1（后端 - venv 方式）：
```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

终端1（后端 - conda 方式）：
```bash
cd backend
conda activate stock-prediction
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

终端2（前端）：
```bash
cd frontend
npm run dev
```

#### 第五步：访问系统

打开浏览器访问：**http://localhost:3000**

## ✅ 验证安装

### 检查后端

访问 http://localhost:8000

应该看到：
```json
{
  "status": "ok",
  "message": "股票预测系统API运行中"
}
```

### 检查前端

访问 http://localhost:3000

应该看到三个区域的界面

### 检查 API 文档

访问 http://localhost:8000/docs

可以看到 Swagger 交互式文档

## 🐛 常见安装问题

### 问题1：Python 虚拟环境问题

**venv 方式错误**：
```bash
# 如果 python 命令找不到，尝试：
python3 -m venv venv

# 或检查 Python 是否安装：
python --version  # 应该显示 3.10 或更高版本
```

**conda 服务条款错误**：
```
CondaToSNonInteractiveError: Terms of Service have not been accepted
```

**解决**：
```bash
# 移除默认源，使用 conda-forge
conda config --remove-key channels
conda config --add channels conda-forge
conda config --set channel_priority strict

# 然后重新创建环境
conda create -n stock-prediction python=3.10 -y
```

### 问题2：conda 命令找不到

**解决**：
1. 如果没有 conda，推荐使用 venv 方式（方式A）
2. 或确保 Miniconda 已安装
3. 重新打开终端
4. 或手动添加到 PATH

### 问题3：pip 安装速度慢

**解决**：使用国内镜像
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题4：npm 安装失败

**解决**：
```bash
# 清除缓存
npm cache clean --force

# 使用淘宝镜像
npm install --registry=https://registry.npmmirror.com
```

### 问题5：端口被占用

**解决**：
```bash
# 修改端口
# 后端：在 backend/start.bat 中修改 --port 8000
# 前端：在 frontend/package.json 中修改脚本为 "dev": "next dev -p 3001"
```

## 📝 环境变量配置

`.env` 文件内容：

```env
# 必填：您的 Claude API Key
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# 可选：数据库路径
DATABASE_PATH=../data/stocks.db

# 可选：数据年限
YEARS_OF_DATA=3
```

## 🔄 下一步

安装完成后，请查看 [README.md](README.md) 了解：
- 使用指南
- 功能说明
- 故障排除

---

**安装遇到问题？** 检查上述常见问题或查看 README.md 的故障排除章节。
