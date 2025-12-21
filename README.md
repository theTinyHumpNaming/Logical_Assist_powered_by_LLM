# Logical_Assist_powered_by_LLM

## 逻辑推理评测系统

一个基于大语言模型（LLM）的逻辑推理能力评测系统，使用 Z3 约束求解器进行形式化验证。

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue)](https://github.com/theTinyHumpNaming/Logical_Assist_powered_by_LLM)

## 项目简介

本系统旨在评测大语言模型在逻辑推理任务上的表现，支持多种逻辑推理数据集。系统通过引导 LLM 生成 Z3 Python 代码来形式化表达逻辑问题，然后使用 Z3 求解器验证答案的正确性。

### 主要特性

- 🎯 **多数据集支持**：支持 5 种主流逻辑推理数据集
  - ProntoQA
  - FOLIO
  - Logical Deduction
  - AR-LSAT
  - ProofWriter

- 🤖 **多模型兼容**：支持 OpenAI 和 DeepSeek API
  - GPT-4、GPT-3.5
  - DeepSeek Chat/Reasoner

- 🔧 **智能修复机制**：
  - 自动修复 Z3 代码语法错误
  - 语义检查和代码精炼
  - 多轮迭代优化

- 🗳️ **多数投票模式**：
  - 每题运行3次取多数结果
  - 提高答案准确性和稳定性
  - 失败自动降级处理

- 📊 **可视化界面**：基于 tkinter 的图形用户界面
  - 实时显示评测进度
  - 详细的日志输出
  - 评测结果统计

- ⚡ **并发处理**：支持多线程并发评测，提升效率

## 系统架构

```
Logical_Assist_powered_by_LLM/
├── main.py                 # 主程序入口（GUI界面）
├── request.py              # LLM API 请求封装
├── z3_execute.py          # Z3 代码执行模块
├── repair.py              # 代码自动修复模块
├── semantic_check.py      # 语义检查模块
├── translate.py           # 数据集翻译模块
├── dataset_and_prompt.py  # 数据集和提示词管理
├── requirements.txt       # 项目依赖
│
├── data/                  # 数据集目录
│   ├── ProntoQA.json
│   ├── FOLIO.json
│   ├── LogicalDeduction.json
│   ├── AR-LSAT.json
│   └── ProofWriter.json
│
├── all_prompt/            # 提示词模板目录
│   ├── prontoQA/
│   ├── folio/
│   ├── logicaldeduction/
│   ├── arlsat/
│   └── proofwriter/
│
├── logs/                  # 评测日志目录
├── error_codes/           # 错误代码样例
└── keys.txt               # API密钥配置
```

## 安装指南

### 环境要求

- Python 3.8+
- Windows/Linux/macOS

### 安装步骤

1. **克隆项目**

```bash
git clone https://github.com/your-username/Logical_Assist_powered_by_LLM.git
cd Logical_Assist_powered_by_LLM
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

主要依赖包：
- `z3-solver>=4.12.0` - Z3 约束求解器
- `openai>=1.0.0` - OpenAI API 客户端

3. **配置 API 密钥**

在项目根目录创建 `keys.txt` 文件：

```
openai:sk-your-openai-api-key
deepseek:sk-your-deepseek-api-key
```

## 使用说明

### 启动程序

```bash
python main.py
```

### GUI 界面使用

1. **配置 API**
   - 选择要使用的 LLM 模型（OpenAI 或 DeepSeek）
   - 输入或选择对应的 API Key
   - 点击"测试连接"验证 API 可用性

2. **选择数据集**
   - 点击"选择数据集文件"按钮
   - 选择要评测的 JSON 格式数据集文件
   - 系统会自动检测数据集类型

3. **配置评测参数**
   - **调用模式**：选择 direct 或 single_text 模式
   - **语义检查**：启用/禁用语义检查功能
   - **代码修复**：启用/禁用代码修复功能
   - **Repair**：启用/禁用执行前自动修复
   - **多数投票**：启用/禁用多数投票模式（运行3次取多数）
   - **题目限制**：限制评测的题目数量（0 表示全部）
   - **Workers数量**：并行处理的工作线程数

4. **开始评测**
   - 点击"开始评测"按钮
   - 实时查看评测进度和日志
   - 评测完成后查看结果统计

5. **查看结果**
   - 正确题目数量和准确率
   - 详细的日志信息
   - 结果保存在 `logs/` 目录

### 命令行使用

如果需要自定义使用，可以直接调用核心模块：

```python
from request import LLMClient
from z3_execute import execute_z3_code
from dataset_and_prompt import build_initial_messages_for_all_datasets

# 创建 LLM 客户端
client = LLMClient(api_key="your-api-key", model="gpt-4")

# 构建提示词
messages = build_initial_messages_for_all_datasets(problem, dataset_type="prontoqa")

# 请求 LLM 生成代码
response = client.query(messages)

# 执行 Z3 代码
result, error, repair_log = execute_z3_code(response)
```

## 工作流程

```
┌─────────────┐
│  读取题目    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  构建提示词  │ (根据数据集类型)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  LLM生成代码 │ (Z3 Python代码)
└──────┬──────┘
       │
       ▼
┌─────────────┐      失败
│  执行Z3代码  │ ─────────┐
└──────┬──────┘          │
       │ 成功             ▼
       │          ┌─────────────┐
       │          │  语法修复    │
       │          └──────┬──────┘
       │                 │
       │                 ▼
       │          ┌─────────────┐
       │          │  语义检查    │
       │          └──────┬──────┘
       │                 │
       │                 └───────> 重新执行
       │
       ▼
┌─────────────┐
│  验证答案    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  输出结果    │
└─────────────┘
```

## 核心模块说明

### 1. Z3 执行模块 (`z3_execute.py`)

- 线程安全的 Z3 代码执行
- 支持超时控制
- 自动捕获执行输出和错误

### 2. 代码修复模块 (`repair.py`)

自动修复常见错误：
- 括号不匹配
- 导入语句缺失
- 变量名错误
- 语法错误

### 3. 语义检查模块 (`semantic_check.py`)

- 验证 Z3 代码的逻辑正确性
- 检查约束是否完整
- 引导 LLM 改进代码质量

### 4. 请求模块 (`request.py`)

- 封装 OpenAI API 调用
- 支持流式和非流式响应
- 自动重试和错误处理

### 5. 数据集管理 (`dataset_and_prompt.py`)

- 自动检测数据集类型
- 为不同数据集构建专用提示词
- 支持单次和多轮对话模式

## 数据集格式

每个数据集应为 JSON 格式，包含以下字段：

```json
[
  {
    "id": "ProntoQA_dev_0",
    "context": "逻辑推理的上下文信息...",
    "question": "需要回答的问题",
    "options": ["A. 选项1", "B. 选项2", ...],
    "label": 0
  }
]
```

## 配置说明

### API 密钥配置 (`keys.txt`)

```
openai:sk-xxxxxxxxxxxxx
deepseek:sk-xxxxxxxxxxxxx
```

### 提示词自定义

每个数据集的提示词位于 `all_prompt/<dataset_name>/` 目录：

- `instruction.txt` - 系统指令
- `user.txt` - 用户提示词模板
- `refine_code.txt` - 代码精炼提示
- `refine_semantic.txt` - 语义检查提示

## 日志系统

### 日志级别

- **DEBUG**：详细的调试信息
- **INFO**：一般信息（默认）
- **WARNING**：警告信息
- **ERROR**：错误信息

### 日志文件

- 位置：`logs/eval_<timestamp>.log`
- 包含完整的评测过程记录
- 自动生成时间戳文件名

## 性能优化

### 并发处理

- 使用线程池并发处理多个题目
- Z3 执行使用全局锁保证线程安全
- 可配置并发数量（默认：4）

### 缓存机制

- 缓存翻译结果避免重复翻译
- 缓存 API 响应减少请求次数

### 超时控制

- Z3 代码执行超时（默认：10秒）
- API 请求超时控制
- 避免长时间阻塞

## 常见问题

### Q: 多数投票模式什么时候使用？

A: 当需要提高答案准确性时可以启用多数投票模式。注意：
- 会增加3倍的API调用次数
- 处理时间约增加到3倍
- 适合对准确性要求高的场景
- 失败情况下默认选择选项A

### Q: Z3 代码执行失败怎么办？

A: 系统会自动尝试修复常见错误。如果多次修复失败，可以：
- 增加"最大修正次数"参数
- 启用语义检查
- 检查日志文件中的详细错误信息

### Q: API 请求失败？

A: 请检查：
- API Key 是否正确
- 网络连接是否正常
- API 服务是否可用
- 是否达到了 API 调用限制

### Q: 评测速度太慢？

A: 可以尝试：
- 增加并发数（注意 API 限制）
- 减少最大修正次数
- 使用更快的模型

### Q: 准确率偏低？

A: 可以尝试：
- 增加语义检查次数
- 使用更强大的模型（如 GPT-4）
- 调整提示词模板

## 技术细节

### Z3 线程安全

Z3 Python API 不是线程安全的，系统使用全局互斥锁 (`_z3_lock`) 来保护所有 Z3 操作，确保任何时刻只有一个线程在执行 Z3 代码。

### 自动修复机制

1. **快速括号修复**：自动补全缺失的括号
2. **导入语句修复**：添加必要的 Z3 导入
3. **变量名修复**：修正常见的变量名错误
4. **语法错误修复**：修复常见的 Python 语法错误

### 语义检查流程

1. 提取 Z3 代码和执行结果
2. 让 LLM 检查代码逻辑是否正确
3. 根据反馈精炼代码
4. 重新执行验证

## 开发指南

### 添加新数据集支持

1. 在 `all_prompt/` 下创建新目录
2. 添加提示词模板文件
3. 在 `dataset_and_prompt.py` 中添加检测逻辑
4. 实现提示词构建函数

### 自定义修复规则

在 `repair.py` 中添加新的修复函数：

```python
def custom_fix(code: str) -> str:
    # 实现自定义修复逻辑
    return fixed_code
```

### 扩展 LLM 支持

在 `request.py` 中添加新的 API 客户端：

```python
class CustomLLMClient(LLMClient):
    def __init__(self, api_key: str, **kwargs):
        # 实现自定义客户端
        pass
```

## 贡献指南

欢迎提交 Issue 和 Pull Request！

在提交代码前，请确保：
- 代码符合 PEP 8 规范
- 添加必要的注释
- 更新相关文档

## 许可证

本项目仅用于学术研究和教育目的。

## 项目链接

- **GitHub**: [https://github.com/theTinyHumpNaming/Logical_Assist_powered_by_LLM](https://github.com/theTinyHumpNaming/Logical_Assist_powered_by_LLM)
- **文档**: 查看本 README 文件
- **问题反馈**: [提交 Issue](https://github.com/theTinyHumpNaming/Logical_Assist_powered_by_LLM/issues)

## 联系方式

如有问题或建议，欢迎通过以下方式联系：
- 在 GitHub 上提交 Issue
- 发送邮件

---

**注意**：使用本系统需要有效的 OpenAI 或 DeepSeek API 密钥，并遵守相应的使用条款。

