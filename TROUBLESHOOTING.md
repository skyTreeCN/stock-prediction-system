# 故障排除指南

本文档汇总了安装和使用股票预测系统时可能遇到的所有问题及解决方案。

---

## 📦 安装相关问题

### 1. Conda 服务条款错误

**错误信息**：
```
CondaToSNonInteractiveError: Terms of Service have not been accepted for the following channels
```

**原因**：Conda 官方源需要接受服务条款。

**解决方案 1**：使用 venv 替代 conda（推荐）
```bash
cd backend
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
```

**解决方案 2**：配置 conda 使用免费源
```bash
# 移除默认源
conda config --remove-key channels

# 添加 conda-forge 源
conda config --add channels conda-forge
conda config --set channel_priority strict

# 重新创建环境
conda create -n stock-prediction python=3.10 -y
conda activate stock-prediction
pip install -r requirements.txt
```

---

### 2. Python 命令找不到

**错误信息**：
```
'python' is not recognized as an internal or external command
```

**解决方案**：
```bash
# 检查 Python 是否安装
python --version

# 如果找不到，尝试
python3 --version

# 使用 python3 创建虚拟环境
python3 -m venv venv
```

---

### 3. pip 安装速度慢

**问题**：安装依赖包时下载速度很慢

**解决方案**：使用国内镜像
```bash
# 临时使用清华镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或永久配置
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 4. npm 安装失败

**错误信息**：
```
npm ERR! network timeout
```

**解决方案**：
```bash
# 清除 npm 缓存
npm cache clean --force

# 使用淘宝镜像
npm install --registry=https://registry.npmmirror.com

# 或永久配置
npm config set registry https://registry.npmmirror.com
```

---

### 5. 虚拟环境激活失败（Windows）

**问题**：`source venv/Scripts/activate` 不工作

**解决方案**：

**Git Bash（推荐）**：
```bash
source venv/Scripts/activate
```

**CMD**：
```cmd
venv\Scripts\activate.bat
```

**PowerShell**：
```powershell
venv\Scripts\Activate.ps1
```

如果 PowerShell 提示权限错误：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 🚀 运行相关问题

### 6. 后端启动失败 - 模块找不到

**错误信息**：
```
ModuleNotFoundError: No module named 'fastapi'
```

**原因**：虚拟环境未激活或依赖未安装

**解决方案**：
```bash
# 确认虚拟环境已激活
# venv 方式：
source venv/Scripts/activate

# conda 方式：
conda activate stock-prediction

# 重新安装依赖
pip install -r requirements.txt
```

---

### 7. 端口已被占用

**错误信息**：
```
OSError: [Errno 98] Address already in use
```

**解决方案 1**：查找并关闭占用端口的进程
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <进程ID> /F

# Linux/Mac
lsof -i :8000
kill -9 <进程ID>
```

**解决方案 2**：修改端口
```bash
# 后端：修改启动命令
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# 前端：修改 package.json
"dev": "next dev -p 3001"
```

---

### 8. API Key 错误

**错误信息**：
```
anthropic.AuthenticationError: Invalid API key
```

**解决方案**：
1. 检查 `backend/.env` 文件是否存在
2. 确认 API Key 格式正确（以 `sk-ant-` 开头）
3. 确认 API Key 有足够的额度
4. 确认没有多余的空格或引号

**.env 正确格式**：
```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
DATABASE_PATH=../data/stocks.db
YEARS_OF_DATA=3
```

---

### 9. 数据库锁定

**错误信息**：
```
sqlite3.OperationalError: database is locked
```

**原因**：多个进程同时访问数据库

**解决方案**：
```bash
# 1. 关闭所有后端服务
# 2. 删除数据库文件重新开始
rm data/stocks.db

# 或等待几秒后重试
```

---

### 10. 前端无法连接后端

**问题**：前端显示网络错误或 CORS 错误

**解决方案**：

1. **确认后端已启动**
   ```bash
   # 访问这个地址应该返回 JSON
   curl http://localhost:8000
   ```

2. **检查 CORS 配置**（backend/app/main.py）
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["http://localhost:3000"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

3. **检查防火墙**
   - Windows 防火墙可能阻止了 8000 端口
   - 临时关闭防火墙测试

---

## 📊 数据相关问题

### 11. AkShare 数据获取失败

**错误信息**：
```
Timeout Error / Connection Error
```

**解决方案**：

1. **检查网络连接**
   ```bash
   ping akshare.akfamily.xyz
   ```

2. **增加延迟时间**
   编辑 `backend/app/data_fetcher.py`：
   ```python
   time.sleep(1)  # 从 0.5 改为 1
   ```

3. **减少并发请求**
   在 `fetch_all_stocks()` 中添加更多延迟

4. **使用代理**（如果在特殊网络环境）
   ```python
   import os
   os.environ['http_proxy'] = 'http://your-proxy:port'
   ```

---

### 12. 数据获取超时

**问题**：获取数据时间过长（超过30分钟）

**解决方案**：

1. **减少股票数量**（测试用）
   编辑 `backend/app/main.py`：
   ```python
   # 在 fetch_task 函数中
   df = fetcher.fetch_all_stocks(limit=100)  # 只获取100只股票
   ```

2. **使用已有数据**
   如果已经有部分数据，可以继续使用

3. **分批获取**
   多次运行，每次获取一部分

---

### 13. Claude API 超时或限流

**错误信息**：
```
anthropic.RateLimitError: Rate limit exceeded
```

**解决方案**：

1. **等待限流重置**（通常1分钟）

2. **减少批处理大小**
   编辑 `backend/app/analyzer.py`：
   ```python
   # 将 batch_size 从 50 改为 20
   batch_size: int = 20
   ```

3. **增加重试延迟**
   ```python
   import time
   time.sleep(60)  # 等待60秒后重试
   ```

---

## 🔧 环境相关问题

### 14. Git Bash 中文乱码

**问题**：中文显示为乱码

**解决方案**：
```bash
# 在 Git Bash 中执行
git config --global core.quotepath false
export LANG=zh_CN.UTF-8
```

---

### 15. 文件路径问题（Windows）

**问题**：路径中包含空格导致错误

**解决方案**：
```bash
# 使用引号包裹路径
cd "C:/Users/Your Name/Documents/Claude/Stock"

# 或避免使用包含空格的路径
```

---

### 16. 权限错误

**错误信息**：
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**：

**Windows**：
- 以管理员身份运行终端
- 或修改文件夹权限

**Linux/Mac**：
```bash
chmod +x backend/start.sh
```

---

## 💡 性能优化问题

### 17. 内存不足

**问题**：处理大量数据时内存不足

**解决方案**：

1. **减少数据量**
   ```python
   # 只获取最近1年数据
   YEARS_OF_DATA=1
   ```

2. **分批处理**
   修改预测逻辑，一次处理更少的股票

3. **增加虚拟内存**（Windows）
   - 系统设置 → 高级系统设置 → 性能 → 高级 → 虚拟内存

---

### 18. 预测时间过长

**问题**：预测3-10分钟太慢

**解决方案**：

1. **减少分析的股票数量**
2. **减少历史数据天数**（从30天改为20天）
3. **使用更快的 Claude 模型**（如 Haiku，但精度可能降低）

---

## 🆘 仍然无法解决？

如果以上方法都无法解决您的问题：

1. **查看完整日志**
   ```bash
   # 后端日志
   uvicorn app.main:app --reload --log-level debug
   ```

2. **检查版本兼容性**
   ```bash
   python --version  # 应该是 3.10+
   node --version    # 应该是 18+
   ```

3. **查阅文档**
   - [README.md](README.md) - 完整使用手册
   - [INSTALL.md](INSTALL.md) - 安装指南
   - [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - 架构说明

4. **重新安装**
   ```bash
   # 删除虚拟环境
   rm -rf venv/  # 或 conda env remove -n stock-prediction

   # 重新按照 START_HERE.md 安装
   ```

---

## 📋 调试检查清单

运行前确认：

- [ ] Python 3.10+ 已安装
- [ ] Node.js 18+ 已安装
- [ ] 虚拟环境已激活（命令行前有 `(venv)` 或 `(stock-prediction)`）
- [ ] 依赖已安装（`pip list` 能看到 fastapi, anthropic 等）
- [ ] `.env` 文件已创建且 API Key 正确
- [ ] 后端能访问（http://localhost:8000 返回 JSON）
- [ ] 前端能访问（http://localhost:3000 显示界面）
- [ ] 防火墙未阻止 8000 和 3000 端口

---

**最后更新**：2025-12-03

如有其他问题，请参考 [README.md](README.md) 的完整文档。
