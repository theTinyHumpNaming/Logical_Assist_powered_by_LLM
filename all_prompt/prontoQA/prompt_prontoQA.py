"""
注意：该代码已经废弃。
你需要把下面的instruction_prompt放到该文件夹中的instruction.txt中，首尾不留换行。
把task_description, few_shot_example, 以及实际问题合并到文件夹的user.txt中，首尾不留换行。
refine_code.txt作为代码报错的指引
refine_semantic.txt作为语义错误的指引
在完成所有工作后删除该文件，文件夹中应只保留四个prompt

特殊格式要求：
所有文件除下面说明外不可附带大括号

代码块必须为标准的形式：
```python
print('hello world')
#注意最后的三个引号前不能有符号
```

user.txt末尾7行必须为：
>>>>>>>>>>>>>>>>>>>>>>>>>>>>
[Problem]:
{problem_text}
[Question]:
{question_text}
[Options]:
{options_text}

refine_code.txt和refine_semantic.txt的末尾7行也需如此。
同时该二者还需在这上方有{info_text}

应该注意refine_semantic.txt的info_text是另一个llm给出的具体信息，
而refine_code.txt中的info_text有可能是说明无法提取python代码的错误，也有可能是Z3代码运行过程中的报错
"""

def build_prompt_prontoqa(problem_text, question_text, error_feedback=None):
    """为 ProntoQA 数据集构建 Prompt
    
    Args:
        problem_text: 问题描述文本
        question_text: 具体问题文本
        error_feedback: 错误反馈信息（用于自我细化），可选
    
    Returns:
        完整的 Prompt 字符串
    """
    # [Instruction Prompt] - 论文 Appendix A Page 9
    # 包含格式规范和硬性约束（如变量不重复定义、关系数量对齐）
    instruction_prompt = """
You should write in the format as comment in python script as follows:
# Define boolean variables for all entities: <the entities you generate>
# Create a solver instance: solver = Solver()
# Parse the problem into relationships: <Relationships you generate>
# Create statements to be checked: <Statements to be checked>
# Check if satisfy the condition: print A if the statement is true and B if the statement is false

You must meet the following requirements:
1. The output should be a python script of the format ```python ... ```
2. All boolean variables should be defined, and you should only define each variable once, not multiple times.
3. Number of Relationships you generate should be the same as number of sentences in the [Problem] (A sentence is defined as ending with ".").
"""

    # [User Prompt] - 论文 Appendix A Page 8
    # 包含任务逻辑步骤
    task_description = """
Task Description: You are given a problem description and a question. The task is to write a python script which includes:
1) Define all variables for all entities in the problem. You should write a comment indicating which sentence the entity is in.
2) Create a solver instance.
3) Parse the problem into relationships based on the defined entities, you should only use 'Implies' and 'Not' in this part. You should write a comment indicating which sentence the relationship is in.
4) Create statements to be checked.
5) Check if the solver can find a model that satisfies the conditions, if true, return A, if false, return B.
"""

    # [Few-shot Example] - 论文 Appendix A Page 8
    few_shot_example = """
Following is an example to follow:
Problem:
Every zumpus is aggressive. Zumpuses are Wumpuses. Wumpuses are not small.
Wumpuses are aggressive. Polly is zumpus.
Question:
Is the following statement true or false? Polly is not small.
Options:
A, B

```python
from z3 import *
# Define boolean variables for all entities
# Every zumpus is aggressive
zumpus = Bool("zumpus")
aggressive = Bool("aggressive")
# Zumpuses are Wumpuses
# zumpus has been defined before
wumpus = Bool("wumpus")
# Wumpuses are not small.
# Wumpuses has been defined before
small = Bool("small")
# Wumpuses are aggressive.
# Wumpuses has been defined before
# Aggressive has been defined before
# Polly is zumpus.
polly = Bool("polly")
# Zumpuses has been defined before

# Create a solver instance
solver = Solver()

# Parse the problem into relationships
# Every zumpus is aggressive
solver.add(Implies(zumpus, aggressive))
# Zumpuses are Wumpuses
solver.add(Implies(zumpus, wumpus))
# Wumpuses are not small
solver.add(Implies(wumpus, Not(small)))
# Wumpuses are aggressive
solver.add(Implies(wumpus, aggressive))
# Polly is zumpus
solver.add(Implies(polly, zumpus))
# Create facts in the problem
solver.add(polly)

# Create statements to be checked
# Polly is not small.
solver.add(polly, Not(small))

# Check if the solver can find a model that satisfies the conditions
if solver.check() == sat:
    print("A") # The statement is true
else:
    print("B") # The statement is false
```
"""

    # 组合 Prompt
    full_prompt = f"{instruction_prompt}\n{task_description}\n{few_shot_example}\n"
    full_prompt += f">>>>>>>>>>>>>>>>>>>>>>>>>>>>\n[Problem]:\n{problem_text}\n\n[Question]:\n{question_text}\n[Options]:\nA, B\n"

    # [Self-Refinement] - 错误反馈机制
    if error_feedback:
        full_prompt += f"\nFeedback: There is an error when the code is executed, and the error is \"{error_feedback}\". Please regenerate the code to fix the error."

    return full_prompt
