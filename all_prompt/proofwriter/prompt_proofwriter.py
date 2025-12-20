"""
ProofWriter 数据集的 Prompt 模板模块
"""
import re


def build_prompt_proofwriter(context: str, question: str, options_text: str, error_feedback: str = None) -> str:
    """
    为 ProofWriter 数据集构建 Prompt（判断 True / False / Unknown）
    - 事实和规则来自 context
    - 问题是一个陈述，选项通常为 A) True / B) False / C) Unknown
    """
    opts = {}
    matches = re.findall(
        r"(?:^|\n)([A-Z])[\)\.\:]\s*(.*?)(?=(?:\n[A-Z][\)\.\:])|$)",
        options_text,
        re.DOTALL,
    )
    for letter, text in matches:
        opts[letter] = text.strip()
    if not opts:
        opts = {"A": "True", "B": "False", "C": "Unknown"}
    option_lines = "\n".join([f"# Option {k}: \"{v}\"" for k, v in sorted(opts.items())])

    instruction_prompt = """You are an expert in translating natural-language facts/rules into Z3 for three-valued reasoning (True / False / Unknown).

STRICT CODE STRUCTURE (follow this exact order):
```
# 1. Domain
Entity, (E1, E2, ...) = EnumSort('Entity', [...])

# 2. Predicates - define ALL predicates here
Pred1 = Function('Pred1', Entity, BoolSort())

solver = Solver()

# 3. Facts - ONLY simple facts, NO ForAll here!
solver.add(Pred(Entity1))

# 4. Rules - define x FIRST, then ForAll statements
x = Const('x', Entity)
solver.add(ForAll([x], Implies(A(x), B(x))))

# 5. Statement
S = ...

# 6. Three-valued check
def is_true(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(Not(stmt))
    return s.check() == unsat

def is_false(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(stmt)
    return s.check() == unsat
```

KEY RULES:
1) Entities = proper names (Bob, Anne, Cat, Lion, Mouse, BaldEagle)
2) Predicates = properties/relations (Cold, Big, Young, Likes, Sees)
3) BEFORE writing code, read the QUESTION and list ALL predicates it mentions!
4) Implies(condition, conclusion) - ALWAYS needs TWO arguments!
5) ForAll ONLY after x = Const('x', Entity)

⚠️ CRITICAL CHECKLIST BEFORE SUBMITTING:
□ Did I define ALL predicates from the question? (e.g., if question asks about "Red", define Red!)
□ Are my entities ONLY proper names? (Young/Cold/Big are predicates, NOT entities!)
□ Does every Implies have TWO arguments? Implies(A) is WRONG → Implies(A, B)
□ Does every And/Or have COMMAS between arguments?
   WRONG: And(A(x) B(x)) → RIGHT: And(A(x), B(x))
   WRONG: Or(A(x) B(x)) → RIGHT: Or(A(x), B(x))
□ Is x = Const('x', Entity) defined BEFORE any ForAll?
□ Are Facts section free of ForAll? (ForAll only in Rules!)"""

    task_description = f"""
## Code Template (follow EXACTLY)
```python
from z3 import *

# 1. Domain - ALL entity names
Entity, (E1, E2, ...) = EnumSort('Entity', [...])

# 2. Predicates - define ALL (including those in question!)
Cold = Function('Cold', Entity, BoolSort())
Likes = Function('Likes', Entity, Entity, BoolSort())

solver = Solver()

# 3. Facts - simple statements, NO ForAll!
solver.add(Cold(E1))
solver.add(Not(Cold(E2)))

# 4. Rules - define x FIRST, then ForAll
x = Const('x', Entity)
solver.add(ForAll([x], Implies(Cold(x), Big(x))))

# 5. Statement from question
S = Big(E1)  # or Not(Big(E1))

# 6. Three-valued check (COPY EXACTLY!)
def is_true(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(Not(stmt))
    return s.check() == unsat

def is_false(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(stmt)
    return s.check() == unsat

if is_true(S):
    print("A")
elif is_false(S):
    print("B")
else:
    print("C")
```
"""

    few_shot_example = """
## Example 1 (Universal rules with ForAll)
Context: Bob is cold. Bob is red. If someone is cold and red then they are quiet. If someone is quiet then they are smart.
Question: Based on the above information, is the following statement true, false, or unknown? Bob is smart.
Options: A) True B) False C) Unknown

```python
from z3 import *

# 1. Domain - list ALL entities
Entity, (Bob,) = EnumSort('Entity', ['Bob'])

# 2. Predicates - define ALL predicates BEFORE using them
Cold = Function('Cold', Entity, BoolSort())
Red = Function('Red', Entity, BoolSort())
Quiet = Function('Quiet', Entity, BoolSort())
Smart = Function('Smart', Entity, BoolSort())

solver = Solver()

# 3. Facts - NO ForAll here, just direct facts about entities
solver.add(Cold(Bob))
solver.add(Red(Bob))

# 4. Rules - MUST define x BEFORE ForAll
# ⚠️ CRITICAL: And() MUST have COMMA between arguments!
# WRONG: And(Cold(x) Red(x)) - NO COMMA = SYNTAX ERROR!
# RIGHT: And(Cold(x), Red(x)) - WITH COMMA = CORRECT!
x = Const('x', Entity)
solver.add(ForAll([x], Implies(And(Cold(x), Red(x)), Quiet(x))))  # ← COMMA inside And()!
solver.add(ForAll([x], Implies(Quiet(x), Smart(x))))  # ← COMMA inside Implies()!

# 5. Statement from question
S = Smart(Bob)

# 6. Three-valued check (COPY EXACTLY!)
def is_true(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(Not(stmt))
    return s.check() == unsat

def is_false(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(stmt)
    return s.check() == unsat

if is_true(S):
    print("A")
elif is_false(S):
    print("B")
else:
    print("C")
```

## Example 2 (Entity-specific rules - NO ForAll needed)
Context: Anne is furry. Anne is nice. Dave is furry. If Anne is big and Anne is green then Anne is round. Furry people are green.
Question: Based on the above information, is the following statement true, false, or unknown? Dave is green.
Options: A) True B) False C) Unknown

```python
from z3 import *

# 1. Domain
Entity, (Anne, Dave) = EnumSort('Entity', ['Anne', 'Dave'])

# 2. Predicates
Furry = Function('Furry', Entity, BoolSort())
Nice = Function('Nice', Entity, BoolSort())
Big = Function('Big', Entity, BoolSort())
Green = Function('Green', Entity, BoolSort())
Round = Function('Round', Entity, BoolSort())

solver = Solver()

# 3. Facts
solver.add(Furry(Anne))
solver.add(Nice(Anne))
solver.add(Furry(Dave))

# 4. Rules
x = Const('x', Entity)
# Entity-specific rule: "If Anne is big and Anne is green then Anne is round"
# ⚠️ This applies ONLY to Anne, so use Implies directly on Anne (no ForAll!)
# ⚠️ CRITICAL: And(Big(Anne), Green(Anne)) - COMMA is REQUIRED!
solver.add(Implies(And(Big(Anne), Green(Anne)), Round(Anne)))  # ← COMMA inside And()!

# Universal rule: "Furry people are green" = ForAll x: Furry(x) => Green(x)
solver.add(ForAll([x], Implies(Furry(x), Green(x))))

# 5. Statement
S = Green(Dave)

# 6. Three-valued check
def is_true(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(Not(stmt))
    return s.check() == unsat

def is_false(stmt):
    s = Solver()
    s.add(*solver.assertions())
    s.add(stmt)
    return s.check() == unsat

if is_true(S):
    print("A")
elif is_false(S):
    print("B")
else:
    print("C")
```
"""

    full_prompt = f"{instruction_prompt}\n{task_description}\n{few_shot_example}\n"
    full_prompt += f"{'='*40}\nNow solve:\n{'='*40}\n\nContext:\n{context}\n\nQuestion:\n{question}\n\nOptions:\n{options_text}\n"

    if error_feedback:
        full_prompt += f'\nFeedback: Previous run failed with "{error_feedback}". Fix the code following the checklist (do not relax constraints).'

    return full_prompt

