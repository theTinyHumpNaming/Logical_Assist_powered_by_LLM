"""
翻译模块 - 将逻辑推理题目翻译为标准化格式（Canonical English）

目前支持的数据集：
- FOLIO

功能：
1. 使用LLM将原始数据集翻译为Canonical English格式
2. 保留原始JSON结构
3. 支持批量翻译
"""

import json
import os
from typing import Dict, Any, List, Optional
from request import query_llm_loop_messages


def load_translation_prompt(dataset_type: str) -> Optional[str]:
    """
    加载指定数据集的翻译提示词
    
    Args:
        dataset_type: 数据集类型（如 'folio'）
        
    Returns:
        翻译提示词文本，如果不存在则返回None
    """
    prompt_file = os.path.join(os.path.dirname(__file__), 
                               'all_prompt', dataset_type.lower(), 'translation.txt')
    
    if not os.path.exists(prompt_file):
        return None
    
    with open(prompt_file, 'r', encoding='utf-8') as f:
        return f.read().strip()


def build_translation_messages(dataset_type: str, problem: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    构建翻译请求的消息
    
    Args:
        dataset_type: 数据集类型
        problem: 原始题目数据
        
    Returns:
        消息列表
    """
    system_prompt = load_translation_prompt(dataset_type)
    
    if not system_prompt:
        raise ValueError(f"未找到数据集 {dataset_type} 的翻译提示词")
    
    # 构建用户消息 - 将题目转换为JSON字符串
    user_content = json.dumps(problem, ensure_ascii=False, indent=2)
    
    messages = [
        {
            'role': 'system',
            'content': system_prompt
        },
        {
            'role': 'user',
            'content': user_content
        }
    ]
    
    return messages


def translate_single_problem(api_key: str, dataset_type: str, problem: Dict[str, Any],
                            model: str = 'gpt-3.5-turbo', 
                            api_base: Optional[str] = None) -> Dict[str, Any]:
    """
    翻译单个题目
    
    Args:
        api_key: API密钥
        dataset_type: 数据集类型
        problem: 原始题目
        model: 模型名称
        api_base: 自定义API地址
        
    Returns:
        翻译结果字典，包含success, translated_problem, error等字段
    """
    try:
        # 构建消息
        messages = build_translation_messages(dataset_type, problem)
        
        # 调用LLM
        response = query_llm_loop_messages(
            api_key, 
            messages, 
            model, 
            api_base,
            max_tokens=2000, 
            temperature=0
        )
        
        if not response['success']:
            return {
                'success': False,
                'error': response.get('error', 'API请求失败'),
                'original_problem': problem
            }
        
        # 解析LLM返回的JSON
        llm_output = response['content'].strip()
        
        # 尝试从代码块中提取JSON
        if '```json' in llm_output:
            # 提取代码块中的内容
            import re
            match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL | re.IGNORECASE)
            if match:
                llm_output = match.group(1).strip()
        elif '```' in llm_output:
            # 处理没有json标记的代码块
            import re
            match = re.search(r'```\s*(.*?)\s*```', llm_output, re.DOTALL)
            if match:
                llm_output = match.group(1).strip()
        
        # 解析JSON
        try:
            translated_problem = json.loads(llm_output)
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'JSON解析失败: {str(e)}',
                'raw_output': llm_output,
                'original_problem': problem
            }
        
        # 验证翻译结果包含必要字段
        required_fields = ['id', 'context', 'question', 'options', 'answer']
        missing_fields = [f for f in required_fields if f not in translated_problem]
        
        if missing_fields:
            return {
                'success': False,
                'error': f'翻译结果缺少字段: {", ".join(missing_fields)}',
                'translated_problem': translated_problem,
                'original_problem': problem
            }
        
        return {
            'success': True,
            'translated_problem': translated_problem,
            'original_problem': problem
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'original_problem': problem
        }


def translate_dataset(api_key: str, dataset_type: str, problems: List[Dict[str, Any]],
                     model: str = 'gpt-3.5-turbo', api_base: Optional[str] = None,
                     progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """
    翻译整个数据集
    
    Args:
        api_key: API密钥
        dataset_type: 数据集类型
        problems: 题目列表
        model: 模型名称
        api_base: 自定义API地址
        progress_callback: 进度回调函数，接收 (current, total, result) 参数
        
    Returns:
        翻译结果字典，包含成功和失败的题目
    """
    total = len(problems)
    translated_problems = []
    failed_problems = []
    
    for i, problem in enumerate(problems):
        result = translate_single_problem(api_key, dataset_type, problem, model, api_base)
        
        if result['success']:
            translated_problems.append(result['translated_problem'])
        else:
            failed_problems.append({
                'index': i,
                'id': problem.get('id', f'Problem_{i+1}'),
                'error': result['error'],
                'original_problem': problem
            })
        
        # 调用进度回调
        if progress_callback:
            progress_callback(i + 1, total, result)
    
    return {
        'total': total,
        'success_count': len(translated_problems),
        'failed_count': len(failed_problems),
        'translated_problems': translated_problems,
        'failed_problems': failed_problems
    }


def save_translated_dataset(translated_problems: List[Dict[str, Any]], 
                           output_path: str) -> None:
    """
    保存翻译后的数据集
    
    Args:
        translated_problems: 翻译后的题目列表
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(translated_problems, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # 测试代码
    print("翻译模块已加载")
    print("支持的数据集: FOLIO")


