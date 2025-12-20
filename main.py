"""
主程序 - 逻辑推理题目评测系统

功能：
1. 输入API Key
2. 选择数据集路径
3. 选择模型
4. 运行评测，输出正确/错误的题目列表
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
import threading
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from request import LLMClient, query_llm_loop_messages, test_api_connection
from semantic_check import generate_semantic_check_full_prompt, semantic_check_response_analyze
from dataset_and_prompt import (detect_dataset_type, build_initial_messages_for_all_datasets, 
                                 build_next_messages_for_all_datasets, build_single_text_message_for_all_datasets,
                                 build_next_single_text_message_for_all_datasets, convert_messages_to_single_text_format)
from z3_execute import execute_z3_code


class LogicEvalApp:
    """逻辑推理评测应用"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("逻辑推理评测系统 - Logic Reasoning Evaluator")
        self.root.geometry("1200x900")  # 增大窗口尺寸以容纳更多日志
        self.root.configure(bg='#1e1e2e')
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 设置样式
        self.setup_styles()
        
        # 状态变量
        self.is_running = False
        self.stop_flag = False
        self.results = []

        # 时间跟踪
        self.start_time = None
        self.total_problems = 0

        # 日志控制变量
        self.log_level_var = tk.StringVar(value="INFO")
        self.auto_scroll_var = tk.BooleanVar(value=True)
        
        # 文件日志
        self.log_file = None
        self.setup_file_logging()
        
        # 加载 API keys
        self.api_keys = self.load_api_keys()
        
        # 创建界面
        self.create_widgets()
        
        # 设置默认 API key
        self.update_api_key_for_model()
    
    def setup_file_logging(self):
        """设置文件日志"""
        try:
            # 创建 logs 目录
            logs_dir = os.path.join(os.path.dirname(__file__), 'logs')
            if not os.path.exists(logs_dir):
                os.makedirs(logs_dir)
            
            # 创建日志文件名（包含时间戳）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_filename = os.path.join(logs_dir, f'eval_{timestamp}.log')
            
            # 打开日志文件
            self.log_file = open(log_filename, 'a', encoding='utf-8')
            self.log_file.write(f"=== 评测日志开始于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
            self.log_file.flush()
            
            # 记录日志文件路径
            print(f"日志文件: {log_filename}")
            
        except Exception as e:
            print(f"设置文件日志失败: {e}")
            self.log_file = None
    
    def load_api_keys(self):
        """从 keys 文件加载 API keys"""
        keys = {'openai': '', 'deepseek': ''}
        keys_file = os.path.join(os.path.dirname(__file__), 'keys')
        
        try:
            if os.path.exists(keys_file):
                with open(keys_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    lines = [l.strip() for l in content.split('\n') if l.strip()]
                    
                    current_provider = None
                    for line in lines:
                        if line.upper() == 'DS':
                            current_provider = 'deepseek'
                        elif line.upper() == 'GPT':
                            current_provider = 'openai'
                        elif line.startswith('sk-') and current_provider:
                            keys[current_provider] = line
        except Exception as e:
            self.log(f"加载 keys 文件失败: {e}", 'error')
        
        return keys
    
    def update_api_key_for_model(self):
        """根据当前选择的模型更新 API key"""
        model = self.model_var.get()
        provider = LLMClient.get_model_provider(model)
        
        if provider == 'deepseek' and self.api_keys.get('deepseek'):
            self.api_key_var.set(self.api_keys['deepseek'])
        elif provider == 'openai' and self.api_keys.get('openai'):
            self.api_key_var.set(self.api_keys['openai'])
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 颜色方案 - Catppuccin Mocha 风格
        self.colors = {
            'bg': '#1e1e2e',
            'surface': '#313244',
            'overlay': '#45475a',
            'text': '#cdd6f4',
            'subtext': '#a6adc8',
            'blue': '#89b4fa',
            'green': '#a6e3a1',
            'red': '#f38ba8',
            'yellow': '#f9e2af',
            'mauve': '#cba6f7',
            'teal': '#94e2d5',
        }
        
        # 配置样式
        style.configure('TFrame', background=self.colors['bg'])
        style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'], 
                       font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), padding=8)
        style.configure('TEntry', font=('Consolas', 10), padding=5)
        style.configure('TCombobox', font=('Segoe UI', 10), padding=5)
        
        # 标题样式
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), 
                       foreground=self.colors['mauve'])
        style.configure('Subtitle.TLabel', font=('Segoe UI', 11), 
                       foreground=self.colors['subtext'])
        
        # 按钮样式
        style.configure('Accent.TButton', background=self.colors['blue'], 
                       foreground=self.colors['bg'])
        style.map('Accent.TButton',
                 background=[('active', self.colors['mauve']), ('pressed', self.colors['teal'])])
        
    def create_widgets(self):
        """创建界面组件"""
        # 主容器 - 使用grid布局以更好地控制空间分配
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 配置grid布局权重 - 左右分栏布局
        main_frame.grid_rowconfigure(0, weight=0)  # 标题区域固定高度
        main_frame.grid_rowconfigure(1, weight=1)  # 左侧配置区域可扩展
        main_frame.grid_rowconfigure(2, weight=1)  # 右侧日志区域可扩展
        main_frame.grid_columnconfigure(0, weight=1)  # 左侧列
        main_frame.grid_columnconfigure(1, weight=2)  # 右侧列（日志区域更宽）
        
        # 标题 - 跨越两列
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 20))

        ttk.Label(title_frame, text="🧠 逻辑推理评测系统",
                 style='Title.TLabel').pack(side=tk.LEFT)
        ttk.Label(title_frame, text="Logic Reasoning Evaluator with LLM + Z3",
                 style='Subtitle.TLabel').pack(side=tk.LEFT, padx=(15, 0), pady=(5, 0))

        # 左侧配置区域
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=1, column=0, sticky='nsew', padx=(0, 10))

        # 配置区域
        config_frame = ttk.LabelFrame(left_frame, text=" ⚙️ 配置 ", padding="15")
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # API Key
        api_frame = ttk.Frame(config_frame)
        api_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(api_frame, text="API Key:", width=12).pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key_var, 
                                       show="*", width=50)
        self.api_key_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(api_frame, text="显示", variable=self.show_key_var,
                       command=self.toggle_key_visibility).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(api_frame, text="测试连接", 
                  command=self.test_connection).pack(side=tk.LEFT)
        
        # 自定义API地址
        api_base_frame = ttk.Frame(config_frame)
        api_base_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(api_base_frame, text="API地址:", width=12).pack(side=tk.LEFT)
        self.api_base_var = tk.StringVar()
        ttk.Entry(api_base_frame, textvariable=self.api_base_var, 
                 width=50).pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        ttk.Label(api_base_frame, text="(可选，留空使用默认)", 
                 foreground=self.colors['subtext']).pack(side=tk.LEFT)
        
        # 模型选择
        model_frame = ttk.Frame(config_frame)
        model_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(model_frame, text="模型:", width=12).pack(side=tk.LEFT)
        self.model_var = tk.StringVar(value='gpt-3.5-turbo')
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var, 
                                   values=LLMClient.get_supported_models(),
                                   state='readonly', width=25)
        model_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(model_frame, text="提供商: ", 
                 foreground=self.colors['subtext']).pack(side=tk.LEFT)
        self.provider_label = ttk.Label(model_frame, text="openai", 
                                        foreground=self.colors['teal'])
        self.provider_label.pack(side=tk.LEFT)
        model_combo.bind('<<ComboboxSelected>>', self.on_model_change)
        
        # 数据集选择
        dataset_frame = ttk.Frame(config_frame)
        dataset_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(dataset_frame, text="数据集:", width=12).pack(side=tk.LEFT)
        self.dataset_var = tk.StringVar()
        self.dataset_entry = ttk.Entry(dataset_frame, textvariable=self.dataset_var, width=50)
        self.dataset_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)

        ttk.Button(dataset_frame, text="浏览...",
                  command=self.browse_dataset).pack(side=tk.LEFT)

        # 模式选择
        mode_frame = ttk.Frame(config_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(mode_frame, text="调用模式:", width=12).pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value="direct")  # 默认选择直接生成模式
        mode_combo = ttk.Combobox(mode_frame, textvariable=self.mode_var,
                                  values=['direct', 'single_text'],
                                  state='readonly', width=20)
        mode_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(mode_frame, text="(多轮消息调用模式)",
                  foreground=self.colors['subtext'], font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=(0, 20))

        # 语义检查选项
        semantic_check_frame = ttk.Frame(config_frame)
        semantic_check_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(semantic_check_frame, text="语义检查:", width=12).pack(side=tk.LEFT)
        self.semantic_check_var = tk.BooleanVar(value=False)  # 默认关闭
        ttk.Checkbutton(semantic_check_frame, text="启用语义检查功能",
                       variable=self.semantic_check_var,
                       command=self.on_semantic_check_toggle).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(semantic_check_frame, text="(验证推理过程的语义正确性)",
                 foreground=self.colors['subtext']).pack(side=tk.LEFT)

        # 代码修复选项
        refinement_code_frame = ttk.Frame(config_frame)
        refinement_code_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(refinement_code_frame, text="代码修复:", width=12).pack(side=tk.LEFT)
        self.refinement_code_var = tk.BooleanVar(value=True)  # 默认开启
        ttk.Checkbutton(refinement_code_frame, text="启用代码修复功能",
                       variable=self.refinement_code_var,
                       command=self.on_refinement_code_toggle).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(refinement_code_frame, text="(代码执行失败时自动修复重试)",
                 foreground=self.colors['subtext']).pack(side=tk.LEFT)
        
        
        # 题目数量限制
        limit_frame = ttk.Frame(config_frame)
        limit_frame.pack(fill=tk.X)
        
        ttk.Label(limit_frame, text="题目限制:", width=12).pack(side=tk.LEFT)
        self.limit_var = tk.StringVar(value="0")
        ttk.Entry(limit_frame, textvariable=self.limit_var, width=10).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(limit_frame, text="(0表示不限制)",
                 foreground=self.colors['subtext']).pack(side=tk.LEFT)

        # Workers数量设置
        workers_frame = ttk.Frame(config_frame)
        workers_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(workers_frame, text="Workers数量:", width=12).pack(side=tk.LEFT)
        self.workers_var = tk.StringVar(value="4")
        ttk.Entry(workers_frame, textvariable=self.workers_var, width=10).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(workers_frame, text="(并行处理的工作线程数)",
                 foreground=self.colors['subtext']).pack(side=tk.LEFT)


        # 控制按钮
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_btn = ttk.Button(control_frame, text="▶ 开始评测", 
                                    command=self.start_evaluation, style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ 停止", 
                                   command=self.stop_evaluation, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="📋 导出结果", 
                  command=self.export_results).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(control_frame, text="🗑 清空日志", 
                  command=self.clear_log).pack(side=tk.LEFT)
        
        # 右侧区域 - 进度、统计和日志
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=1, column=1, sticky='nsew')

        # 进度条和统计信息区域
        top_right_frame = ttk.Frame(right_frame)
        top_right_frame.pack(fill=tk.X, pady=(0, 15))

        # 进度条
        progress_frame = ttk.Frame(top_right_frame)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, length=400)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.progress_label = ttk.Label(progress_frame, text="0/0 (0%)")
        self.progress_label.pack(side=tk.LEFT)

        # 时间估计
        self.time_label = ttk.Label(progress_frame, text="", foreground=self.colors['blue'])
        self.time_label.pack(side=tk.RIGHT, padx=(10, 0))

        # 统计信息
        stats_frame = ttk.LabelFrame(top_right_frame, text=" 📊 统计 ", padding="10")
        stats_frame.pack(fill=tk.X)

        stats_inner = ttk.Frame(stats_frame)
        stats_inner.pack(fill=tk.X)

        self.stats_labels = {}
        stats_items = [
            ('total', '总题数', self.colors['text']),
            ('correct', '正确', self.colors['green']),
            ('wrong', '错误', self.colors['red']),
            ('error', '异常', self.colors['yellow']),
            ('accuracy', '准确率', self.colors['mauve']),
        ]

        for key, name, color in stats_items:
            frame = ttk.Frame(stats_inner)
            frame.pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(frame, text=f"{name}:", foreground=self.colors['subtext']).pack(side=tk.LEFT)
            self.stats_labels[key] = ttk.Label(frame, text="0", foreground=color,
                                               font=('Segoe UI', 12, 'bold'))
            self.stats_labels[key].pack(side=tk.LEFT, padx=(5, 0))

        # 日志区域
        log_frame = ttk.LabelFrame(right_frame, text=" 📝 运行日志 ", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            font=('Consolas', 9),
            bg=self.colors['surface'],
            fg=self.colors['text'],
            insertbackground=self.colors['text'],
            selectbackground=self.colors['overlay'],
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置日志标签颜色
        self.log_text.tag_configure('info', foreground=self.colors['blue'])
        self.log_text.tag_configure('success', foreground=self.colors['green'])
        self.log_text.tag_configure('error', foreground=self.colors['red'])
        self.log_text.tag_configure('warning', foreground=self.colors['yellow'])
        self.log_text.tag_configure('highlight', foreground=self.colors['mauve'])
        
    def toggle_key_visibility(self):
        """切换API Key显示/隐藏"""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
            
    def on_model_change(self, event=None):
        """模型选择变化时更新提供商显示和 API key"""
        model = self.model_var.get()
        provider = LLMClient.get_model_provider(model)
        self.provider_label.config(text=provider)

        # 自动切换对应的 API key
        self.update_api_key_for_model()

    def on_semantic_check_toggle(self):
        """语义检查选项切换时的处理"""
        # 实现语义检查功能的开关逻辑
        enabled = self.semantic_check_var.get()
        if enabled:
            self.log("语义检查功能已启用", 'info')
        else:
            self.log("语义检查功能已关闭", 'info')

    def on_refinement_code_toggle(self):
        """代码修复选项切换时的处理"""
        enabled = self.refinement_code_var.get()
        if enabled:
            self.log("代码修复功能已启用", 'info')
        else:
            self.log("代码修复功能已关闭", 'info')
        
    def browse_dataset(self):
        """浏览选择数据集文件"""
        filename = filedialog.askopenfilename(
            title="选择数据集文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.join(os.path.dirname(__file__), 'data')
        )
        if filename:
            self.dataset_var.set(filename)
            
            
    def test_connection(self):
        """测试API连接"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请先输入API Key")
            return
            
        model = self.model_var.get()
        api_base = self.api_base_var.get().strip() or None
        
        self.log("正在测试API连接...", 'info')
        
        def test():
            result = test_api_connection(api_key, model, api_base)
            self.root.after(0, lambda: self._show_test_result(result))
            
        threading.Thread(target=test, daemon=True).start()
        
    def _show_test_result(self, result):
        """显示连接测试结果"""
        if result['success']:
            self.log(f"✓ {result['message']}", 'success')
            messagebox.showinfo("成功", result['message'])
        else:
            self.log(f"✗ {result['message']}", 'error')
            messagebox.showerror("失败", result['message'])
            
    def log(self, message: str, tag: str = None, level: str = "INFO"):
        """添加日志"""
        # 检查日志级别
        log_levels = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        current_level = self.log_level_var.get()
        if log_levels.get(level.upper(), 1) < log_levels.get(current_level, 1):
            return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        # 输出到GUI
        self.log_text.insert(tk.END, f"[{timestamp}] ", 'info')
        self.log_text.insert(tk.END, f"{message}\n", tag)
        
        # 输出到文件
        if self.log_file:
            try:
                self.log_file.write(log_entry + "\n")
                self.log_file.flush()
            except Exception as e:
                print(f"写入日志文件失败: {e}")
        
        # 自动滚动到底部
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
        
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        
    def save_log_to_file(self):
        """保存日志到文件"""
        filename = filedialog.asksaveasfilename(
            title="保存日志文件",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                log_content = self.log_text.get(1.0, tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log(f"日志已保存到: {filename}", 'success')
                messagebox.showinfo("成功", f"日志已保存到:\n{filename}")
            except Exception as e:
                self.log(f"保存日志失败: {str(e)}", 'error')
                messagebox.showerror("错误", f"保存日志失败:\n{str(e)}")
                
    def copy_log_to_clipboard(self):
        """复制日志到剪贴板"""
        try:
            log_content = self.log_text.get(1.0, tk.END)
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            self.log("日志已复制到剪贴板", 'success')
            messagebox.showinfo("成功", "日志已复制到剪贴板")
        except Exception as e:
            self.log(f"复制日志失败: {str(e)}", 'error')
            messagebox.showerror("错误", f"复制日志失败:\n{str(e)}")
        
    def update_stats(self, total=0, correct=0, wrong=0, error=0):
        """更新统计信息"""
        self.stats_labels['total'].config(text=str(total))
        self.stats_labels['correct'].config(text=str(correct))
        self.stats_labels['wrong'].config(text=str(wrong))
        self.stats_labels['error'].config(text=str(error))
        
        accuracy = (correct / total * 100) if total > 0 else 0
        self.stats_labels['accuracy'].config(text=f"{accuracy:.1f}%")
        
    def update_progress(self, current, total):
        """更新进度条"""
        if total > 0:
            percentage = current / total * 100
            self.progress_var.set(percentage)
            self.progress_label.config(text=f"{current}/{total} ({percentage:.1f}%)")

            # 更新时间估计
            self._update_time_estimate(current, total)

    def _update_time_estimate(self, current, total):
        """更新时间估计"""
        if self.start_time is None or current == 0:
            self.time_label.config(text="")
            return

        import time
        elapsed_time = time.time() - self.start_time

        if current < total:
            # 计算预计总时间和剩余时间
            avg_time_per_problem = elapsed_time / current
            remaining_problems = total - current
            estimated_remaining = avg_time_per_problem * remaining_problems

            # 格式化时间显示
            if estimated_remaining < 60:
                time_str = f"剩余 {estimated_remaining:.0f}秒"
            elif estimated_remaining < 3600:
                minutes = int(estimated_remaining // 60)
                seconds = int(estimated_remaining % 60)
                time_str = f"剩余 {minutes}分 {seconds}秒"
            else:
                hours = int(estimated_remaining // 3600)
                minutes = int((estimated_remaining % 3600) // 60)
                time_str = f"剩余 {hours}时 {minutes}分"
        else:
            # 已完成，显示总用时
            if elapsed_time < 60:
                time_str = f"总用时 {elapsed_time:.1f}秒"
            elif elapsed_time < 3600:
                minutes = int(elapsed_time // 60)
                seconds = int(elapsed_time % 60)
                time_str = f"总用时 {minutes}分 {seconds}秒"
            else:
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                time_str = f"总用时 {hours}时 {minutes}分"

        self.time_label.config(text=time_str)
        
    def start_evaluation(self):
        """开始评测"""
        # 验证输入
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请输入API Key")
            return
            
        dataset_path = self.dataset_var.get().strip()
        if not dataset_path:
            messagebox.showwarning("警告", "请选择数据集文件")
            return
            
        if not os.path.exists(dataset_path):
            messagebox.showerror("错误", "数据集文件不存在")
            return

        # 验证workers数量
        try:
            num_workers = int(self.workers_var.get())
            if num_workers <= 0:
                raise ValueError()
        except ValueError:
            messagebox.showwarning("警告", "Workers数量必须是大于0的整数")
            return

        # 更新UI状态
        self.is_running = True
        self.stop_flag = False
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.results = []

        # 设置时间跟踪
        import time
        self.start_time = time.time()

        # 在后台线程运行评测
        threading.Thread(target=self._run_evaluation, args=(api_key, dataset_path),
                        daemon=True).start()
        
    def stop_evaluation(self):
        """停止评测"""
        self.stop_flag = True
        self.log("正在停止评测，终止所有任务...", 'warning')
        self.stop_btn.config(state=tk.DISABLED)  # 防止重复点击

    def _get_question_context(self, problem)->tuple[str,str,str]:
        """获取问题的详细信息"""
        context = problem.get('context', '')
        question = problem.get('question', '')
        options = problem.get('options', [])
        options_text = "\n".join(options) if isinstance(options, list) else str(options)

        return context, question, options_text

    def _extract_python_code_from_response(self, response_text: str) -> str|None:
        """从LLM响应中提取Python代码块"""
        match = re.search(r'```python\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        else:
            return None

    def _process_single_problem(self, problem, index, api_key, model, api_base):
        """处理单个题目（供并行调用）"""
        # 检查停止标志
        if self.stop_flag:
            return {
                'id': problem.get('id', f'Problem_{index+1}'),
                'predicted': None,
                'correct': problem.get('answer', '').strip().upper(),
                'is_correct': False,
                'error': '用户停止',
                'cancelled': True,
                'attempts': 0
            }
        
        problem_id = problem.get('id', f'Problem_{index+1}')
        correct_answer = problem.get('answer', '').strip().upper()
        mode = self.mode_var.get()

        semantic_check_enabled = self.semantic_check_var.get()
        refinement_code_enabled = self.refinement_code_var.get()

        # 直接生成模式只支持direct模式
        dataset_type = detect_dataset_type(problem)
        
        self.root.after(0, lambda pid=problem_id:
                       self.log(f"[Worker] 开始处理: {pid} (mode={mode}, semantic_check={semantic_check_enabled}, refinement_code={refinement_code_enabled})", 'info'))
        
        # 在try块外初始化code变量，以便在异常时也能保存
        code = None
        
        try:
            max_attempts = 10  # 在great Refinement module下总共允许调用10次LLM，多轮调用
            attempt = 0

            # 初次生成对话 - 根据模式选择不同的消息构建方式
            if mode == "single_text":
                messages = build_single_text_message_for_all_datasets(dataset_type, *self._get_question_context(problem))
                accumulated_context = messages[0]['content']
                extra_type_is_semantic = None
                extra_info = ''
                llm_output = ''
            else:  # direct mode
                messages = build_initial_messages_for_all_datasets(dataset_type, *self._get_question_context(problem))
                extra_type_is_semantic = None
                extra_info = ''
                llm_output = ''
            
            while attempt < max_attempts:
                # 每次循环开始时检查停止标志
                if self.stop_flag:
                    raise Exception('用户停止')
                
                attempt += 1
                if attempt >= max_attempts:
                    self.root.after(0, lambda pid=problem_id:
                        self.log(f"  [{pid}] great Refinement module修复次数达到上限{max_attempts}次", 'error'))
                    raise Exception('great Refinement module修复次数达到上限{max_attempts}次')
                elif attempt > 1:
                    self.root.after(0, lambda pid=problem_id, a=attempt: 
                                   self.log(f"  [{pid}] 第{a}次尝试重新生成...", 'warning'))
                    # 生成后续对话 - 根据模式选择不同的消息构建方式
                    if mode == "single_text":
                        messages = build_next_single_text_message_for_all_datasets(
                            dataset_type,
                            *self._get_question_context(problem),
                            extra_type_is_semantic,
                            extra_info,
                            llm_output,
                            accumulated_context
                        )
                    else:  # direct mode
                        next_message = build_next_messages_for_all_datasets(dataset_type, *self._get_question_context(problem),
                                                                          extra_type_is_semantic, extra_info, llm_output)
                        messages.extend(next_message)
                
                # 调用前检查停止标志
                if self.stop_flag:
                    raise Exception('用户停止')
                
                # 获取Z3代码
                response = query_llm_loop_messages(api_key, messages, model, api_base,
                                    max_tokens=2000, temperature=0)
                
                # 调用后检查停止标志
                if self.stop_flag:
                    raise Exception('用户停止')
                
                if not response['success']:
                    raise Exception(response.get('error', 'API请求失败'))
                llm_output = response['content']

                code = self._extract_python_code_from_response(llm_output)

                if code is None:
                    extract_info=("Unable to extract Python code correctly from the content you provided. "
                    "Did you really give the script in standard format:\n"
                    "```python\n"
                    "#todo\n"
                    "```\n")
                    self.root.after(0, lambda pid=problem_id:
                            self.log(f"  [{pid}] 提取python代码失败", 'warning'))
                    
                    # 如果代码修复功能关闭，直接返回错误
                    if not refinement_code_enabled:
                        raise Exception("提取Python代码失败（代码修复功能已关闭）")
                    
                    extra_type_is_semantic = False
                    continue

                # semantic check module
                if semantic_check_enabled:
                    # 调用前检查停止标志
                    if self.stop_flag:
                        raise Exception('用户停止')
                    
                    semantic_messages=generate_semantic_check_full_prompt(*self._get_question_context(problem),code)
                    semantic_response=query_llm_loop_messages(api_key, semantic_messages, model, api_base,
                                                              max_tokens=2000, temperature=0)
                    
                    # 调用后检查停止标志
                    if self.stop_flag:
                        raise Exception('用户停止')
                    
                    if not response['success']:
                        raise Exception(response.get('error', 'API请求失败'))
                    semantic_output = semantic_response['content']

                    semantic_check_result=semantic_check_response_analyze(semantic_output)
                    if semantic_check_result is None: # todo
                        print(semantic_output)
                        self.root.after(0, lambda pid=problem_id:
                            self.log(f"  [{pid}] semantic check module给出错误回答", 'error'))
                    elif semantic_check_result is False:
                        self.root.after(0, lambda pid=problem_id:
                            self.log(f"  [{pid}] semantic check module检查得到语义错误", 'warning'))
                        
                        # 如果代码修复功能关闭，直接返回错误
                        if not refinement_code_enabled:
                            raise Exception("语义检查失败（代码修复功能已关闭）")
                        
                        extra_info=semantic_check_result
                        extra_type_is_semantic=True
                        continue

                # 执行代码前检查停止标志
                if self.stop_flag:
                    raise Exception('用户停止')
                
                # 每次执行前都使用repair修复代码
                result, exec_error, repair_log = execute_z3_code(code)
                
                # 记录修复日志
                if repair_log:
                    self.root.after(0, lambda pid=problem_id, logs=repair_log: 
                                   self.log(f"  [{pid}] 代码自动修复: {'; '.join(logs)}", 'debug'))
                
                # self refine
                if exec_error:
                    self.root.after(0, lambda pid=problem_id, e=exec_error: 
                                   self.log(f"  [{pid}] code执行错误（repair修复后）: {e}", 'warning'))
                    
                    # 如果代码修复功能关闭，直接抛出错误
                    if not refinement_code_enabled:
                        raise Exception(f"代码执行错误（repair修复后仍失败）: {exec_error}")
                    
                    # 如果达到最大尝试次数，抛出错误
                    if attempt >= max_attempts - 1:
                        raise Exception(f"代码执行错误（repair修复 + LLM修复{max_attempts}次后仍失败）: {exec_error}")
                    
                    # 继续LLM refine循环
                    extra_info=exec_error
                    extra_type_is_semantic=False
                    continue
                
                # 成功执行结束
                predicted = result.upper() if result else None
                is_correct = predicted == correct_answer

                result_info = {
                    'id': problem_id,
                    'predicted': predicted,
                    'correct': correct_answer,
                    'is_correct': is_correct,
                    'pseudocode': None,
                    'mode': mode,
                    'error': exec_error,
                    'attempts': attempt,
                    # 'messages': messages, # 包含所有轮对话的内容（不包含最后一轮模型输出），但大小较大
                }
                if mode == "direct":
                    result_info['code'] = code

                return result_info

        except Exception as e:
            error_msg = str(e)
            is_cancelled = error_msg == '用户停止'
            return {
                'id': problem_id,
                'predicted': None,
                'correct': correct_answer,
                'is_correct': False,
                'error': error_msg,
                'cancelled': is_cancelled,
                'attempts': attempt if 'attempt' in locals() else 1,
                'code': code  # 保存生成的代码（即使执行出错）
            }
    
    def _run_evaluation(self, api_key: str, dataset_path: str):
        """运行评测（后台线程，4个workers并行处理）"""
        try:
            # 加载数据集
            self.root.after(0, lambda: self.log(f"正在加载数据集: {dataset_path}", 'info'))
            
            with open(dataset_path, 'r', encoding='utf-8') as f:
                problems = json.load(f)
            
            # 应用题目限制
            try:
                limit = int(self.limit_var.get())
                if limit > 0:
                    problems = problems[:limit]
            except:
                pass
            
            total = len(problems)

            # 获取并验证workers数量
            try:
                num_workers = int(self.workers_var.get())
                if num_workers <= 0:
                    raise ValueError("Workers数量必须大于0")
            except ValueError:
                num_workers = 4  # 默认值
                self.root.after(0, lambda: self.log("Workers数量无效，使用默认值4", 'warning'))

            self.root.after(0, lambda: self.log(f"共 {total} 道题目，使用 {num_workers} 个 workers 并行处理", 'info'))
            self.root.after(0, lambda: self.update_progress(0, total))

            model = self.model_var.get()
            api_base = self.api_base_var.get().strip() or None

            correct_count = 0
            wrong_count = 0
            error_count = 0
            completed_count = 0

            # 使用线程锁保护计数器
            lock = threading.Lock()

            # 使用配置的 workers 数量并行处理
            executor = ThreadPoolExecutor(max_workers=num_workers)
            try:
                # 提交所有任务
                future_to_problem = {}
                for i, problem in enumerate(problems):
                    if self.stop_flag:
                        break
                    future = executor.submit(
                        self._process_single_problem, 
                        problem, i, api_key, model, api_base
                    )
                    future_to_problem[future] = (i, problem)
                
                # 处理完成的任务
                for future in as_completed(future_to_problem):
                    if self.stop_flag:
                        # 立即取消所有未完成的任务
                        for f in future_to_problem:
                            f.cancel()
                        self.root.after(0, lambda: self.log("正在终止所有任务...", 'warning'))
                        break
                    
                    try:
                        result_info = future.result(timeout=0.1)
                    except Exception:
                        # 任务被取消或超时
                        continue
                    
                    # 跳过被取消的任务
                    if result_info.get('cancelled'):
                        self.root.after(0, lambda pid=result_info['id']: 
                                       self.log(f"  [{pid}] 已取消", 'warning'))
                        continue
                    
                    problem_id = result_info['id']
                    predicted = result_info['predicted']
                    correct_answer = result_info['correct']
                    is_correct = result_info['is_correct']
                    has_error = result_info.get('error') and not result_info['predicted']

                    # 为结果添加原题信息
                    i, original_problem = future_to_problem[future]
                    result_info.update({
                        'context': original_problem.get('context'),
                        'question': original_problem.get('question'),
                        'options': original_problem.get('options')
                    })

                    with lock:
                        self.results.append(result_info)
                        completed_count += 1
                        
                        if has_error:
                            error_count += 1
                            self.root.after(0, lambda pid=problem_id, e=result_info.get('error'): 
                                           self.log(f"  [{pid}] ⚠ 异常: {e}", 'error'))
                        elif is_correct:
                            correct_count += 1
                            self.root.after(0, lambda pid=problem_id, p=predicted, c=correct_answer: 
                                           self.log(f"  [{pid}] ✓ 正确! 预测={p}, 答案={c}", 'success'))
                        else:
                            wrong_count += 1
                            self.root.after(0, lambda pid=problem_id, p=predicted, c=correct_answer: 
                                           self.log(f"  [{pid}] ✗ 错误! 预测={p}, 答案={c}", 'error'))
                        
                        # 更新进度
                        cc, wc, ec, cur = correct_count, wrong_count, error_count, completed_count
                        self.root.after(0, lambda c=cur, t=total, 
                                       cc=cc, wc=wc, ec=ec: 
                                       (self.update_progress(c, t), 
                                        self.update_stats(c, cc, wc, ec)))
            finally:
                # 立即关闭线程池，不等待任务完成
                executor.shutdown(wait=False, cancel_futures=True)
            
            # 完成
            was_stopped = self.stop_flag
            self.root.after(0, lambda: self._evaluation_complete(
                completed_count, correct_count, wrong_count, error_count, was_stopped))
            
        except Exception as e:
            self.root.after(0, lambda: self.log(f"评测出错: {str(e)}", 'error'))
            self.root.after(0, self._reset_ui)

    def _evaluation_complete(self, total, correct, wrong, error, was_stopped=False):
        """评测完成"""
        self.log("=" * 50, 'highlight')
        if was_stopped:
            self.log(f"评测已停止!", 'warning')
        else:
            self.log(f"评测完成!", 'highlight')
        self.log(f"已完成: {total}, 正确: {correct}, 错误: {wrong}, 异常: {error}", 'highlight')
        accuracy = (correct / total * 100) if total > 0 else 0
        self.log(f"准确率: {accuracy:.2f}%", 'highlight')
        self.log("=" * 50, 'highlight')
        
        self._reset_ui()
        
    def on_closing(self):
        """窗口关闭事件处理"""
        if self.is_running:
            if messagebox.askyesno("确认", "评测正在运行，确定要退出吗？"):
                self.stop_flag = True
                # 等待一小段时间让评测停止
                self.root.after(1000, self._close_log_file_and_exit)
            else:
                return
        else:
            self._close_log_file_and_exit()
    
    def _close_log_file_and_exit(self):
        """关闭日志文件并退出"""
        if self.log_file:
            try:
                self.log_file.write(f"=== 评测日志结束于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                self.log_file.close()
                self.log_file = None
            except Exception as e:
                print(f"关闭日志文件失败: {e}")
        
        self.root.destroy()
    
    def _reset_ui(self):
        """重置UI状态"""
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

        # 重置时间跟踪
        self.start_time = None
        self.total_problems = 0
        
    def export_results(self):
        """导出结果"""
        if not self.results:
            messagebox.showinfo("提示", "没有可导出的结果")
            return
            
        filename = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            # 统计信息
            total = len(self.results)
            correct = sum(1 for r in self.results if r.get('is_correct'))
            wrong = sum(1 for r in self.results if not r.get('is_correct') and not r.get('error'))
            error = sum(1 for r in self.results if r.get('error'))
            
            export_data = {
                'summary': {
                    'total': total,
                    'correct': correct,
                    'wrong': wrong,
                    'error': error,
                    'accuracy': correct / total * 100 if total > 0 else 0
                },
                'correct_problems': [r['id'] for r in self.results if r.get('is_correct')],
                'wrong_problems': [r['id'] for r in self.results if not r.get('is_correct')],
                'details': self.results
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
                
            self.log(f"结果已导出到: {filename}", 'success')
            messagebox.showinfo("成功", f"结果已导出到:\n{filename}")


def main():
    root = tk.Tk()
    app = LogicEvalApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

