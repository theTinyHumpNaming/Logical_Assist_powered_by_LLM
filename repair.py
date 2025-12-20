"""
代码修复模块 - 在执行Z3代码前自动修复常见语法错误

主要修复的错误类型：
1. 括号不匹配 - ForAll、Implies、And等语句缺少右括号
2. 未定义的谓词/函数使用
3. 其他常见语法问题
"""

import re
from typing import Tuple, List, Optional


def repair_code(code: str) -> Tuple[str, List[str]]:
    """
    修复Z3代码中的常见语法错误
    
    Args:
        code: 原始Z3 Python代码
        
    Returns:
        (修复后的代码, 修复记录列表)
    """
    repairs = []
    repaired_code = code
    
    # 1. 修复括号不匹配
    repaired_code, bracket_repairs = fix_bracket_mismatch(repaired_code)
    repairs.extend(bracket_repairs)
    
    # 2. 修复行级括号不匹配（逐行检查）
    repaired_code, line_repairs = fix_line_brackets(repaired_code)
    repairs.extend(line_repairs)
    
    # 3. 修复未定义但被调用的函数（如in_state, same_state等） - 必须在Bool变量修复之前
    repaired_code, undefined_func_repairs = fix_undefined_function_calls(repaired_code)
    repairs.extend(undefined_func_repairs)
    
    # 4. 修复未定义的Bool变量
    repaired_code, bool_repairs = fix_undefined_bool_variables(repaired_code)
    repairs.extend(bool_repairs)
    
    # 5. 修复未定义的谓词
    repaired_code, predicate_repairs = fix_undefined_predicates(repaired_code)
    repairs.extend(predicate_repairs)
    
    # 6. 修复常见的Z3语法问题
    repaired_code, syntax_repairs = fix_common_syntax_issues(repaired_code)
    repairs.extend(syntax_repairs)
    
    # 7. 修复Python逻辑运算符（or/and）为Z3函数（Or/And）
    repaired_code, logic_repairs = fix_python_logical_operators(repaired_code)
    repairs.extend(logic_repairs)
    
    # 8. 修复未定义的量化变量（x, y等）
    repaired_code, quantifier_repairs = fix_undefined_quantifier_variables(repaired_code)
    repairs.extend(quantifier_repairs)
    
    # 9. 修复ForAll在Facts部分的问题（需要移动到Rules部分）
    repaired_code, forall_move_repairs = fix_forall_in_facts(repaired_code)
    repairs.extend(forall_move_repairs)
    
    # 10. 修复Z3表达式类型错误
    repaired_code, type_repairs = fix_z3_type_errors(repaired_code)
    repairs.extend(type_repairs)
    
    # 11. 修复Function定义错误（BoolSort应该是Entity）
    repaired_code, func_sig_repairs = fix_function_signature_errors(repaired_code)
    repairs.extend(func_sig_repairs)
    
    # 12. 修复孤立的缩进行（在注释掉某行后留下的缩进行）
    repaired_code, orphan_repairs = fix_orphaned_indented_lines(repaired_code)
    repairs.extend(orphan_repairs)
    
    # 13. 最终清理：移除孤立的括号行
    repaired_code, final_repairs = final_cleanup_orphaned_brackets(repaired_code)
    repairs.extend(final_repairs)
    
    return repaired_code, repairs


def fix_bracket_mismatch(code: str) -> Tuple[str, List[str]]:
    """
    修复全局括号不匹配
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    
    # 计算整体括号平衡
    open_parens = code.count('(')
    close_parens = code.count(')')
    
    if open_parens > close_parens:
        # 缺少右括号
        missing = open_parens - close_parens
        # 在代码末尾添加缺失的右括号（保守策略）
        # 但实际上我们更希望在正确的位置添加
        repairs.append(f"检测到缺少 {missing} 个右括号")
    
    return code, repairs


def fix_line_brackets(code: str) -> Tuple[str, List[str]]:
    """
    逐行修复括号不匹配问题
    这是主要的修复函数，针对每行solver.add()语句
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        original_line = line
        
        # 检查是否是solver.add语句或包含ForAll/Implies/And的语句
        if 'solver.add(' in line or 'ForAll(' in line or 'Implies(' in line:
            # 计算该行的括号平衡
            open_count = line.count('(')
            close_count = line.count(')')
            
            if open_count > close_count:
                # 缺少右括号，在行尾（注释之前）添加
                missing = open_count - close_count
                
                # 检查行尾是否有注释
                comment_match = re.search(r'\s*#.*$', line)
                if comment_match:
                    # 在注释前插入括号
                    comment_start = comment_match.start()
                    line = line[:comment_start].rstrip() + ')' * missing + '  ' + line[comment_start:].lstrip()
                else:
                    # 直接在行尾添加
                    line = line.rstrip() + ')' * missing
                
                repairs.append(f"第{i+1}行: 添加 {missing} 个右括号")
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), repairs


def fix_undefined_bool_variables(code: str) -> Tuple[str, List[str]]:
    """
    检测并修复未定义的Bool变量
    
    例如：代码中使用了 rock_is_animal 但没有定义
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    
    # 提取已定义的Bool变量
    defined_vars = set()
    # 匹配形如: variable_name = Bool("variable_name")
    bool_pattern = r'(\w+)\s*=\s*Bool\s*\(\s*["\'](\w+)["\']\s*\)'
    for match in re.finditer(bool_pattern, code):
        defined_vars.add(match.group(1))
    
    # 查找所有使用的变量
    # 在Implies、And、Or、Not等语句中使用的变量
    used_vars = set()
    
    # Python关键字（不能作为变量名）
    python_keywords = {
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
        'try', 'while', 'with', 'yield'
    }
    
    # Z3关键字和内置函数，不应被视为变量
    z3_keywords = {
        'Solver', 'Bool', 'Bools', 'Int', 'Ints', 'BoolSort', 'IntSort', 'EnumSort', 'Function',
        'Const', 'Consts', 'And', 'Or', 'Not', 'Implies', 'ForAll', 'Exists', 'Distinct',
        'If', 'sat', 'unsat', 'unknown', 'is_true', 'is_false', 'check', 'add',
        'push', 'pop', 'model', 'assertions', 'print', 'eval', 'as_long',
        'solver', 'x', 'y', 'z',  # 常见的量化变量名
        'b', 'birds', 'golfers', 'vehicles', 'fruits', 'books',  # 常见的循环变量名
        'i', 'j', 'k', 'v', 'f', 'g',  # 循环计数器
    }
    
    # 合并所有关键字
    all_keywords = python_keywords | z3_keywords
    
    # 在solver.add()、Implies()、And()、Or()、Not()等语句中查找变量
    # 匹配小写字母开头的标识符（可能是Bool变量）
    var_usage_pattern = r'\b([a-z][a-z0-9_]*)\b'
    
    # 只在特定上下文中查找：solver.add、Implies、And、Or、Not后面
    lines = code.split('\n')
    for line in lines:
        # 跳过注释
        if line.strip().startswith('#'):
            continue
        
        # 跳过for循环行（避免将循环变量误认为Bool变量）
        if 'for ' in line and ' in ' in line:
            continue
        
        # 只检查包含Z3约束的行
        if any(keyword in line for keyword in ['solver.add', 'Implies', 'And', 'Or', 'Not', 'ForAll']):
            # 提取该行中的变量
            for match in re.finditer(var_usage_pattern, line):
                var_name = match.group(1)
                # 排除Python关键字和Z3关键字
                if var_name not in all_keywords and not var_name.startswith('_'):
                    used_vars.add(var_name)
    
    # 查找未定义的变量
    undefined_vars = used_vars - defined_vars
    
    if undefined_vars:
        # 找到Bool变量定义的位置
        lines = code.split('\n')
        insert_position = None
        
        # 找到最后一个Bool变量定义的位置
        for i, line in enumerate(lines):
            if 'Bool(' in line and '=' in line and not line.strip().startswith('#'):
                insert_position = i + 1
        
        # 如果没有找到Bool定义，尝试在"# Define"注释后或第一个solver=Solver()之前
        if insert_position is None:
            for i, line in enumerate(lines):
                if 'solver = Solver()' in line or 'solver=Solver()' in line:
                    insert_position = i
                    break
                elif '# Define' in line or '# Create' in line:
                    insert_position = i + 1
        
        if insert_position is not None:
            # 生成新的变量定义
            new_definitions = []
            for var in sorted(undefined_vars):
                new_definitions.append(f'{var} = Bool("{var}")')
                repairs.append(f"自动添加未定义的Bool变量: {var}")
            
            # 在找到的位置插入
            for j, new_def in enumerate(new_definitions):
                lines.insert(insert_position + j, new_def)
            
            code = '\n'.join(lines)
    
    return code, repairs


def fix_undefined_predicates(code: str) -> Tuple[str, List[str]]:
    """
    检测并修复未定义的谓词（添加函数定义）
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    
    # 提取已定义的谓词函数
    defined_predicates = set()
    function_pattern = r"(\w+)\s*=\s*Function\s*\(\s*['\"](\w+)['\"]"
    for match in re.finditer(function_pattern, code):
        defined_predicates.add(match.group(1))
    
    # 查找所有使用的谓词（形如 PredicateName(entity) 的调用）
    # 但要排除Python内置函数和z3函数
    builtin_functions = {
        'print', 'len', 'str', 'int', 'bool', 'list', 'dict', 'set', 'tuple',
        'Solver', 'Bool', 'Bools', 'Int', 'Ints', 'BoolSort', 'IntSort', 'EnumSort', 'Function',
        'Const', 'Consts', 'And', 'Or', 'Not', 'Implies', 'ForAll', 'Exists', 'Distinct',
        'If', 'is_true', 'is_false', 'check', 'add', 'assertions', 'model', 'eval', 'as_long', 'range', 'sum'
    }
    
    used_predicates = set()
    # 匹配类似 Predicate(x) 或 Predicate(Entity) 的调用
    usage_pattern = r'\b([A-Z][a-zA-Z]*)\s*\('
    for match in re.finditer(usage_pattern, code):
        pred_name = match.group(1)
        if pred_name not in builtin_functions:
            used_predicates.add(pred_name)
    
    # 查找未定义的谓词
    undefined = used_predicates - defined_predicates
    
    if undefined:
        repairs.append(f"检测到未定义的谓词: {', '.join(undefined)}")
        
        # 尝试在适当位置插入谓词定义
        # 找到最后一个Function定义的位置
        lines = code.split('\n')
        insert_position = None
        last_predicate_line = None
        
        for i, line in enumerate(lines):
            if 'Function(' in line and '=' in line and not line.strip().startswith('#'):
                last_predicate_line = i
        
        if last_predicate_line is not None:
            insert_position = last_predicate_line + 1
        
        if insert_position is not None:
            # 查找Entity类型名称
            entity_match = re.search(r"Entity,\s*\([^)]+\)\s*=\s*EnumSort\s*\(\s*['\"](\w+)['\"]", code)
            entity_type = 'Entity' if entity_match else 'Entity'
            
            # 判断谓词的参数数量（单元谓词还是二元谓词）
            # 通过分析代码中的使用方式
            predicate_arities = {}
            for pred in undefined:
                # 查找该谓词的调用，看有几个参数
                # 例如：Eats(x, y) 是二元的，Cold(x) 是一元的
                pattern = rf'{pred}\s*\(([^)]+)\)'
                max_arity = 1  # 默认一元
                for match in re.finditer(pattern, code):
                    args = match.group(1)
                    # 简单计数逗号数量+1
                    arity = args.count(',') + 1
                    if arity > max_arity:
                        max_arity = arity
                predicate_arities[pred] = max_arity
            
            # 生成新的谓词定义
            new_definitions = []
            for pred in sorted(undefined):
                arity = predicate_arities.get(pred, 1)
                if arity == 1:
                    new_definitions.append(f"{pred} = Function('{pred}', {entity_type}, BoolSort())")
                elif arity == 2:
                    new_definitions.append(f"{pred} = Function('{pred}', {entity_type}, {entity_type}, BoolSort())")
                else:
                    # 三元及以上，按需扩展
                    entity_args = ', '.join([entity_type] * arity)
                    new_definitions.append(f"{pred} = Function('{pred}', {entity_args}, BoolSort())")
                repairs.append(f"添加谓词定义: {pred} (参数数量: {arity})")
            
            # 在找到的位置插入
            for j, new_def in enumerate(new_definitions):
                lines.insert(insert_position + j, new_def)
            
            code = '\n'.join(lines)
    
    return code, repairs


def fix_common_syntax_issues(code: str) -> Tuple[str, List[str]]:
    """
    修复其他常见的Z3语法问题
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    fixed_lines = []
    
    for line_num, line in enumerate(lines):
        original_line = line
        
        # 跳过注释和空行
        if line.strip().startswith('#') or not line.strip():
            fixed_lines.append(line)
            continue
        
        # 修复And/Or/Implies中缺少逗号的问题
        # 检测模式: And(A(x) B(x)) 应该是 And(A(x), B(x))
        if any(keyword in line for keyword in ['And(', 'Or(', 'Implies(']):
            # 使用正则表达式检测缺少逗号的模式
            # 匹配: FunctionName(arg) FunctionName(arg) （中间没有逗号）
            missing_comma_pattern = r'(\w+\([^)]*\))\s+(\w+\()'
            
            # 在And、Or、Implies的参数中查找
            fixed_line = line
            iteration = 0
            max_iterations = 10  # 防止无限循环
            
            while iteration < max_iterations:
                new_line = re.sub(
                    missing_comma_pattern,
                    r'\1, \2',
                    fixed_line
                )
                if new_line == fixed_line:
                    break  # 没有更多替换
                fixed_line = new_line
                iteration += 1
            
            if fixed_line != line:
                line = fixed_line
                repairs.append(f"第{line_num+1}行: 添加缺失的逗号")
        
        # 修复Implies只有一个参数的情况
        # 例如：Implies(And(Young(x), Not(White(x))), Rough(x))
        # 错误：Implies(And(Young(x), Not(White(x)), Rough(x))) - Rough(x)被包含在And中
        if 'Implies(' in line:
            # 检查Implies是否只有一个参数（缺少逗号分隔条件和结论）
            # 模式：Implies(And(...), something) 或 Implies(something, ...) 
            # 寻找不正确的模式：Implies(And(a, b, c))，其中c应该是第二个参数
            implies_pattern = r'Implies\s*\(\s*And\s*\(([^)]+(?:\([^)]*\))*)\)\s*,\s*(\w+\([^)]*\))\s*\)'
            
            # 检查括号是否匹配
            # 如果Implies内部的And有多余的参数，可能是缺少逗号
            implies_match = re.search(r'Implies\s*\((.*)\)', line)
            if implies_match:
                content = implies_match.group(1)
                # 计算逗号数量（顶层的，不在括号内的）
                depth = 0
                comma_count = 0
                for char in content:
                    if char == '(':
                        depth += 1
                    elif char == ')':
                        depth -= 1
                    elif char == ',' and depth == 0:
                        comma_count += 1
                
                # Implies需要恰好一个顶层逗号（两个参数）
                if comma_count == 0:
                    # 没有逗号，尝试修复
                    # 尝试找到And(...)的结束位置，在其后添加逗号并将剩余部分作为第二个参数
                    and_match = re.search(r'Implies\s*\(\s*And\s*\(', line)
                    if and_match:
                        # 找到And的结束位置
                        start_pos = and_match.end()
                        depth = 1
                        pos = start_pos
                        and_end = -1
                        while pos < len(line) and depth > 0:
                            if line[pos] == '(':
                                depth += 1
                            elif line[pos] == ')':
                                depth -= 1
                                if depth == 0:
                                    and_end = pos
                            pos += 1
                        
                        if and_end > 0:
                            # 检查And后面是否还有内容（应该作为第二个参数）
                            after_and = line[and_end+1:].strip()
                            # 移除Implies的结束括号
                            if after_and.startswith(','):
                                # 已经有逗号，没问题
                                pass
                            elif after_and.startswith(')'):
                                # 只有结束括号，说明缺少第二个参数
                                # 这种情况可能是And包含了过多参数
                                # 尝试将And的最后一个参数移出来作为Implies的第二个参数
                                and_content = line[start_pos:and_end]
                                # 找到最后一个逗号（顶层）
                                depth = 0
                                last_comma = -1
                                for i in range(len(and_content)-1, -1, -1):
                                    if and_content[i] == ')':
                                        depth += 1
                                    elif and_content[i] == '(':
                                        depth -= 1
                                    elif and_content[i] == ',' and depth == 0:
                                        last_comma = i
                                        break
                                
                                if last_comma > 0:
                                    # 找到了最后一个逗号
                                    before_comma = and_content[:last_comma]
                                    after_comma = and_content[last_comma+1:].strip()
                                    # 重构：Implies(And(before_comma), after_comma)
                                    new_implies = f"Implies(And({before_comma}), {after_comma})"
                                    # 替换整个Implies
                                    line = line[:and_match.start()] + new_implies + line[line.find(')', and_end+1)+1:]
                                    repairs.append(f"第{line_num+1}行: 修复 Implies 缺少第二个参数（从And中提取）")
        
        # 1. 修复 And/Or 只有一个参数的情况
        # And(single_arg) -> single_arg
        single_and_pattern = r'\bAnd\s*\(\s*([^,()]+(?:\([^()]*\))?)\s*\)'
        matches = list(re.finditer(single_and_pattern, line))
        for match in reversed(matches):  # 从后往前替换避免位置偏移
            # 检查是否真的只有一个参数（没有逗号）
            inner = match.group(1)
            if ',' not in inner and inner.count('(') == inner.count(')'):
                line = line[:match.start()] + inner + line[match.end():]
                repairs.append(f"第{line_num+1}行: 简化 And({inner}) 为 {inner}")
        
        # 2. 修复空的 And() 或 Or()
        if 'And()' in line:
            line = line.replace('And()', 'True')
            repairs.append(f"第{line_num+1}行: 替换 And() 为 True")
        if 'Or()' in line:
            line = line.replace('Or()', 'False')
            repairs.append(f"第{line_num+1}行: 替换 Or() 为 False")
        
        # 3. 修复多余的逗号（如 And(a, b,) ）
        line = re.sub(r',\s*\)', ')', line)
        
        # 4. 修复 ForAll 后缺少方括号的情况
        # ForAll(x, ...) -> ForAll([x], ...)
        forall_fix_pattern = r'ForAll\s*\(\s*([a-z_]\w*)\s*,'
        if re.search(forall_fix_pattern, line):
            line = re.sub(forall_fix_pattern, r'ForAll([\1],', line)
            repairs.append(f"第{line_num+1}行: 修复 ForAll 的变量格式（添加方括号）")
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), repairs


def fix_python_logical_operators(code: str) -> Tuple[str, List[str]]:
    """
    修复Python逻辑运算符为Z3函数
    
    将 "expr1 or expr2" 转换为 "Or(expr1, expr2)"
    将 "expr1 and expr2" 转换为 "And(expr1, expr2)"
    
    注意：只在solver.add()等Z3上下文中修复
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    fixed_lines = []
    
    for line_num, line in enumerate(lines):
        original_line = line
        
        # 跳过注释
        if line.strip().startswith('#'):
            fixed_lines.append(line)
            continue
        
        # 修复solver.add中的or
        if 'solver.add' in line and ' or ' in line:
            match = re.search(r'solver\.add\((.*)\)', line, re.DOTALL)
            if match:
                arg = match.group(1)
                if ' or ' in arg:
                    # 分割or两边的表达式（考虑括号平衡）
                    parts = []
                    current = []
                    depth = 0
                    tokens = arg.split()
                    
                    for token in tokens:
                        if token == 'or' and depth == 0:
                            parts.append(' '.join(current))
                            current = []
                        else:
                            current.append(token)
                            depth += token.count('(') - token.count(')')
                    
                    if current:
                        parts.append(' '.join(current))
                    
                    if len(parts) == 2:
                        new_arg = f"Or({parts[0]}, {parts[1]})"
                        line = line.replace(arg, new_arg)
                        repairs.append(f"第{line_num+1}行: 将 Python 'or' 转换为 Z3 'Or()'")
        
        # 修复solver.add中的and (类似逻辑)
        if 'solver.add' in line and ' and ' in line and line != original_line:
            # 避免重复修复，只在未修改时处理
            pass
        elif 'solver.add' in line and ' and ' in line:
            match = re.search(r'solver\.add\((.*)\)', line, re.DOTALL)
            if match:
                arg = match.group(1)
                if ' and ' in arg:
                    # 检查是否是Python的and而不是已经在函数调用中
                    parts = []
                    current = []
                    depth = 0
                    tokens = arg.split()
                    
                    for token in tokens:
                        if token == 'and' and depth == 0:
                            parts.append(' '.join(current))
                            current = []
                        else:
                            current.append(token)
                            depth += token.count('(') - token.count(')')
                    
                    if current:
                        parts.append(' '.join(current))
                    
                    if len(parts) == 2:
                        new_arg = f"And({parts[0]}, {parts[1]})"
                        line = line.replace(arg, new_arg)
                        repairs.append(f"第{line_num+1}行: 将 Python 'and' 转换为 Z3 'And()'")
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), repairs


def fix_undefined_quantifier_variables(code: str) -> Tuple[str, List[str]]:
    """
    检测并修复ForAll/Exists中使用但未定义的量化变量
    
    例如：代码中使用了 ForAll([x], ...) 但没有定义 x = Const('x', Entity)
    
    注意：如果代码中没有定义Entity类型，会注释掉使用ForAll的行
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    
    # 查找已定义的量化变量
    defined_vars = set()
    # 匹配形如: x = Const('x', Entity) 或 x = Const('x', SomeType)
    const_pattern = r'^([a-z])\s*=\s*Const\s*\(\s*["\']([a-z])["\']\s*,'
    for line in lines:
        match = re.match(const_pattern, line.strip())
        if match:
            defined_vars.add(match.group(1))
    
    # 查找ForAll/Exists中使用的变量
    used_vars = set()
    # 匹配 ForAll([x], ...) 或 ForAll([x, y], ...) 或 Exists([x], ...)
    forall_pattern = r'(?:ForAll|Exists)\s*\(\s*\[([^\]]+)\]'
    for line in lines:
        matches = re.finditer(forall_pattern, line)
        for match in matches:
            vars_str = match.group(1)
            # 分割变量名（可能有多个）
            for var in vars_str.split(','):
                var = var.strip()
                if var and var.isidentifier():
                    used_vars.add(var)
    
    # 找出未定义的变量
    undefined_vars = used_vars - defined_vars
    
    if undefined_vars:
        # 检查是否定义了Entity类型
        has_entity_def = False
        entity_type = 'Entity'
        
        for line in lines:
            if 'EnumSort' in line and '=' in line:
                has_entity_def = True
                # 提取Entity类型名
                match = re.search(r'(\w+)\s*,\s*\([^)]+\)\s*=\s*EnumSort', line)
                if match:
                    entity_type = match.group(1)
                break
        
        if not has_entity_def:
            # 没有Entity定义，无法添加Const变量
            # 需要注释掉所有使用ForAll/Exists的行
            repairs.append(f"警告：代码使用了ForAll/Exists但缺少Entity定义，将注释掉相关行")
            
            fixed_lines = []
            for i, line in enumerate(lines):
                if re.search(forall_pattern, line) and not line.strip().startswith('#'):
                    fixed_lines.append('# ERROR_NO_ENTITY: ' + line.lstrip() + '  # 缺少Entity定义，无法使用ForAll/Exists')
                    repairs.append(f"第{i+1}行: 注释掉ForAll/Exists（缺少Entity定义）")
                else:
                    fixed_lines.append(line)
            
            return '\n'.join(fixed_lines), repairs
        
        # 有Entity定义，可以添加变量
        insert_position = None
        
        # 查找solver = Solver()的位置，在它之前插入
        for i, line in enumerate(lines):
            if 'solver = Solver()' in line or 'solver=Solver()' in line:
                insert_position = i
                break
        
        if insert_position is not None:
            # 在solver定义前插入变量定义（添加空行）
            new_definitions = []
            # 先添加注释
            new_definitions.append('')
            new_definitions.append('# Quantifier variables')
            for var in sorted(undefined_vars):
                new_definitions.append(f"{var} = Const('{var}', {entity_type})")
                repairs.append(f"自动添加未定义的量化变量: {var} = Const('{var}', {entity_type})")
            
            # 在找到的位置之前插入
            for j, new_def in enumerate(new_definitions):
                lines.insert(insert_position + j, new_def)
            
            code = '\n'.join(lines)
    
    return code, repairs


def fix_forall_in_facts(code: str) -> Tuple[str, List[str]]:
    """
    修复ForAll语句错误地放在Facts部分（在x定义之前）的问题
    
    将这些ForAll语句移动到Rules部分（在x定义之后）
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    
    # 找到关键位置
    facts_start = None
    rules_start = None
    x_definition = None
    
    for i, line in enumerate(lines):
        if '# 3. Facts' in line:
            facts_start = i
        elif '# 4. Rules' in line:
            rules_start = i
        elif re.match(r'^\s*x\s*=\s*Const\s*\(', line.strip()):
            x_definition = i
    
    # 如果找到了Facts和Rules部分
    if facts_start is not None and rules_start is not None:
        # 收集Facts部分中的ForAll语句
        forall_statements = []
        lines_to_remove = []
        
        for i in range(facts_start + 1, rules_start):
            line = lines[i]
            if 'ForAll(' in line or 'Exists(' in line:
                forall_statements.append(line)
                lines_to_remove.append(i)
                repairs.append(f"第{i+1}行: 检测到Facts部分中的ForAll语句，将移动到Rules部分")
        
        # 如果有ForAll语句需要移动
        if forall_statements:
            # 删除这些行（从后往前删除避免索引问题）
            for i in reversed(lines_to_remove):
                del lines[i]
            
            # 重新找到Rules部分的位置（因为删除了行）
            rules_start = None
            for i, line in enumerate(lines):
                if '# 4. Rules' in line:
                    rules_start = i
                    break
            
            if rules_start is not None:
                # 找到x定义的位置（应该在Rules部分之后）
                insert_position = rules_start + 1
                for i in range(rules_start + 1, len(lines)):
                    if 'Const(' in lines[i] and '=' in lines[i]:
                        insert_position = i + 1
                        break
                
                # 在x定义之后插入ForAll语句
                for j, statement in enumerate(forall_statements):
                    lines.insert(insert_position + j, statement)
                
                code = '\n'.join(lines)
    
    return code, repairs


def fix_z3_type_errors(code: str) -> Tuple[str, List[str]]:
    """
    修复Z3类型错误，特别是"Z3 expression expected"
    
    常见错误：
    1. 使用Python的True/False而不是Z3的Bool常量
    2. 在Z3表达式中混用Python类型
    3. 在solver.add()中使用Python布尔值
    4. Entity被错误定义为Function（最常见）
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    
    # 首先，找出所有在EnumSort中定义的实体名
    entity_names = set()
    enum_pattern = r'EnumSort\s*\(\s*["\'](\w+)["\']\s*,\s*\[([^\]]+)\]'
    for line in lines:
        match = re.search(enum_pattern, line)
        if match:
            entities_str = match.group(2)
            # 提取所有实体名
            for entity in re.findall(r'["\'](\w+)["\']', entities_str):
                entity_names.add(entity)
    
    # 检查是否有实体名被错误地定义为Function
    fixed_lines = []
    for line_num, line in enumerate(lines):
        original_line = line
        
        # 跳过注释和空行
        if line.strip().startswith('#') or not line.strip():
            fixed_lines.append(line)
            continue
        
        # 检测Entity被定义为Function的错误
        if 'Function(' in line and '=' in line:
            match = re.search(r'(\w+)\s*=\s*Function\s*\(\s*["\'](\w+)["\']\s*,', line)
            if match:
                var_name = match.group(1)
                func_name = match.group(2)
                
                # 如果这个名字在entity_names中，这是一个错误
                if var_name in entity_names:
                    # 注释掉这行
                    line = '# ' + line.lstrip() + f'  # ERROR: {var_name} is an Entity, not a Function!'
                    repairs.append(f"第{line_num+1}行: 注释掉错误的函数定义 - {var_name} 是Entity，不应该是Function")
        
        # 修复solver.add(True) 或 solver.add(False)
        if 'solver.add(' in line:
            # 替换solver.add(True)为注释（True约束无意义）
            if re.search(r'solver\.add\s*\(\s*True\s*\)', line):
                line = '# ' + line.lstrip() + '  # Removed: solver.add(True) is redundant'
                repairs.append(f"第{line_num+1}行: 移除无意义的 solver.add(True)")
            
            # 替换solver.add(False)为注释（使求解器unsat）
            elif re.search(r'solver\.add\s*\(\s*False\s*\)', line):
                line = '# ' + line.lstrip() + '  # WARNING: solver.add(False) makes problem UNSAT'
                repairs.append(f"第{line_num+1}行: 注释掉 solver.add(False)")
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), repairs


def analyze_bracket_error(code: str, error_line: int) -> Optional[str]:
    """
    分析特定行的括号错误并给出修复建议
    
    Args:
        code: 原始代码
        error_line: 出错的行号
        
    Returns:
        修复建议字符串
    """
    lines = code.split('\n')
    
    if error_line < 1 or error_line > len(lines):
        return None
    
    target_line = lines[error_line - 1]
    
    # 分析该行的括号情况
    open_count = target_line.count('(')
    close_count = target_line.count(')')
    
    if open_count > close_count:
        return f"第 {error_line} 行缺少 {open_count - close_count} 个右括号 ')'"
    elif close_count > open_count:
        return f"第 {error_line} 行多出 {close_count - open_count} 个右括号 ')'"
    
    # 检查前面的行是否有未闭合的括号
    total_open = 0
    total_close = 0
    for i in range(error_line):
        total_open += lines[i].count('(')
        total_close += lines[i].count(')')
    
    if total_open > total_close:
        return f"在第 {error_line} 行之前累计缺少 {total_open - total_close} 个右括号"
    
    return None


def fix_undefined_function_calls(code: str) -> Tuple[str, List[str]]:
    """
    修复未定义但被调用的函数
    
    常见情况：
    - in_state("montana") 但 in_state 未定义
    - same_state(x, y) 但 same_state 未定义
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    
    # 查找已定义的函数和变量
    defined_items = set()
    
    # Bool变量
    for match in re.finditer(r'(\w+)\s*=\s*Bool\s*\(', code):
        defined_items.add(match.group(1))
    
    # Function定义
    for match in re.finditer(r'(\w+)\s*=\s*Function\s*\(', code):
        defined_items.add(match.group(1))
    
    # Const定义
    for match in re.finditer(r'(\w+)\s*=\s*Const\s*\(', code):
        defined_items.add(match.group(1))
    
    # 查找被调用的函数（形如 func_name(...) ）
    z3_builtins = {
        'Solver', 'Bool', 'Bools', 'Int', 'Ints', 'Function', 'Const', 'Consts', 'And', 'Or', 'Not', 
        'Implies', 'ForAll', 'Exists', 'Distinct', 'If', 'EnumSort', 'BoolSort',
        'IntSort', 'print', 'exit', 'unsat', 'sat', 'unknown', 'check', 'push', 'pop', 'add',
        'is_true', 'is_false', 'model', 'eval', 'as_long', 'range', 'len', 'sum'
    }
    
    called_functions = set()
    for line in lines:
        # 跳过注释和定义行
        if line.strip().startswith('#'):
            continue
        
        # 查找函数调用 func_name(...)
        for match in re.finditer(r'(\w+)\s*\(', line):
            func_name = match.group(1)
            if func_name not in z3_builtins and func_name not in defined_items:
                # 检查是否看起来像函数调用（不是关键字）
                if func_name not in ['if', 'elif', 'while', 'for', 'def', 'class']:
                    called_functions.add(func_name)
    
    # 分析未定义的函数调用
    undefined_functions = called_functions - defined_items
    
    if undefined_functions:
        repairs.append(f"检测到未定义的函数调用: {', '.join(sorted(undefined_functions))}")
        
        # 检查是否有Entity定义
        has_entity = 'EnumSort' in code
        
        if not has_entity:
            # 没有Entity，无法定义这些函数，需要注释掉调用
            repairs.append("警告：代码缺少Entity定义，无法定义函数，将注释掉相关调用")
            
            fixed_lines = []
            for i, line in enumerate(lines):
                if line.strip().startswith('#'):
                    fixed_lines.append(line)
                    continue
                
                # 检查是否调用了未定义的函数
                has_undefined_call = False
                for func in undefined_functions:
                    if re.search(rf'\b{func}\s*\(', line):
                        has_undefined_call = True
                        break
                
                if has_undefined_call:
                    fixed_lines.append('# ERROR_UNDEFINED_FUNC: ' + line.lstrip() + '  # 调用了未定义的函数')
                    repairs.append(f"第{i+1}行: 注释掉对未定义函数的调用")
                else:
                    fixed_lines.append(line)
            
            return '\n'.join(fixed_lines), repairs
    
    return code, repairs


def fix_function_signature_errors(code: str) -> Tuple[str, List[str]]:
    """
    修复Function定义的签名错误
    
    常见错误:
    - Function("lost_to", BoolSort(), BoolSort()) 应该是 Function("lost_to", Entity, Entity, BoolSort())
    - 参数类型应该是Entity或其他具体类型，而不是BoolSort
    
    这个函数会:
    1. 检测错误的Function定义（使用BoolSort作为参数）
    2. 注释掉这些定义
    3. 移除对这些函数的所有调用（因为它们无法正确定义）
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    fixed_lines = []
    
    # 检查是否定义了Entity类型
    has_entity = 'EnumSort' in code
    
    # 第一遍：找出所有有问题的Function定义
    problematic_functions = set()
    
    for line_num, line in enumerate(lines):
        if 'Function(' in line and '=' in line and not line.strip().startswith('#'):
            match = re.search(r'(\w+)\s*=\s*Function\s*\(\s*["\'](\w+)["\']\s*,\s*(.+)\)', line)
            if match:
                func_var = match.group(1)
                func_name = match.group(2)
                type_args = match.group(3)
                
                # 分割类型参数
                type_parts = []
                depth = 0
                current = []
                for char in type_args:
                    if char == '(':
                        depth += 1
                        current.append(char)
                    elif char == ')':
                        depth -= 1
                        current.append(char)
                    elif char == ',' and depth == 0:
                        type_parts.append(''.join(current).strip())
                        current = []
                    else:
                        current.append(char)
                
                if current:
                    type_parts.append(''.join(current).strip())
                
                # 检查是否有BoolSort()作为非返回类型参数（错误）
                if len(type_parts) >= 2:
                    has_bool_param = False
                    for i, part in enumerate(type_parts[:-1]):  # 除了最后一个（返回类型）
                        if 'BoolSort' in part:
                            has_bool_param = True
                            break
                    
                    if has_bool_param:
                        problematic_functions.add(func_var)
                        problematic_functions.add(func_name)
    
    # 第二遍：注释掉有问题的定义，并移除对它们的调用
    for line_num, line in enumerate(lines):
        original_line = line
        modified = False
        
        # 检查Function定义
        if 'Function(' in line and '=' in line and not line.strip().startswith('#'):
            match = re.search(r'(\w+)\s*=\s*Function\s*\(\s*["\'](\w+)["\']\s*,', line)
            if match:
                func_var = match.group(1)
                if func_var in problematic_functions:
                    line = '# ERROR_FUNCTION_SIGNATURE: ' + line.lstrip() + f'  # {func_var} 参数类型错误（无法修复，已移除）'
                    repairs.append(f"第{line_num+1}行: 注释掉错误的函数定义 {func_var}（BoolSort不应作为参数）")
                    modified = True
        
        # 检查是否调用了有问题的函数，如果是则注释掉整行
        if not modified and not line.strip().startswith('#'):
            for prob_func in problematic_functions:
                # 检查函数调用模式：prob_func(...)
                if re.search(rf'\b{prob_func}\s*\(', line):
                    # 这是一个对有问题函数的调用，需要注释掉
                    line = '# ERROR_REMOVED_CALL: ' + line.lstrip() + f'  # 调用了未定义的函数 {prob_func}'
                    repairs.append(f"第{line_num+1}行: 注释掉对错误函数 {prob_func} 的调用")
                    modified = True
                    break
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), repairs


def fix_orphaned_indented_lines(code: str) -> Tuple[str, List[str]]:
    """
    修复孤立的缩进行和多余的括号
    
    当某一行被注释掉后，如果它后面有缩进的延续行，这些行会变成孤立的缩进行
    导致IndentationError。同时，结束的括号也会变成多余的。
    
    例如:
        # solver.add(And(
            Implies(...),
            ...
        ))
    
    修复方法：注释掉这些孤立的缩进行和后续的单独括号行
    
    注意：只处理真正孤立的行，不处理合法的缩进块（如if/else/for等后的缩进）
    
    Args:
        code: 原始代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    fixed_lines = []
    
    # Python块开始关键字（这些后面的缩进行是合法的）
    block_keywords = ['if ', 'elif ', 'else:', 'for ', 'while ', 'def ', 'class ', 
                     'try:', 'except ', 'except:', 'finally:', 'with ']
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # 检查当前行是否是被注释掉的行（以 # ERROR、# ORPHANED 等开头）
        is_commented_error = line.strip().startswith(('# ERROR', '# ORPHANED', '# WARNING'))
        
        # 只在行是错误注释时才检查孤立行
        if is_commented_error and i + 1 < len(lines):
            # 检查这个注释行之前是否有合法的块结构
            # 向前查找最近的非空非注释行
            prev_line_idx = i - 1
            while prev_line_idx >= 0:
                prev_line = lines[prev_line_idx].strip()
                if prev_line and not prev_line.startswith('#'):
                    break
                prev_line_idx -= 1
            
            # 如果前一行是块开始（如 else:），则当前注释后的缩进行不是孤立的
            is_in_block = False
            if prev_line_idx >= 0:
                prev_line = lines[prev_line_idx].strip()
                for keyword in block_keywords:
                    if keyword in prev_line:
                        is_in_block = True
                        break
            
            # 如果在合法块中，不处理为孤立行
            if is_in_block:
                fixed_lines.append(line)
                i += 1
                continue
            
            # 检查下一行是否有缩进（可能是孤立的延续行）
            next_line = lines[i + 1]
            
            # 如果下一行有缩进但不是注释，可能是孤立行
            if next_line.startswith((' ', '\t')) and not next_line.strip().startswith('#') and next_line.strip():
                # 这是孤立的缩进行，找到所有连续的缩进行并注释掉
                fixed_lines.append(line)
                i += 1
                
                orphan_count = 0
                while i < len(lines):
                    current = lines[i]
                    stripped = current.strip()
                    
                    # 如果这行有缩进且不是注释
                    if current.startswith((' ', '\t')) and not stripped.startswith('#') and stripped:
                        # 注释掉这行
                        fixed_lines.append('# ORPHANED_LINE: ' + current.lstrip() + '  # 孤立的延续行')
                        orphan_count += 1
                        i += 1
                    elif not stripped:  # 空行
                        fixed_lines.append(current)
                        i += 1
                    else:
                        # 检查是否是单独的括号行（如 `)` 或 `))` 等）
                        if re.match(r'^[)\s]+$', stripped):
                            # 这是多余的括号行
                            fixed_lines.append('# ORPHANED_BRACKETS: ' + current.lstrip() + '  # 多余的括号')
                            repairs.append(f"第{i+1}行: 注释掉多余的括号")
                            i += 1
                            # 继续检查后续行
                            continue
                        else:
                            # 不再是相关的行，停止
                            break
                
                if orphan_count > 0:
                    repairs.append(f"注释掉 {orphan_count} 行孤立的延续行")
                continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines), repairs


def final_cleanup_orphaned_brackets(code: str) -> Tuple[str, List[str]]:
    """
    最终清理：移除孤立的括号行
    
    当多行被注释掉后，可能会留下单独的括号行（如 `))` 或 `)`）
    这些行会导致语法错误
    
    Args:
        code: 代码
        
    Returns:
        (修复后的代码, 修复记录)
    """
    repairs = []
    lines = code.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 如果这行只包含括号和空白
        if stripped and re.match(r'^[)\s]+$', stripped) and not line.strip().startswith('#'):
            # 注释掉这行
            fixed_lines.append('# ORPHANED_BRACKETS: ' + line.lstrip() + '  # 孤立的括号')
            repairs.append(f"第{i+1}行: 注释掉孤立的括号")
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines), repairs


def quick_bracket_fix(code: str) -> str:
    """
    快速修复括号不匹配（简单策略：确保每行的括号平衡）
    
    Args:
        code: 原始代码
        
    Returns:
        修复后的代码
    """
    lines = code.split('\n')
    fixed_lines = []
    
    # 跟踪累计的括号不平衡
    cumulative_imbalance = 0
    
    for line in lines:
        stripped = line.strip()
        
        # 跳过空行和纯注释行
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue
        
        # 计算当前行的括号
        line_open = line.count('(')
        line_close = line.count(')')
        line_imbalance = line_open - line_close
        
        # 如果是以 solver.add( 开头并且括号不平衡
        if ('solver.add(' in line or line.strip().startswith('solver.add(')) and line_imbalance > 0:
            # 检查行尾是否有注释
            comment_match = re.search(r'\s*#.*$', line)
            if comment_match:
                comment_start = comment_match.start()
                line = line[:comment_start].rstrip() + ')' * line_imbalance + '  ' + line[comment_start:].lstrip()
            else:
                line = line.rstrip() + ')' * line_imbalance
        else:
            cumulative_imbalance += line_imbalance
        
        fixed_lines.append(line)
    
    # 如果还有累计的不平衡，在最后添加括号
    result = '\n'.join(fixed_lines)
    if cumulative_imbalance > 0:
        result = result.rstrip() + ')' * cumulative_imbalance
    
    return result


# 测试函数
if __name__ == '__main__':
    # 测试代码示例（来自test6.json的真实错误代码）
    test_code = """from z3 import *

# 1. Domain - list ALL entities
Entity, (Bob, Erin, Gary, Harry) = EnumSort('Entity', ['Bob', 'Erin', 'Gary', 'Harry'])

# 2. Predicates - define ALL predicates BEFORE using them
Big = Function('Big', Entity, BoolSort())
Quiet = Function('Quiet', Entity, BoolSort())
White = Function('White', Entity, BoolSort())
Red = Function('Red', Entity, BoolSort())
Green = Function('Green', Entity, BoolSort())
Smart = Function('Smart', Entity, BoolSort())
Round = Function('Round', Entity, BoolSort())

solver = Solver()

# 3. Facts - NO ForAll here, just direct facts about entities
solver.add(Big(Bob))
solver.add(Quiet(Bob))
solver.add(White(Erin))
solver.add(Big(Gary))
solver.add(Red(Gary))
solver.add(Green(Harry))
solver.add(Smart(Harry))

# 4. Rules - MUST define x BEFORE ForAll
x = Const('x', Entity)
solver.add(ForAll([x], Implies(And(Smart(x), Big(x)), White(x))))
solver.add(ForAll([x], Implies(And(Quiet(x), Red(x)), Smart(x)))
solver.add(ForAll([x], Implies(And(Smart(x), White(x)), Green(x)))
solver.add(ForAll([x], Implies(And(Red(x), Round(x)), Quiet(x)))
solver.add(ForAll([x], Implies(Big(x), Round(x)))
solver.add(Implies(And(Round(Erin), Quiet(Erin)), Smart(Erin)))
solver.add(ForAll([x], Implies(And(Red(x), Green(x)), Big(x)))

# 5. Statement from question
S = Smart(Erin)

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
"""

    print("=" * 60)
    print("测试代码修复模块")
    print("=" * 60)
    
    print("\n原始代码括号分析:")
    print(f"  左括号: {test_code.count('(')}")
    print(f"  右括号: {test_code.count(')')}")
    print(f"  差值: {test_code.count('(') - test_code.count(')')}")
    print()
    
    repaired, repairs = repair_code(test_code)
    
    print("修复记录:")
    if repairs:
        for r in repairs:
            print(f"  - {r}")
    else:
        print("  (无修复)")
    print()
    
    print("修复后代码括号分析:")
    print(f"  左括号: {repaired.count('(')}")
    print(f"  右括号: {repaired.count(')')}")
    print(f"  差值: {repaired.count('(') - repaired.count(')')}")
    print()
    
    # 尝试执行修复后的代码
    print("=" * 60)
    print("尝试执行修复后的代码...")
    print("=" * 60)
    try:
        exec(repaired)
        print("\n✓ 代码执行成功!")
    except Exception as e:
        print(f"\n✗ 代码执行失败: {e}")

