# 翻译模块功能说明

## 新增功能

本次更新为 EnhancingLLM 项目添加了**数据集翻译模块**，用于将逻辑推理题目标准化为 Canonical English 格式。

## 新增文件

1. **`translate.py`** - 翻译模块核心代码
   - `load_translation_prompt()` - 加载翻译提示词
   - `build_translation_messages()` - 构建翻译请求消息
   - `translate_single_problem()` - 翻译单个题目
   - `translate_dataset()` - 批量翻译数据集
   - `save_translated_dataset()` - 保存翻译结果

2. **`TRANSLATION_GUIDE.md`** - 翻译模块使用指南
   - 详细的功能说明
   - GUI 和代码两种使用方式
   - Canonical English 语法规则说明
   - 翻译示例和注意事项

## 修改文件

1. **`main.py`** 
   - 导入翻译模块: `from translate import translate_dataset, save_translated_dataset`
   - 添加 "🌐 翻译数据集" 按钮（第335行）
   - 实现 `translate_dataset()` 方法（第1104-1263行）
     - 验证输入参数
     - 检测数据集类型（目前仅支持 FOLIO）
     - 选择输出文件路径
     - 后台线程执行翻译
     - 实时显示进度和结果
     - 保存翻译结果

2. **`all_prompt\folio\translation.txt`**
   - 规范化示例格式，添加 markdown 代码块标记

## 功能特点

### 1. GUI 界面集成
- 在主界面添加了 "🌐 翻译数据集" 按钮
- 支持选择输入数据集和输出文件路径
- 实时显示翻译进度
- 显示成功/失败统计信息

### 2. 标准化格式
将自然语言逻辑问题转换为 8 种标准句式：
- All/No 全称规则
- If/If and only if 条件规则
- Some/Exactly one 存在规则
- 原子事实和关系规则

### 3. 错误处理
- 自动检测数据集类型
- 验证翻译结果完整性
- 记录失败题目的详细错误信息
- 支持 JSON 解析错误处理

### 4. 批量处理
- 支持翻译整个数据集
- 并行处理提高效率
- 进度条实时更新

## 使用方法

### 通过 GUI 使用

1. 运行主程序:
   ```bash
   python main.py
   ```

2. 配置参数:
   - 输入 API Key
   - 选择数据集文件（FOLIO 格式）
   - 选择模型（推荐 gpt-4 或 gpt-4o）

3. 点击 "🌐 翻译数据集" 按钮

4. 选择输出文件保存位置

5. 确认后开始翻译，在日志区域查看进度

### 通过代码使用

```python
from translate import translate_dataset, save_translated_dataset
import json

# 读取数据集
with open('data/FOLIO.json', 'r', encoding='utf-8') as f:
    problems = json.load(f)

# 翻译数据集
result = translate_dataset(
    api_key='your-api-key',
    dataset_type='folio',
    problems=problems,
    model='gpt-4'
)

# 保存结果
save_translated_dataset(
    result['translated_problems'], 
    'data/Standardized_FOLIO.json'
)
```

## 支持的数据集

- ✅ **FOLIO** - 完全支持
- ❌ AR-LSAT - 待实现
- ❌ LogicalDeduction - 待实现
- ❌ ProntoQA - 待实现
- ❌ ProofWriter - 待实现

## 翻译示例

**原始:**
```
"If people perform in school talent shows often, then they attend and are very engaged with school events."
```

**翻译后:**
```
"If a person performs in talent shows, then that person attends school events. If a person performs in talent shows, then that person is engaged."
```

## 技术实现

- 使用 OpenAI API（支持 GPT 和 DeepSeek 模型）
- 基于 `all_prompt/folio/translation.txt` 中的提示词
- 保留原始 JSON 结构（id, context, question, options, answer）
- 自动处理 JSON 解析和验证
- 多线程支持，不阻塞主界面

## 注意事项

1. **API 消耗**: 每个题目需要调用一次 LLM API
2. **模型选择**: 推荐使用 GPT-4 以获得更好的翻译质量
3. **数据集兼容**: 目前仅支持 FOLIO 数据集格式
4. **结果验证**: 建议人工抽查部分翻译结果

## 后续改进方向

1. 支持更多数据集类型（AR-LSAT, LogicalDeduction 等）
2. 添加翻译质量评估
3. 支持批量重试失败的题目
4. 添加翻译缓存机制
5. 支持自定义翻译规则

## 测试

基础功能已通过测试：
- ✅ 提示词加载
- ✅ 消息构建
- ✅ JSON 解析
- ✅ 字段验证
- ⚠️ 完整翻译流程需要有效的 API Key

## 相关文档

- `TRANSLATION_GUIDE.md` - 详细使用指南
- `all_prompt/folio/translation.txt` - FOLIO 翻译提示词
- `translate.py` - 翻译模块源码

---

**更新日期**: 2025-12-20  
**版本**: 1.0.0  
**作者**: EnhancingLLM Team

