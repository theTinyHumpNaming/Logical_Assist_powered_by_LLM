"""
FOLIO 数据集的 Prompt 模板模块

FOLIO（First-Order Logic Inference）涉及一阶逻辑推理问题，
答案为 True、False 或 Uncertain。
"""

def build_prompt_folio(context, question, options, error_feedback=None):
    """为 FOLIO 数据集构建 Prompt
    
    Args:
        context: 逻辑规则和事实
        question: 具体问题
        options: 选项列表（True, False, Uncertain）
        error_feedback: 错误反馈信息（用于自我细化），可选
    
    Returns:
        完整的 Prompt 字符串
    """
    # [Instruction Prompt]
    instruction_prompt = """
You should write in the format as comment in python script as follows:
# Define boolean variables for all predicates and entities
# Create a solver instance: solver = Solver()
# Encode all logical rules from the context
# Create assertions to check the query
# Determine if the statement is True, False, or Uncertain

You must meet the following requirements:
1. The output should be a python script of the format ```python ... ```
2. Encode all implications and logical rules using Z3 (Implies, And, Or, Not)
3. Handle uncertain cases by checking if the solver can find both satisfying and non-satisfying models
4. Return exactly one of: "A", "B", or "C" (corresponding to True, False, Uncertain)
5. Comment which letter represents which answer type
"""

    # [Task Description]
    task_description = """
Task Description: You are given a first-order logic reasoning problem with:
1) A set of logical rules and facts (context)
2) A query statement to evaluate
3) Three possible answers: True, False, or Uncertain

Your task:
1) Define boolean variables for all relevant propositions/predicates
2) Create a Z3 solver
3) Add all rules from the context as constraints
4) Check if the query statement must be True (always satisfies constraints)
5) Check if the query statement must be False (never satisfies constraints)  
6) If neither, the answer is Uncertain
7) Return the corresponding letter: A for True, B for False, C for Uncertain
"""

    # [Few-shot Example]
    few_shot_example = """
Following is an example to follow:
Context:
All dogs are animals. Spot is a dog. Some animals are fast.
Question:
Is the following statement True, False, or Uncertain? Spot is fast.
Options:
A) True
B) False
C) Uncertain

```python
from z3 import *

# Define boolean variables
spot_is_dog = Bool("spot_is_dog")
spot_is_animal = Bool("spot_is_animal")
spot_is_fast = Bool("spot_is_fast")
all_dogs_are_animals = Bool("all_dogs_are_animals")
some_animals_are_fast = Bool("some_animals_are_fast")

# Create solver
solver = Solver()

# Encode constraints from context
# All dogs are animals
solver.add(Implies(spot_is_dog, spot_is_animal))
# Spot is a dog
solver.add(spot_is_dog)
# From the above two constraints, Spot must be an animal
solver.add(spot_is_animal)

# Check if the statement "Spot is fast" must be true
# Try to find a model where Spot is NOT fast
solver.push()
solver.add(Not(spot_is_fast))
if solver.check() == sat:
    # Found a valid model where Spot is not fast, so the answer is not necessarily True
    solver.pop()
    # Try to find a model where Spot IS fast
    solver.push()
    solver.add(spot_is_fast)
    if solver.check() == sat:
        # Found valid models for both cases - answer is Uncertain
        print("C")
    else:
        # Only valid when Spot is not fast - answer is False
        print("B")
    solver.pop()
else:
    # No valid model where Spot is not fast - answer is True
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
