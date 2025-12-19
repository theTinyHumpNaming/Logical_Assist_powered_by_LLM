"""
Request 模块 - 使用 OpenAI 官方库发送 API 请求

支持模型：
- gpt-3.5-turbo (OpenAI)
- gpt-4 (OpenAI)
- gpt-4-turbo (OpenAI)
- gpt-4o (OpenAI)
- gpt-4o-mini (OpenAI)
- deepseek-chat (DeepSeek)
- deepseek-reasoner (DeepSeek)
"""

from openai import OpenAI
import time
from typing import Optional, Dict, Any, List


class LLMClient:
    """LLM API 客户端（基于 OpenAI 官方库）"""
    
    # 模型配置
    MODEL_CONFIGS = {
        'gpt-3.5-turbo': {
            'provider': 'openai',
            'api_base': 'https://api.openai.com/v1',
            'model_name': 'gpt-3.5-turbo'
        },
        'gpt-4': {
            'provider': 'openai',
            'api_base': 'https://api.openai.com/v1',
            'model_name': 'gpt-4'
        },
        'gpt-4-turbo': {
            'provider': 'openai',
            'api_base': 'https://api.openai.com/v1',
            'model_name': 'gpt-4-turbo'
        },
        'gpt-4o': {
            'provider': 'openai',
            'api_base': 'https://api.openai.com/v1',
            'model_name': 'gpt-4o'
        },
        'gpt-4o-mini': {
            'provider': 'openai',
            'api_base': 'https://api.openai.com/v1',
            'model_name': 'gpt-4o-mini'
        },
        'deepseek-chat': {
            'provider': 'deepseek',
            'api_base': 'https://api.deepseek.com',
            'model_name': 'deepseek-chat'
        },
        'deepseek-reasoner': {
            'provider': 'deepseek',
            'api_base': 'https://api.deepseek.com',
            'model_name': 'deepseek-reasoner'
        }
    }
    
    def __init__(self, api_key: str, model: str = 'gpt-3.5-turbo', 
                 custom_api_base: Optional[str] = None):
        """
        初始化LLM客户端
        
        Args:
            api_key: API密钥
            model: 模型名称
            custom_api_base: 自定义API地址（可选，用于代理）
        """
        self.api_key = api_key
        self.model = model
        self.custom_api_base = custom_api_base
        
        if model not in self.MODEL_CONFIGS:
            raise ValueError(f"不支持的模型: {model}. 支持的模型: {list(self.MODEL_CONFIGS.keys())}")
        
        self.config = self.MODEL_CONFIGS[model]
        
        # 初始化 OpenAI 客户端
        base_url = custom_api_base if custom_api_base else self.config['api_base']
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )

    def send_loop_messages(self, messages: List[Dict[str, Any]], max_tokens: int = 10000,
                           temperature: float = 0.0, timeout: int = 120,
                           max_retries: int = 5) -> Dict[str, Any]:
        """
        发送请求到LLM API

        Args:
            messages: list-like loop messages
            max_tokens: 最大token数
            temperature: 温度参数
            timeout: 超时时间（秒）
            max_retries: 最大重试次数

        Returns:
            包含响应内容和元数据的字典
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.config['model_name'],
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    timeout=timeout
                )

                content = response.choices[0].message.content

                return {
                    'success': True,
                    'content': content,
                    'model': self.model,
                    'usage': {
                        'prompt_tokens': response.usage.prompt_tokens if response.usage else 0,
                        'completion_tokens': response.usage.completion_tokens if response.usage else 0,
                        'total_tokens': response.usage.total_tokens if response.usage else 0
                    },
                    'raw_response': response
                }

            except Exception as e:
                error_str = str(e)

                # 处理特定错误
                if 'rate_limit' in error_str.lower() or '429' in error_str:
                    # 速率限制，等待后重试
                    wait_time = 2 ** attempt * 5
                    time.sleep(wait_time)
                    last_error = f"速率限制，等待 {wait_time}s 后重试"
                    continue

                elif 'authentication' in error_str.lower() or '401' in error_str:
                    return {
                        'success': False,
                        'error': 'API密钥无效或已过期',
                        'model': self.model
                    }

                elif 'timeout' in error_str.lower():
                    last_error = f"请求超时 ({timeout}s)"

                elif 'connection' in error_str.lower():
                    last_error = f"连接错误: {error_str}"

                else:
                    last_error = f"错误: {error_str}"

                # 重试前等待
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)

        return {
            'success': False,
            'error': f"请求失败 (重试{max_retries}次后): {last_error}",
            'model': self.model
        }

    
    @classmethod
    def get_supported_models(cls) -> list:
        """获取支持的模型列表"""
        return list(cls.MODEL_CONFIGS.keys())
    
    @classmethod
    def get_model_provider(cls, model: str) -> str:
        """获取模型的提供商"""
        if model in cls.MODEL_CONFIGS:
            return cls.MODEL_CONFIGS[model]['provider']
        return 'unknown'


def query_llm_loop_messages(api_key: str, messages: List[Dict[str, Any]], model: str = 'gpt-3.5-turbo',
              custom_api_base: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
        便捷函数：查询LLM

        Args:
            api_key: API密钥
            messages: 提示词
            model: 模型名称
            custom_api_base: 自定义API地址
            **kwargs: 其他参数传递给send_request

        Returns:
            响应字典
        """
    try:
        client = LLMClient(api_key, model, custom_api_base)
        return client.send_loop_messages(messages, **kwargs)
    except ValueError as e:
        return {
            'success': False,
            'error': str(e),
            'model': model
        }


def test_api_connection(api_key: str, model: str = 'gpt-3.5-turbo',
                        custom_api_base: Optional[str] = None) -> Dict[str, Any]:
    """
    测试API连接
    
    Args:
        api_key: API密钥
        model: 模型名称
        custom_api_base: 自定义API地址
        
    Returns:
        测试结果字典
    """
    try:
        client = LLMClient(api_key, model, custom_api_base)

        messages=[{
            'role': 'user',
            'content': "Reply with 'OK' only."
            }]
        result = client.send_loop_messages(messages,max_tokens=10,
            timeout=30,
            max_retries=1)
        
        if result['success']:
            return {
                'success': True,
                'message': f'连接成功！模型: {model}'
            }
        else:
            return {
                'success': False,
                'message': f'连接失败: {result.get("error", "未知错误")}'
            }
            
    except ValueError as e:
        return {
            'success': False,
            'message': str(e)
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'连接测试失败: {str(e)}'
        }


if __name__ == "__main__":
    # 测试代码
    print("支持的模型列表:")
    for model in LLMClient.get_supported_models():
        provider = LLMClient.get_model_provider(model)
        print(f"  - {model} ({provider})")
