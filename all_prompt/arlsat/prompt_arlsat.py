"""
AR-LSAT 数据集的 Prompt 模板模块

AR-LSAT（Analytical Reasoning - LSAT）是逻辑推理考试的一部分，
主要涉及约束满足问题（scheduling、arrangement 等）。
"""

def build_prompt_arlsat(context, question, options, error_feedback=None):
    """为 AR-LSAT 数据集构建 Prompt
    
    Args:
        context: 场景描述和约束条件
        question: 具体问题
        options: 选项列表
        error_feedback: 错误反馈信息（用于自我细化），可选
    
    Returns:
        完整的 Prompt 字符串
    """
    # [Instruction Prompt]
    instruction_prompt = """
You should write in the format as comment in python script as follows:
# Define variables for all entities and constraints
# Create a solver instance: solver = Solver()
# Add constraints based on the problem description
# Create statements to be checked
# Check if the statement is satisfied and return the correct option letter

You must meet the following requirements:
1. The output should be a python script of the format ```python ... ```
2. Use appropriate Z3 variables (Bool, Int, etc.) based on the problem type
3. Encode all constraints from the problem description
4. Return only a single letter (A, B, C, D, or E) as the final answer
5. Comment which option each letter represents
"""

    # [Task Description]
    task_description = """
Task Description: You are given an analytical reasoning problem with constraints.
1) Define all variables needed to represent the entities and their properties
2) Create a Z3 solver instance
3) Add all constraints mentioned in the problem
4) Evaluate the given options to find which one satisfies all constraints
5) Return the letter of the correct option (A, B, C, D, or E)
"""

    # [Few-shot Example] - Simple scheduling example
    few_shot_example = """
Following is an example to follow:
Context:
Three people (Alice, Bob, Carol) have three tasks (1, 2, 3) assigned to them.
Alice must do task 1. Bob cannot do task 1. Carol can do any task.
Question:
Which of the following is a valid assignment?
Options:
A) Alice: 1, Bob: 2, Carol: 3
B) Alice: 2, Bob: 1, Carol: 3
C) Alice: 3, Bob: 1, Carol: 2

```python
from z3 import *

# Define boolean variables for assignments
alice_1 = Bool("alice_1")
alice_2 = Bool("alice_2")
alice_3 = Bool("alice_3")
bob_1 = Bool("bob_1")
bob_2 = Bool("bob_2")
bob_3 = Bool("bob_3")
carol_1 = Bool("carol_1")
carol_2 = Bool("carol_2")
carol_3 = Bool("carol_3")

# Create solver
solver = Solver()

# Add constraints: each person does exactly one task
solver.add(Or(alice_1, alice_2, alice_3))
solver.add(Or(bob_1, bob_2, bob_3))
solver.add(Or(carol_1, carol_2, carol_3))

# Each task is done by exactly one person
solver.add(Or(alice_1, bob_1, carol_1))
solver.add(Or(alice_2, bob_2, carol_2))
solver.add(Or(alice_3, bob_3, carol_3))

# Alice must do task 1
solver.add(alice_1)
# Bob cannot do task 1
solver.add(Not(bob_1))

# Check each option
# Option A: Alice: 1, Bob: 2, Carol: 3
solver.push()
solver.add(alice_1, bob_2, carol_3)
if solver.check() == sat:
    print("A")
else:
    solver.pop()
    # Check Option B and C similarly...
    print("A")
solver.pop()
```
"""

    # 组合 Prompt
    options_str = "\\n".join(options)
    full_prompt = f"{instruction_prompt}\n{task_description}\n{few_shot_example}\n"
    full_prompt += f">>>>>>>>>>>>>>>>>>>>>>>>>>>>\n[Context]:\n{context}\n\n[Question]:\n{question}\n[Options]:\n{options_str}\n"

    # [Self-Refinement]
    if error_feedback:
        full_prompt += f"\nFeedback: There is an error when the code is executed, and the error is \"{error_feedback}\". Please regenerate the code to fix the error."

    return full_prompt
