#!/usr/bin/env python3
"""
实时音频字幕翻译 - GUI 版本
使用 tkinter 显示浮动字幕窗口
"""

import os
import sys
import subprocess
import threading
import queue
import json
import time
from pathlib import Path

# 检查 tkinter
import tkinter as tk
from tkinter import ttk, scrolledtext

class TranslatorWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("实时字幕翻译")
        self.root.geometry("800x200")
        self.root.attributes('-topmost', True)  # 置顶
        
        # 设置透明度
        self.root.attributes('-alpha', 0.95)
        
        # 创建界面
        self.setup_ui()
        
        # 字幕队列
        self.subtitle_queue = queue.Queue()
        
        # 运行状态
        self.running = False
        
    def setup_ui(self):
        """设置界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置 grid 权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 源语言标签
        ttk.Label(main_frame, text="原文:", font=("Helvetica", 10)).grid(row=0, column=0, sticky=tk.W)
        
        # 原文显示区域
        self.original_text = tk.StringVar(value="等待音频输入...")
        original_label = ttk.Label(
            main_frame, 
            textvariable=self.original_text,
            font=("Helvetica", 14),
            wraplength=780,
            justify=tk.LEFT,
            foreground="#333333"
        )
        original_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 分隔线
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # 翻译标签
        ttk.Label(main_frame, text="翻译:", font=("Helvetica", 10)).grid(row=3, column=0, sticky=tk.W)
        
        # 翻译显示区域
        self.translated_text = tk.StringVar(value="")
        translated_label = ttk.Label(
            main_frame,
            textvariable=self.translated_text,
            font=("Helvetica", 16, "bold"),
            wraplength=780,
            justify=tk.LEFT,
            foreground="#0066cc"
        )
        translated_label.grid(row=4, column=0, sticky=(tk.W, tk.E))
        
        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 9))
        status_bar.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 绑定快捷键
        self.root.bind('<Command-q>', lambda e: self.quit())
        self.root.bind('<Escape>', lambda e: self.quit())
        
    def update_subtitle(self, original, translated):
        """更新字幕"""
        self.original_text.set(original)
        self.translated_text.set(translated)
        
    def set_status(self, status):
        """设置状态"""
        self.status_var.set(status)
        
    def quit(self):
        """退出"""
        self.running = False
        self.root.quit()
        
    def run(self):
        """运行主循环"""
        self.running = True
        self.root.mainloop()


def get_blackhole_device():
    """获取 BlackHole 设备索引"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
            capture_output=True,
            text=True
        )
        output = result.stderr
        
        # 查找 BlackHole 设备
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'BlackHole' in line:
                # 提取设备索引
                import re
                match = re.search(r'\[(\d+)\]', lines[i-1] if i > 0 else line)
                if match:
                    return match.group(1)
        return None
    except Exception as e:
        print(f"获取设备失败: {e}")
        return None


def transcribe_audio(audio_file, model_path, lang="auto"):
    """使用 whisper.cpp 转录音频"""
    try:
        cmd = [
            'whisper-cpp',
            '-m', model_path,
            '-f', audio_file,
            '-l', lang,
            '--no-timestamps',
            '-otxt'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # 提取最后一行作为转录结果
        lines = result.stdout.strip().split('\n')
        return lines[-1] if lines else ""
    except Exception as e:
        return ""


def translate_text(text, target_lang="zh"):
    """使用 translate-shell 翻译"""
    try:
        if not text or len(text.strip()) < 2:
            return ""
            
        cmd = ['trans', '-brief', '-no-warn', '-no-autocorrect', f':{target_lang}']
        result = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return ""


class AudioProcessor:
    def __init__(self, window, source_lang="auto", target_lang="zh", model="medium"):
        self.window = window
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.model = model
        self.model_path = None
        self.device_index = None
        self.running = False
        self.buffer_dir = Path("/tmp/audio_translator_gui")
        
    def setup(self):
        """初始化设置"""
        # 创建工作目录
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取 BlackHole 设备
        self.device_index = get_blackhole_device()
        if not self.device_index:
            raise Exception("未找到 BlackHole 设备，请先安装 blackhole-2ch")
        
        # 获取模型路径
        try:
            result = subprocess.run(
                ['whisper-cpp-model-path', self.model],
                capture_output=True,
                text=True
            )
            self.model_path = result.stdout.strip()
            
            if not Path(self.model_path).exists():
                print(f"下载模型: {self.model}")
                subprocess.run(['whisper-cpp-model-download', self.model], check=True)
                result = subprocess.run(
                    ['whisper-cpp-model-path', self.model],
                    capture_output=True,
                    text=True
                )
                self.model_path = result.stdout.strip()
        except Exception as e:
            raise Exception(f"无法获取 Whisper 模型: {e}")
        
    def start_capture(self):
        """开始捕获音频"""
        audio_dir = self.buffer_dir / "audio"
        audio_dir.mkdir(exist_ok=True)
        
        output_pattern = str(audio_dir / "segment_%03d.wav")
        
        cmd = [
            'ffmpeg',
            '-f', 'avfoundation',
            '-i', f':{self.device_index}',
            '-ar', '16000',
            '-ac', '1',
            '-c:a', 'pcm_s16le',
            '-f', 'segment',
            '-segment_time', '5',
            '-reset_timestamps', '1',
            output_pattern,
            '-y'
        ]
        
        self.ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
    def process_loop(self):
        """处理循环"""
        processed = set()
        audio_dir = self.buffer_dir / "audio"
        
        while self.running:
            # 查找新音频文件
            for audio_file in sorted(audio_dir.glob("segment_*.wav")):
                if audio_file in processed:
                    continue
                
                # 检查文件是否已写完
                try:
                    stat = audio_file.stat()
                    file_age = time.time() - stat.st_mtime
                    
                    if file_age >= 5:  # 等待5秒确保写完
                        processed.add(audio_file)
                        
                        # 转录
                        self.window.set_status(f"正在识别: {audio_file.name}...")
                        transcript = transcribe_audio(
                            str(audio_file),
                            self.model_path,
                            self.source_lang
                        )
                        
                        if transcript and len(transcript) > 2:
                            # 翻译
                            self.window.set_status("正在翻译...")
                            translation = translate_text(transcript, self.target_lang)
                            
                            # 更新显示
                            self.window.update_subtitle(transcript, translation)
                            self.window.set_status(f"完成: {audio_file.name}")
                        
                        # 删除已处理的文件
                        audio_file.unlink()
                        
                except Exception as e:
                    print(f"处理文件出错: {e}")
            
            time.sleep(0.5)
    
    def start(self):
        """启动处理器"""
        self.setup()
        self.running = True
        
        # 启动音频捕获
        self.start_capture()
        time.sleep(2)  # 等待 ffmpeg 启动
        
        # 在后台线程中运行处理循环
        self.processor_thread = threading.Thread(target=self.process_loop)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
    def stop(self):
        """停止处理器"""
        self.running = False
        
        if hasattr(self, 'ffmpeg_process'):
            self.ffmpeg_process.terminate()
            self.ffmpeg_process.wait()
        
        if hasattr(self, 'processor_thread'):
            self.processor_thread.join(timeout=2)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='实时音频字幕翻译 (GUI版)')
    parser.add_argument('-s', '--source', default='auto', help='源语言 (默认: auto)')
    parser.add_argument('-t', '--target', default='zh', help='目标语言 (默认: zh)')
    parser.add_argument('-m', '--model', default='medium', help='Whisper模型 (默认: medium)')
    
    args = parser.parse_args()
    
    # 创建窗口
    window = TranslatorWindow()
    
    # 创建处理器
    processor = AudioProcessor(
        window,
        source_lang=args.source,
        target_lang=args.target,
        model=args.model
    )
    
    try:
        window.set_status("正在初始化...")
        processor.start()
        window.set_status("运行中 - 正在捕获音频")
        
        # 运行窗口主循环
        window.run()
        
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        processor.stop()


if __name__ == '__main__':
    main()
