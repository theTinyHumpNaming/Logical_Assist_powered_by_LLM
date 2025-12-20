"""
演示 repair.py 如何修复 test15.json 中的错误
"""
import sys
import json
sys.path.insert(0, '.')

from repair import repair_code

print("="*80)
print("test15.json 错误修复演示")
print("="*80)

# 加载error_codes目录中的所有错误代码
import os
error_files = [f for f in os.listdir('error_codes') if f.endswith('.py')]

print(f"\n找到 {len(error_files)} 个错误文件\n")

success_count = 0
for error_file in sorted(error_files):
    problem_id = error_file.replace('.py', '')
    
    print(f"\n{'='*80}")
    print(f"处理: {problem_id}")
    print('='*80)
    
    with open(f'error_codes/{error_file}', 'r', encoding='utf-8') as f:
        code = f.read()
        # 移除头部注释
        lines = code.split('\n')
        code_lines = []
        skip = True
        for line in lines:
            if skip and (line.startswith('# Problem:') or line.startswith('# Error:') or line.startswith('#====')):
                continue
            skip = False
            code_lines.append(line)
        code = '\n'.join(code_lines).strip()
    
    # 提取原始错误信息
    with open(f'error_codes/{error_file}', 'r', encoding='utf-8') as f:
        first_lines = f.readlines()[:3]
        error_msg = ""
        for line in first_lines:
            if line.startswith('# Error:'):
                error_msg = line.replace('# Error:', '').strip()
                break
    
    print(f"原始错误: {error_msg}")
    
    # 修复代码
    repaired, repairs = repair_code(code)
    
    print(f"\n修复操作数: {len(repairs)}")
    print("主要修复:")
    for repair in repairs[:5]:  # 只显示前5个
        print(f"  - {repair}")
    if len(repairs) > 5:
        print(f"  ... 还有 {len(repairs) - 5} 个修复")
    
    # 尝试执行
    print("\n测试执行... ", end='')
    try:
        exec(repaired)
        print("✓ 成功!")
        success_count += 1
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {str(e)[:50]}")

print("\n\n" + "="*80)
print("总结")
print("="*80)
print(f"总共处理: {len(error_files)} 个错误")
print(f"修复成功: {success_count} 个")
print(f"成功率: {success_count/len(error_files)*100:.1f}%")

if success_count == len(error_files):
    print("\n✓ 所有错误都已成功修复!")

