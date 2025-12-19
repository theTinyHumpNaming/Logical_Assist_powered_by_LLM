"""
关于prompt的数据接口
"""
import os
from typing import List, Dict

def detect_dataset_type(problem)->str:
    """根据问题ID或内容检测数据集类型"""
    problem_id = problem.get('id', '').lower()

    if 'prontoqa' in problem_id:
        return 'prontoqa'
    elif 'folio' in problem_id:
        return 'folio'
    elif 'logical_deduction' in problem_id:
        return 'logical_deduction'
    elif 'ar_lsat' in problem_id or 'lsat' in problem_id:
        return 'ar_lsat'
    elif 'proofwriter' in problem_id:
        return 'proofwriter'
    else:
        # 根据选项数量和内容推断
        options = problem.get('options', [])
        if len(options) == 2:
            return 'prontoqa'
        elif len(options) == 3:
            question = problem.get('question', '').lower()
            if 'uncertain' in question:
                return 'folio'
            return 'proofwriter'
        else:
            context = problem.get('context', '').lower()
            if 'arranged' in context or 'order' in context or 'left' in context or 'right' in context:
                return 'logical_deduction'
            return 'ar_lsat'

def _simply_return_prompt(dataset:str,prompt_type:str)->str:
    # 获取prompt
    prompt_folder_names = {
        'prontoqa': 'prontoQA',
        'folio': 'folio',
        'logical_deduction': 'logicaldeduction',
        'ar_lsat': 'arlsat',
        'proofwriter': 'proofwriter',
    }
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_folder = os.path.join(current_dir, 'all_prompt', prompt_folder_names[dataset])

    assert prompt_type in ['instruction','user','refine_code','refine_semantic']
    prompt_path = os.path.join(prompt_folder, prompt_type+'.txt')

    with open(prompt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        return content

def build_initial_messages_for_all_datasets(dataset:str, context:str, question:str, options_text:str)->List[Dict[str,str]]:
    # 根据数据集返回初始的messages以开始和llm对话
    instruction_prompt = _simply_return_prompt(dataset,'instruction')
    user_prompt = _simply_return_prompt(dataset,'user')

    # 根据数据集类型提供正确的参数映射
    if dataset in ['folio', 'ar_lsat', 'proofwriter']:
        user_prompt_values={
            'context':context,
            'question':question,
            'options_text':options_text,
        }
    else:
        user_prompt_values={
            'problem_text':context,
            'question_text':question,
            'options_text':options_text,
        }
    real_user_prompt = user_prompt.format(**user_prompt_values)
    messages=[
        {
            'role': 'system',
            'content':instruction_prompt,
        },
        {
            'role': 'user',
            'content': real_user_prompt,
        }
    ]
    return messages

def build_next_messages_for_all_datasets(dataset:str, context:str, question:str, options_text:str,
                                         extra_type_is_semantic:bool, extra_info:str, llm_output:str)->List[Dict[str,str]]:
    user_prompt = _simply_return_prompt(dataset,'refine_semantic' if extra_type_is_semantic else 'refine_code')

    # 根据数据集类型提供正确的参数映射
    if dataset in ['folio', 'ar_lsat', 'proofwriter']:
        user_prompt_values={
            'info_text':extra_info,
            'context':context,
            'question':question,
            'options_text':options_text,
        }
    else:
        user_prompt_values={
            'info_text':extra_info,
            'problem_text':context,
            'question_text':question,
            'options_text':options_text,
        }
    real_user_prompt = user_prompt.format(**user_prompt_values)

    messages=[
        {
            'role': 'assistant',
            'content':llm_output,
        },
        {
            'role': 'user',
            'content': real_user_prompt,
        }
    ]
    return messages

def build_single_text_message_for_all_datasets(dataset:str, context:str, question:str, options_text:str)->List[Dict[str,str]]:
    """
    单文本模式：将instruction和user内容合并成一个大文本块
    作为单个user消息发送，不包含system prompt和assistant消息
    """
    instruction_prompt = _simply_return_prompt(dataset,'instruction')
    user_prompt = _simply_return_prompt(dataset,'user')

    # 根据数据集类型提供正确的参数映射
    if dataset in ['folio', 'ar_lsat', 'proofwriter']:
        user_prompt_values={
            'context':context,
            'question':question,
            'options_text':options_text,
        }
    else:
        user_prompt_values={
            'problem_text':context,
            'question_text':question,
            'options_text':options_text,
        }
    real_user_prompt = user_prompt.format(**user_prompt_values)
    
    # 合并instruction和user内容成一个大文本块
    combined_text = f"{instruction_prompt}\n\n========================================\n\n{real_user_prompt}"
    
    messages=[
        {
            'role': 'user',
            'content': combined_text,
        }
    ]
    return messages

def build_next_single_text_message_for_all_datasets(dataset:str, context:str, question:str, options_text:str,
                                                    extra_type_is_semantic:bool, extra_info:str, llm_output:str,
                                                    accumulated_context:str)->List[Dict[str,str]]:
    """
    单文本模式的后续调用（旧版）：将所有信息（包括之前的错误和修复建议）合并成一个大文本块
    保留用于向后兼容
    """
    user_prompt = _simply_return_prompt(dataset,'refine_semantic' if extra_type_is_semantic else 'refine_code')

    # 根据数据集类型提供正确的参数映射
    if dataset in ['folio', 'ar_lsat', 'proofwriter']:
        user_prompt_values={
            'info_text':extra_info,
            'context':context,
            'question':question,
            'options_text':options_text,
        }
    else:
        user_prompt_values={
            'info_text':extra_info,
            'problem_text':context,
            'question_text':question,
            'options_text':options_text,
        }
    real_user_prompt = user_prompt.format(**user_prompt_values)
    
    # 合并所有上下文成一个大文本块
    # 格式：[历史上下文] + [之前的LLM输出] + [修复提示]
    combined_text = f"{accumulated_context}\n\nPrevious attempt output:\n```python\n{llm_output}\n```\n\nFix instructions:\n{real_user_prompt}"
    
    messages=[
        {
            'role': 'user',
            'content': combined_text,
        }
    ]
    return messages

def convert_messages_to_single_text_format(messages:List[Dict[str,str]], dataset:str, context:str, question:str, options_text:str)->List[Dict[str,str]]:
    """
    将Direct Mode的完整消息列表转换为Single Text Mode的单个user消息
    这样可以包含所有历史信息（instruction + problem + 所有对话）
    
    Args:
        messages: Direct Mode的完整消息列表
        dataset: 数据集类型
        context: 原始context
        question: 原始question
        options_text: 原始options
    
    Returns:
        包含单个user消息的列表（包含所有历史）
    """
    instruction_prompt = _simply_return_prompt(dataset, 'instruction')
    
    # 根据数据集类型提供正确的参数映射
    if dataset in ['folio', 'ar_lsat', 'proofwriter']:
        user_prompt = _simply_return_prompt(dataset, 'user')
        user_prompt_values = {
            'context': context,
            'question': question,
            'options_text': options_text,
        }
    else:
        user_prompt = _simply_return_prompt(dataset, 'user')
        user_prompt_values = {
            'problem_text': context,
            'question_text': question,
            'options_text': options_text,
        }
    
    real_user_prompt = user_prompt.format(**user_prompt_values)
    
    # 构建合并后的文本
    combined_text = f"{instruction_prompt}\n\n========================================\n\n{real_user_prompt}"
    
    # 添加所有历史对话（跳过system消息，从user消息开始）
    for msg in messages:
        if msg['role'] == 'system':
            continue  # 已包含在instruction_prompt中
        elif msg['role'] == 'user' and msg['content'] == real_user_prompt:
            continue  # 跳过第一条user消息，因为已包含在开头
        else:
            # 添加assistant消息和后续user消息
            role_label = "Assistant" if msg['role'] == 'assistant' else "User"
            combined_text += f"\n\n--- {role_label} ---\n{msg['content']}"
    
    return [{
        'role': 'user',
        'content': combined_text
    }]

def get_original_semantic_prompt(prompt_type:str)->str:
    assert prompt_type in ['user','instruction']
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, 'all_prompt', 'semantic_check_'+prompt_type+'.txt')
    with open(prompt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        return content

