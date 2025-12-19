"""
语义检查模块
"""
from typing import List,Dict
import re
from dataset_and_prompt import get_original_semantic_prompt


def generate_semantic_check_full_prompt(context:str,question:str,options_text:str,code_text:str)->List[Dict[str,str]]:
    # 生成用于语义检查的prompt
    instruction_prompt=get_original_semantic_prompt('instruction')
    user_prompt=get_original_semantic_prompt('user')

    user_prompt_values={
        'problem_text': context,
        'question_text': question,
        'options_text': options_text,
        'code_text': code_text,
    }
    real_user_prompt=user_prompt.format(**user_prompt_values)
    messages=[
        {
            'role': 'system',
            'content':instruction_prompt,
        },
        {
            'role': 'user',
            'content':real_user_prompt,
        },
    ]
    return messages

def semantic_check_response_analyze(response:str)->bool|None:
    match = re.search(r'(yes|no)\s*[^a-zA-Z]*$', response, re.IGNORECASE)
    if match:
        return match.group(1).lower()=='yes'
    else:
        return None
