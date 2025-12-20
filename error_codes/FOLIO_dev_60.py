# Problem: FOLIO_dev_60
# Error: 代码执行错误（repair修复后仍失败）: 'BoolRef' object is not callable
#==============================================================================

from z3 import *

# Step 1: Scan context and question, list ALL predicates needed
# Predicates: city_in_state, same_state, not_in_state
# Now define ALL boolean variables BEFORE using them
billings_in_mt = Bool("billings_in_mt")
butte_in_mt = Bool("butte_in_mt")
helena_in_mt = Bool("helena_in_mt")
missoula_in_mt = Bool("missoula_in_mt")
white_springs_in_mt = Bool("white_springs_in_mt")
pierre_in_mt = Bool("pierre_in_mt")

# Step 2: Create solver
solver = Solver()

# Step 3: Encode ONLY context constraints (NOT the query!)
# Rule 1: Billings is a city in Montana
solver.add(Implies(billings_in_mt, True))

# Rule 2: Montana includes the cities of Butte, Helena, and Missoula
solver.add(And(butte_in_mt, helena_in_mt, missoula_in_mt))

# Rule 3: White Sulphur Springs and Butte are cities in the same state
solver.add(same_state(white_springs_in_mt, butte_in_mt))

# Rule 4: The city of Pierre is not in Montana
solver.add(Not(pierre_in_mt))

# Rule 5: Any city in Butte is not in Pierre
solver.add(Implies(butte_in_mt, Not(pierre_in_mt)))

# Step 4: Check for contradictions in base constraints
if solver.check() == unsat:
    print("Error: Base constraints are contradictory")
    exit()

# Step 5: Test the query "Montana is home to the city of Missoula" - Do NOT add it to base solver!
# Test 1: Can Missoula be in Montana? (query is true)
solver.push()
solver.add(missoula_in_mt)
can_be_true = (solver.check() == sat)
solver.pop()

# Test 2: Can Missoula NOT be in Montana? (query is false)
solver.push()
solver.add(Not(missoula_in_mt))
can_be_false = (solver.check() == sat)
solver.pop()

# Step 6: Determine answer based on both tests
if can_be_true and can_be_false:
    print("C")  # Uncertain - both are possible
elif can_be_true and not can_be_false:
    print("A")  # True - Missoula is in Montana
else:
    print("B")  # False - Missoula is not in Montana