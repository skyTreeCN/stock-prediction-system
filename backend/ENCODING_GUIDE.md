# Python 编码问题排查指南

## 问题发现 (2025-12-11)

### 症状
在Windows环境下直接用 `python -c "from app.main import app"` 测试导入时，出现：
```
UnicodeEncodeError: 'cp932' codec can't encode character '\u2713' in position 0
```

### 根本原因
- Windows系统的stdout默认编码是 **cp932** (日文编码)
- cp932不支持中文字符和emoji符号（如 ✓✗🔥⚠️💡📊等）
- 通过uvicorn启动时会自动设置UTF-8，所以以前没发现问题

## 如何避免此问题

### 1. 启动API时设置环境变量（推荐）

使用提供的启动脚本：
```bash
cd backend
start_api.bat
```

或手动设置：
```bash
set PYTHONIOENCODING=utf-8
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 检查编码环境

```python
import sys
print(f"stdout encoding: {sys.stdout.encoding}")  # 应该是 utf-8
print(f"default encoding: {sys.getdefaultencoding()}")  # utf-8
```

### 3. 测试导入时注意

如果要在命令行直接测试导入：
```bash
# 错误方式（会触发cp932错误）
python -c "from app.main import app"

# 正确方式（设置UTF-8）
PYTHONIOENCODING=utf-8 python -c "from app.main import app"
```

## 诊断步骤

当遇到UnicodeEncodeError时：

1. **检查环境变量**
   ```bash
   echo $PYTHONIOENCODING  # 应该是 utf-8
   ```

2. **检查Python编码**
   ```python
   import sys
   print(sys.stdout.encoding)  # 如果是cp932就有问题
   ```

3. **确认是否通过正确方式启动**
   - ✅ uvicorn启动：自动处理编码
   - ✅ start_api.bat启动：已设置UTF-8
   - ❌ 直接python启动：可能使用cp932

## 为什么以前能运行

1. **通过uvicorn启动**：uvicorn会自动设置正确的编码
2. **通过IDE运行**：IDE通常会设置UTF-8环境
3. **只在今天测试时暴露**：直接用`python -c`测试导入触发了print语句

## 今后注意事项

### 开发时
- 使用 [start_api.bat](start_api.bat) 启动API
- 测试导入时设置 `PYTHONIOENCODING=utf-8`
- 新增代码可以使用emoji和中文（已有保护措施）

### 代码审查时
- 不需要避免emoji和中文
- 确保启动脚本包含 `PYTHONIOENCODING=utf-8`
- 如果遇到编码错误，首先检查环境变量

### 部署时
- 在启动脚本或systemd配置中设置环境变量
- 或在代码入口处强制设置编码：
  ```python
  import sys
  import io
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
  ```

## 相关文件

- [start_api.bat](start_api.bat) - 带编码设置的API启动脚本
- [app/main.py](app/main.py) - 主API入口
- [app/analyzer.py](app/analyzer.py) - 分析器（包含emoji输出）

## 参考

- Python文档: https://docs.python.org/3/library/sys.html#sys.stdout
- PYTHONIOENCODING: https://docs.python.org/3/using/cmdline.html#envvar-PYTHONIOENCODING
