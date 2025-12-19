"""
LogicalDeduction 数据集的 Prompt 模板模块
"""
import re


def build_prompt_logicaldeduction(problem_text, question_text, options_text, error_feedback=None):
    """为 LogicalDeduction 数据集构建 Prompt"""
    opts = {}
    matches = re.findall(
        r"(?:^|\n)([A-Z])[\)\.\:]\s*(.*?)(?=(?:\n[A-Z][\)\.\:])|$)",
        options_text,
        re.DOTALL,
    )
    for letter, text in matches:
        opts[letter] = text.strip()
    if not opts:
        opts = {chr(ord("A") + i): f"Option {chr(ord('A') + i)}" for i in range(5)}
    option_lines = "\n".join([f"# Option {k}: \"{v}\"" for k, v in sorted(opts.items())])

    instruction_prompt = """You are an expert in translating logic puzzles into Z3 Python code.

Follow this checklist and do not skip steps:
- Extract all distinct entities; set N = entity count. Do not assume N=5.
- Axis: 1 = leftmost / oldest / cheapest / first / best rank; N = rightmost / newest / most expensive / last / worst rank.
- Absolute positions:
  * "kth from left/first/oldest/cheapest" → k
  * "kth from right/last/newest/most expensive" or "kth-newest" / "kth-most expensive" → N + 1 - k
  * "second-to-last" → N - 1; "last/rightmost/newest/most expensive/worst" → N; "first/leftmost/cheapest/best" → 1
- Comparisons: left of / older / cheaper / less expensive / before / above / better → < ; right of / newer / more expensive / after / below / worse → >.
- Golf/competition: "finished/placed above" = smaller (better); "finished/placed below" = larger (worse). Respect the stated mapping 1..N.
- Add domain 1..N and Distinct on all variables. Apply each textual rule exactly once; never flip or double-count (e.g., "third from the left" = 3, not N+1-3).
- When checking options, derive the condition exactly from the option text and print only the matching letter (no extra output).
Output ONLY the Python script."""

    task_description = f"""
## Code Template
```python
from z3 import *

# Define variables for all entities (1..N in the chosen order)
# ...
solver = Solver()

# Domain and distinctness
# solver.add(v >= 1, v <= N) for each variable
# solver.add(Distinct(all_vars))

# Problem constraints from the text
# ...

if solver.check() == sat:
    m = solver.model()
    # Evaluate positions for every entity
    # Options to check (print only the matching letter):
{option_lines}
    # Example: if <Entity> == <position>: print("A")
else:
    print("Error: Unsatisfiable")
```
"""

    few_shot_example = """
## Example 1 (N=5, left/right positions)
Problem: On a branch, there are five birds: a quail, an owl, a raven, a falcon, and a robin. The owl is the leftmost. The robin is to the left of the raven. The quail is the rightmost. The raven is the third from the left. The falcon is the second from the right.
Question: Which is the second from the right?
Options: A) quail B) owl C) raven D) falcon E) robin

```python
from z3 import *

# N = 5, Mapping: 1 = leftmost, 5 = rightmost
Quail, Owl, Raven, Falcon, Robin = Ints('Quail Owl Raven Falcon Robin')
birds = [Quail, Owl, Raven, Falcon, Robin]

solver = Solver()
for b in birds:
    solver.add(b >= 1, b <= 5)
solver.add(Distinct(birds))

# "The owl is the leftmost" → position 1
solver.add(Owl == 1)

# "The robin is to the left of the raven" → Robin < Raven
solver.add(Robin < Raven)

# "The quail is the rightmost" → position N = 5
solver.add(Quail == 5)

# "The raven is the third from the left" → position 3
solver.add(Raven == 3)

# "The falcon is the second from the right" → N+1-2 = 5+1-2 = 4
solver.add(Falcon == 4)

if solver.check() == sat:
    m = solver.model()
    quail_pos = m.eval(Quail).as_long()
    owl_pos = m.eval(Owl).as_long()
    raven_pos = m.eval(Raven).as_long()
    falcon_pos = m.eval(Falcon).as_long()
    robin_pos = m.eval(Robin).as_long()
    
    # "second from the right" when N=5 → position 4
    if quail_pos == 4: print("A")
    elif owl_pos == 4: print("B")
    elif raven_pos == 4: print("C")
    elif falcon_pos == 4: print("D")
    elif robin_pos == 4: print("E")
else:
    print("Error: Unsatisfiable")
```

## Example 2 (N=7, cheap/expensive)
Problem: A fruit stand sells seven fruits: kiwis, plums, mangoes, watermelons, pears, peaches, and oranges. The pears are the third-cheapest. The kiwis are the second-most expensive. The mangoes are the third-most expensive. The peaches are the second-cheapest.
Question: Which is the cheapest?
Options: A) kiwis B) plums C) mangoes D) watermelons E) pears F) peaches G) oranges

```python
from z3 import *

# N = 7, Mapping: 1 = cheapest, 7 = most expensive
Kiwis, Plums, Mangoes, Watermelons, Pears, Peaches, Oranges = Ints('Kiwis Plums Mangoes Watermelons Pears Peaches Oranges')
fruits = [Kiwis, Plums, Mangoes, Watermelons, Pears, Peaches, Oranges]

solver = Solver()
for f in fruits:
    solver.add(f >= 1, f <= 7)
solver.add(Distinct(fruits))

# "third-cheapest" → position 3
solver.add(Pears == 3)

# "second-most expensive" → N+1-2 = 7+1-2 = 6
solver.add(Kiwis == 6)

# "third-most expensive" → N+1-3 = 7+1-3 = 5
solver.add(Mangoes == 5)

# "second-cheapest" → position 2
solver.add(Peaches == 2)

if solver.check() == sat:
    m = solver.model()
    kiwis_pos = m.eval(Kiwis).as_long()
    plums_pos = m.eval(Plums).as_long()
    mangoes_pos = m.eval(Mangoes).as_long()
    watermelons_pos = m.eval(Watermelons).as_long()
    pears_pos = m.eval(Pears).as_long()
    peaches_pos = m.eval(Peaches).as_long()
    oranges_pos = m.eval(Oranges).as_long()
    
    # "cheapest" → position 1
    if kiwis_pos == 1: print("A")
    elif plums_pos == 1: print("B")
    elif mangoes_pos == 1: print("C")
    elif watermelons_pos == 1: print("D")
    elif pears_pos == 1: print("E")
    elif peaches_pos == 1: print("F")
    elif oranges_pos == 1: print("G")
else:
    print("Error: Unsatisfiable")
```

## Example 3 (Golf tournament)
Problem: In a golf tournament, there were five golfers: Dan, Amy, Eve, Ana, and Mya. Dan finished above Eve. Dan finished below Mya. Amy finished third. Ana finished second-to-last.
Question: Who finished last?
Options: A) Dan B) Amy C) Eve D) Ana E) Mya

```python
from z3 import *

# N = 5, Mapping: 1 = first place, 5 = last place
Dan, Amy, Eve, Ana, Mya = Ints('Dan Amy Eve Ana Mya')
golfers = [Dan, Amy, Eve, Ana, Mya]

solver = Solver()
for g in golfers:
    solver.add(g >= 1, g <= 5)
solver.add(Distinct(golfers))

# "above" in golf = better rank = smaller number
solver.add(Dan < Eve)

# "below" in golf = worse rank = bigger number
solver.add(Dan > Mya)

# "third" → position 3
solver.add(Amy == 3)

# "second-to-last" → N+1-2 = 5+1-2 = 4
solver.add(Ana == 4)

if solver.check() == sat:
    m = solver.model()
    dan_pos = m.eval(Dan).as_long()
    amy_pos = m.eval(Amy).as_long()
    eve_pos = m.eval(Eve).as_long()
    ana_pos = m.eval(Ana).as_long()
    mya_pos = m.eval(Mya).as_long()
    
    # "last" → position N = 5
    if dan_pos == 5: print("A")
    elif amy_pos == 5: print("B")
    elif eve_pos == 5: print("C")
    elif ana_pos == 5: print("D")
    elif mya_pos == 5: print("E")
else:
    print("Error: Unsatisfiable")
```
"""

    full_prompt = f"{instruction_prompt}\n{task_description}\n{few_shot_example}\n"
    full_prompt += f"{'='*40}\nNow solve:\n{'='*40}\n\nProblem: {problem_text}\n\nQuestion: {question_text}\n\nOptions:\n{options_text}\n"

    if error_feedback:
        if "unexpected output" in error_feedback or "Expected" in error_feedback:
            full_prompt += "\nFeedback: Previous code printed extra output. Only print the answer letter."
        else:
            full_prompt += f'\nFeedback: Error occurred: "{error_feedback}". Please fix.'

    return full_prompt
