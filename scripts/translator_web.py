#!/usr/bin/env python3
"""
实时字幕翻译 - Web 配置界面
"""
import os
import sys
import json
import time
import subprocess
import threading
from flask import Flask, render_template, jsonify, request, stream_with_context, Response

app = Flask(__name__)

# 配置文件路径
CONFIG_FILE = os.path.expanduser("~/.config/realtime-translator/config.json")
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

# 默认配置
DEFAULT_CONFIG = {
    "translator": "local",  # local, google, deepl
    "source_lang": "auto",
    "target_lang": "zh",
    "whisper_model": "base",  # tiny, base, small, medium
    "deepl_api_key": "",
    "proxy": "",  # e.g., http://127.0.0.1:7890
    "segment_duration": 5,
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# 存储运行状态
translator_process = None
latest_subtitle = {"original": "", "translated": "", "timestamp": 0}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(load_config())

@app.route('/api/config', methods=['POST'])
def update_config():
    config = load_config()
    config.update(request.json)
    save_config(config)
    return jsonify({"status": "ok"})

@app.route('/api/models')
def list_models():
    """列出可用的本地模型"""
    models = []
    whisper_dir = os.path.expanduser("~/.local/share/whisper")
    if os.path.exists(whisper_dir):
        for f in os.listdir(whisper_dir):
            if f.endswith('.bin'):
                models.append(f.replace('ggml-', '').replace('.bin', ''))
    return jsonify(models)

@app.route('/api/start', methods=['POST'])
def start_translator():
    global translator_process
    if translator_process and translator_process.poll() is None:
        return jsonify({"error": "已经在运行中"}), 400
    
    config = load_config()
    
    # 构建启动命令
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)
    
    env = os.environ.copy()
    if config.get('proxy'):
        env['HTTP_PROXY'] = config['proxy']
        env['HTTPS_PROXY'] = config['proxy']
    
    # 选择脚本
    if config['translator'] == 'local':
        script = os.path.join(script_dir, 'realtime-translator-simple.sh')
    else:
        script = os.path.join(script_dir, 'realtime-translator-simple.sh')
    
    try:
        translator_process = subprocess.Popen(
            ['bash', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=script_dir,
            env=env
        )
        
        # 启动后台线程读取输出
        threading.Thread(target=read_output, daemon=True).start()
        
        return jsonify({"status": "started"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def read_output():
    """读取翻译脚本的输出"""
    global latest_subtitle, translator_process
    if not translator_process:
        print("[DEBUG] translator_process is None")
        return
    
    print("[DEBUG] 开始读取脚本输出...")
    original = ""
    translated = ""
    
    try:
        for line in translator_process.stdout:
            line = line.strip()
            print(f"[SCRIPT] {line}")
            
            if line.startswith('📝 原文:') or '原文:' in line:
                original = line.split('原文:')[-1].strip()
                print(f"[DEBUG] 识别到原文: {original}")
            elif '翻译:' in line and ('✅' in line or '🔄' in line):
                translated = line.split('翻译:')[-1].strip()
                print(f"[DEBUG] 识别到翻译: {translated}")
                latest_subtitle = {
                    "original": original,
                    "translated": translated,
                    "timestamp": int(time.time())
                }
                print(f"[DEBUG] 更新字幕: {latest_subtitle}")
    except Exception as e:
        print(f"[ERROR] 读取输出时出错: {e}")
    
    print("[DEBUG] 脚本输出读取结束")

@app.route('/api/stop', methods=['POST'])
def stop_translator():
    global translator_process
    if translator_process:
        translator_process.terminate()
        translator_process = None
    return jsonify({"status": "stopped"})

@app.route('/api/status')
def get_status():
    running = translator_process is not None and translator_process.poll() is None
    return jsonify({
        "running": running,
        "subtitle": latest_subtitle
    })

@app.route('/api/subtitle/stream')
def stream_subtitle():
    """SSE 流式推送字幕"""
    def event_stream():
        last_ts = 0
        while True:
            if latest_subtitle["timestamp"] > last_ts:
                last_ts = latest_subtitle["timestamp"]
                yield f"data: {json.dumps(latest_subtitle)}\n\n"
            time.sleep(0.5)
    
    return Response(stream_with_context(event_stream()), 
                   mimetype='text/event-stream')

if __name__ == '__main__':
    print("启动实时字幕翻译控制面板...")
    print("请在浏览器打开: http://127.0.0.1:8080")
    app.run(host='127.0.0.1', port=8080, debug=False)
