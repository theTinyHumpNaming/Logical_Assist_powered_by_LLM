# 修改日志

## 2025-12-19 新增：单文本模式（Single Text Mode）

### 功能描述
新增了一种LLM调用模式**"Single Text Mode"**，与原有的**"Direct Mode"**形成对比。

#### 两种模式对比

| 特性 | Direct Mode | Single Text Mode |
|------|-----------|-----------------|
| 消息结构 | system + user + assistant循环 | 单个user消息 |
| 初始消息 | 2条 (system + user) | 1条 (user) |
| 后续修复 | 扩展消息列表 | 替换整个文本 |
| 信息合并 | 保留对话历史 | 合并成大文本块 |
| 适用场景 | OpenAI标准API | 本地模型/自定义API |

### 实现修改

#### 1. UI更新 (main.py)
- **位置**：第255-267行
- **改动**：添加调用模式选择下拉菜单
  - "direct" - 默认的多轮消息模式
  - "single_text" - 新的单文本模式
- **显示**：在配置面板中新增"调用模式"选项

#### 2. 新增函数 (dataset_and_prompt.py)

**函数1：`build_single_text_message_for_all_datasets()`**
- 功能：初始调用时，将instruction和user合并成一个大文本块
- 返回：包含单个user消息的列表
- 格式：`instruction + separator + user_prompt`

**函数2：`build_next_single_text_message_for_all_datasets()`**  
- 功能：修复调用时，将历史、输出和修复指示合并
- 参数：额外接收`accumulated_context`用于积累历史
- 返回：包含单个user消息的列表
- 格式：`accumulated_context + output + fix_instructions`

#### 3. 核心逻辑更新 (main.py)

**初始化阶段**（第695-707行）
```python
if mode == "single_text":
    messages = build_single_text_message_for_all_datasets(...)
    accumulated_context = ""  # 累积上下文
else:  # direct mode
    messages = build_initial_messages_for_all_datasets(...)
```

**修复阶段**（第722-732行）
```python
if mode == "single_text":
    next_message = build_next_single_text_message_for_all_datasets(
        ..., accumulated_context
    )
    messages = next_message  # 替换
    accumulated_context += llm_output + "\n---\nError:\n" + extra_info + "\n---\n"
else:  # direct mode
    next_message = build_next_messages_for_all_datasets(...)
    messages.extend(next_message)  # 扩展
```

### 新增文件
1. **test_modes.py** - 单元测试脚本，验证两种模式的消息构建功能
2. **SINGLE_TEXT_MODE_GUIDE.md** - 详细使用文档和原理说明

### 测试结果
✅ 所有测试通过
- Direct Mode: 正常工作，保持向后兼容
- Single Text Mode: 成功生成正确的单文本消息结构
- 支持所有数据集类型：folio, logical_deduction, ar_lsat, prontoqa

### 使用方式
1. 启动应用
2. 在配置面板中选择"调用模式"
   - 默认：Direct Mode（原有方式）
   - 可选：Single Text Mode（新方式）
3. 开始评测时会自动使用选定的模式

### 性能影响
- Direct Mode：无变化（保持原有性能）
- Single Text Mode：消息数组结构简化，但文本长度增加
- 整体token消耗取决于具体使用场景和LLM实现

### 兼容性
- ✅ 完全向后兼容
- ✅ 不影响现有功能
- ✅ Direct Mode 为默认选项
- ✅ 可在任何时刻切换模式

---

## 问题排查结果

### test8.json 中的 5 个错误代码根本原因

```
错误: b'enumeration sort name is already declared'
```

**这是 Z3 的全局符号表冲突，不是代码语法错误。**

**为什么 repair.py 没有修复？**
- repair.py 只能修复代码语法错误（括号、未定义函数等）
- Z3 的 EnumSort 名称冲突是运行时环境问题
- 需要在执行前修改代码来避免名称冲突

---

## 修复方案

### 文件修改：z3_execute.py

#### 第一步：添加必要的导入（第9-10行）
```python
import uuid  # 生成唯一标识
import re    # 正则表达式替换
```

#### 第二步：在执行前修改 EnumSort 名称（第39-49行）
```python
# 为了避免 "enumeration sort name is already declared" 错误，
# 生成唯一的后缀来修改EnumSort的名称
unique_suffix = str(uuid.uuid4())[:8]

# 替换 EnumSort('Name' 为 EnumSort('Name_{unique}'
# 这样可以避免名称冲突
modified_code = re.sub(
    r"EnumSort\s*\(\s*'(\w+)'",
    lambda m: f"EnumSort('{m.group(1)}_{unique_suffix}'",
    code
)
```

#### 第三步：执行修改后的代码（第83行）
```python
exec(modified_code, global_vars)  # 原来是: exec(code, global_vars)
```

---

## 验证

### ✅ 单元测试通过
- 多次执行相同 Entity 名称的代码 → 成功
- 没有 EnumSort 重复声明错误

### ✅ 集成测试通过
- 模拟 test8.json 问题场景 → 全部成功

### ✅ 代码质量检查
- 语法检查：通过 ✓
- 导入检查：通过 ✓
- 向后兼容性：完全透明 ✓

---

## 预期效果

修复前的 test8.json：
```json
{
  "summary": {
    "total": 6,
    "correct": 0,
    "wrong": 1,
    "error": 5,        ← 都是 EnumSort 错误
    "accuracy": 0.0
  }
}
```

修复后的 test8.json（预期）：
```json
{
  "summary": {
    "total": 6,
    "correct": X,
    "wrong": Y,
    "error": 0,        ← EnumSort 错误消除
    "accuracy": Z      ← 由实际逻辑推理结果决定
  }
}
```

---

## 细节说明

### 为什么这个方案有效？

1. **Z3 的全局符号表**
   - `EnumSort('Entity', ...)` 会在 Z3 全局注册一个名为 'Entity' 的类型
   - 第二次声明相同名称时会冲突

2. **唯一后缀策略**
   - 每次执行生成不同的 UUID（如 `a1b2c3d4`, `f5e6d7c8`）
   - 变成 `'Entity_a1b2c3d4'`, `'Entity_f5e6d7c8'`
   - 全局符号表中现在有不同的名称，不会冲突
   - 逻辑推理的结果完全相同（只是名称不同）

3. **对用户透明**
   - 用户代码不需要修改
   - 修改发生在执行之前，自动进行
   - 结果完全一致

---

## 兼容性保证

- ✅ 不破坏现有代码
- ✅ 不影响逻辑推理结果
- ✅ 与 repair.py 无冲突
- ✅ 与 main.py 无冲突
- ✅ 支持所有原有功能
- ✅ 无性能明显下降（正则表达式替换很快）

---

**修复完成时间：** 2025-12-19 18:30
**修改文件数：** 1 (z3_execute.py)
**测试状态：** ✅ 已验证
**可上线状态：** ✅ 可立即上线

