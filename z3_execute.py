"""
z3运行模块

注意：Z3 Python API不是线程安全的，多线程并发执行会导致内部错误。
本模块使用全局互斥锁来保护所有Z3操作，确保任何时刻只有一个线程在执行Z3代码。
"""
import time
from typing import Optional, Tuple, List
import io
import sys
import threading
import uuid
import re

from repair import repair_code, quick_bracket_fix

# 全局互斥锁，用于保护Z3操作（Z3不是线程安全的）
_z3_lock = threading.Lock()


def execute_z3_code(code: str, timeout: int = 10, auto_repair: bool = True) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    执行Z3代码（线程安全版本）
    
    使用全局互斥锁保护Z3操作，确保任何时刻只有一个线程在执行Z3代码。
    这是为了解决Z3 Python API的并发执行bug。

    Args:
        code: Z3 Python代码
        timeout: 超时时间（秒）
        auto_repair: 是否自动修复常见语法错误

    Returns:
        (执行结果, 错误信息, 修复记录列表)
    """
    # 使用全局锁保护整个Z3操作
    # 这样可以防止多线程并发执行Z3时的竞态条件
    with _z3_lock:
        import z3
        old_stdout = sys.stdout
        result_holder = {'result': None, 'error': None}
        repair_log = []
        
        # 自动修复代码
        if auto_repair:
            code, repair_log = repair_code(code)
            if repair_log:
                # 如果有修复，再做一次快速括号修复确保完整性
                code = quick_bracket_fix(code)
        
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

        def run_code():
            old_stderr = sys.stderr
            stdout_capture = None
            stderr_capture = None
            
            try:
                # 捕获打印输出和错误输出
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                sys.stdout = stdout_capture
                sys.stderr = stderr_capture

                # 准备执行环境
                global_vars = {
                    '__builtins__': __builtins__,
                    'Solver': z3.Solver,
                    'Bool': z3.Bool,
                    'Bools': z3.Bools,
                    'Int': z3.Int,
                    'Ints': z3.Ints,
                    'BoolSort': z3.BoolSort,
                    'IntSort': z3.IntSort,
                    'EnumSort': z3.EnumSort,
                    'Function': z3.Function,
                    'Const': z3.Const,
                    'Consts': z3.Consts,
                    'And': z3.And,
                    'Or': z3.Or,
                    'Not': z3.Not,
                    'Implies': z3.Implies,
                    'ForAll': z3.ForAll,
                    'Exists': z3.Exists,
                    'Distinct': z3.Distinct,
                    'sat': z3.sat,
                    'unsat': z3.unsat,
                    'unknown': z3.unknown,
                    'is_true': z3.is_true,
                    'is_false': z3.is_false,
                }
                # 执行修改后的代码，只使用全局变量环境
                exec(modified_code, global_vars)

                # 获取输出（在还原stdout之前）
                output = stdout_capture.getvalue()
                stderr_output = stderr_capture.getvalue()

                # 检查 stderr 是否有 Z3 断言错误
                if stderr_output and ('ASSERTION' in stderr_output or 'VIOLATION' in stderr_output):
                    result_holder['error'] = f"Z3 assertion error (known Z3 bug, try simpler constraints)"
                    return

                # 从输出中提取结果
                result = output.strip().split('\n')[-1] if output.strip() else None
                if result and result != 'NONE':
                    result_holder['result'] = result
                    return

            except Exception as e:
                error_str = str(e)
                # 处理 Z3 特定错误
                z3_error_keywords = ['access violation', 'unreachable', 'assertion', 'unexpected', 'dec_ref', 'invalid']
                if any(x in error_str.lower() for x in z3_error_keywords):
                    # 对于某些Z3内部错误，尝试重试一次
                    # 这些错误有时是暂时的
                    if 'unreachable' in error_str.lower():
                        try:
                            # 短暂延迟后重试
                            time.sleep(0.1)
                            # 重新执行一次
                            exec(code, global_vars)
                            # 安全地获取输出
                            if stdout_capture and hasattr(stdout_capture, 'getvalue'):
                                output = stdout_capture.getvalue()
                                result = output.strip().split('\n')[-1] if output.strip() else None
                                if result and result != 'NONE':
                                    result_holder['result'] = result
                                    return
                        except:
                            pass
                    result_holder['error'] = f"Z3 internal error (known bug): {error_str[:100]}"
                else:
                    result_holder['error'] = error_str
            finally:
                sys.stderr = old_stderr

        try:
            # 在线程中执行以支持超时
            thread = threading.Thread(target=run_code)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout)

            if thread.is_alive():
                result_holder['error'] = "Z3 execution timeout"
                # 线程仍在运行，无法强制终止，但返回超时错误
        finally:
            sys.stdout = old_stdout

        return result_holder['result'], result_holder['error'], repair_log


def execute_z3_code_simple(code: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    执行Z3代码的简单版本（向后兼容，不返回修复记录）

    Args:
        code: Z3 Python代码
        timeout: 超时时间（秒）

    Returns:
        (执行结果, 错误信息)
    """
    result, error, _ = execute_z3_code(code, timeout, auto_repair=True)
    return result, error


def execute_z3_code_without_repair(code: str, timeout: int = 10) -> Tuple[Optional[str], Optional[str]]:
    """
    执行Z3代码但不使用repair自动修复
    
    Args:
        code: Z3 Python代码
        timeout: 超时时间（秒）
    
    Returns:
        (执行结果, 错误信息)
    """
    result, error, _ = execute_z3_code(code, timeout, auto_repair=False)
    return result, error
