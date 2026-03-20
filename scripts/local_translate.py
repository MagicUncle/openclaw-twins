#!/usr/bin/env python3
"""
本地翻译脚本 - 使用 Helsinki-NLP 轻量级模型
支持模型缓存，避免重复加载
"""
import sys
import os

# 设置模型缓存目录
cache_dir = os.path.expanduser("~/.cache/huggingface")
os.makedirs(cache_dir, exist_ok=True)

# 全局模型缓存
_model_cache = {}

def get_model(model_name):
    """获取或加载模型（带缓存）"""
    if model_name not in _model_cache:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=cache_dir)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, cache_dir=cache_dir)
        _model_cache[model_name] = (tokenizer, model)
    return _model_cache[model_name]

def translate_en_to_zh(text):
    """英译中"""
    try:
        tokenizer, model = get_model("Helsinki-NLP/opus-mt-en-zh")
        inputs = tokenizer(text, return_tensors="pt", padding=True)
        outputs = model.generate(**inputs)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
    except Exception as e:
        return f"[翻译错误: {e}]"

def translate_zh_to_en(text):
    """中译英"""
    try:
        tokenizer, model = get_model("Helsinki-NLP/opus-mt-zh-en")
        inputs = tokenizer(text, return_tensors="pt", padding=True)
        outputs = model.generate(**inputs)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return translated
    except Exception as e:
        return f"[翻译错误: {e}]"

def translate_auto(text, target="zh"):
    """自动检测源语言并翻译"""
    # 简单检测：如果包含大量中文字符，认为是中文
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    if chinese_chars > len(text) * 0.3:
        return translate_zh_to_en(text)
    else:
        return translate_en_to_zh(text)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        text = sys.stdin.read().strip()
    else:
        text = " ".join(sys.argv[1:])
    
    if not text:
        print("用法: python3 local_translate.py '要翻译的文本'")
        sys.exit(1)
    
    result = translate_auto(text)
    print(result)
