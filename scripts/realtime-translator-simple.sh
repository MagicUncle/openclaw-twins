#!/bin/bash

# ============================================
# 实时音频字幕翻译 - Web 版
# ============================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# 配置
SOURCE_LANG="${1:-auto}"
TARGET_LANG="${2:-zh}"
WHISPER_MODEL="${3:-base}"
SEGMENT_DURATION=5
BUFFER_DIR="/tmp/audio_translator_simple"

# 从环境变量读取翻译配置
TRANSLATOR_TYPE="${TRANSLATOR:-local}"
PROXY_URL="${PROXY:-}"
DEEPL_KEY="${DEEPL_API_KEY:-}"

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}🛑 正在停止...${NC}"
    if [ -n "$FFMPEG_PID" ]; then
        kill $FFMPEG_PID 2>/dev/null || true
    fi
    pkill -f "whisper-cli" 2>/dev/null || true
    echo -e "${GREEN}✅ 已停止${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 获取 BlackHole 索引
get_blackhole_index() {
    ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | \
        grep -B 1 "BlackHole 2ch" | \
        grep "\[\d*\]" | \
        head -1 | \
        sed -E 's/.*\[(.*)\].*/\1/'
}

# 翻译函数
translate_text() {
    local text="$1"
    
    case "$TRANSLATOR_TYPE" in
        "google")
            # Google 翻译
            if [ -n "$PROXY_URL" ]; then
                export HTTP_PROXY="$PROXY_URL"
                export HTTPS_PROXY="$PROXY_URL"
            fi
            echo "$text" | trans -brief -no-warn -no-autocorrect ":$TARGET_LANG" 2>/dev/null || echo ""
            ;;
        "deepl")
            # DeepL 翻译（需要 API Key）
            if [ -z "$DEEPL_KEY" ]; then
                echo "[错误: 未设置 DeepL API Key]"
                return
            fi
            curl -s -X POST "https://api-free.deepl.com/v2/translate" \
                -H "Authorization: DeepL-Auth-Key $DEEPL_KEY" \
                -d "text=$text" \
                -d "target_lang=${TARGET_LANG^^}" 2>/dev/null | \
                python3 -c "import sys,json; data=json.load(sys.stdin); print(data['translations'][0]['text'])" 2>/dev/null || echo ""
            ;;
        "local"|*)
            # 本地模型翻译
            SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
            WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"
            (cd "$WORKSPACE_DIR" && source translator-env/bin/activate 2>/dev/null && echo "$text" | python3 scripts/local_translate.py 2>/dev/null) || echo ""
            ;;
    esac
}

# 主程序
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}    实时音频字幕翻译${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "配置: ${CYAN}$SOURCE_LANG${NC} -> ${CYAN}$TARGET_LANG${NC} | 模型: ${CYAN}$WHISPER_MODEL${NC} | 翻译: ${CYAN}$TRANSLATOR_TYPE${NC}"
echo ""

# 检查依赖
if ! command -v whisper-cli >/dev/null 2>&1; then
    echo -e "${RED}❌ 未安装 whisper.cpp${NC}"
    exit 1
fi

# 获取模型路径
MODEL_PATH="$HOME/.local/share/whisper/ggml-$WHISPER_MODEL.bin"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${RED}❌ 模型文件不存在: $MODEL_PATH${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 模型就绪: $WHISPER_MODEL${NC}"

# 获取设备
DEVICE_INDEX=$(get_blackhole_index)
if [ -z "$DEVICE_INDEX" ]; then
    echo -e "${RED}❌ 未找到 BlackHole 设备${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 音频设备: BlackHole 2ch [$DEVICE_INDEX]${NC}"

# 创建工作目录
rm -rf "$BUFFER_DIR"
mkdir -p "$BUFFER_DIR/audio"
mkdir -p "$BUFFER_DIR/text"

# 启动音频捕获
echo -e "${CYAN}🎙️  开始捕获音频...${NC}"
echo -e "${YELLOW}💡 现在可以播放视频/音频了${NC}"
echo ""

ffmpeg -f avfoundation -i ":$DEVICE_INDEX" \
    -ar 16000 -ac 1 -c:a pcm_s16le \
    -f segment -segment_time $SEGMENT_DURATION \
    -reset_timestamps 1 \
    "$BUFFER_DIR/audio/segment_%03d.wav" \
    -y 2>/dev/null &

FFMPEG_PID=$!
sleep 3

# 处理循环
while true; do
    for audio_file in "$BUFFER_DIR/audio"/segment_*.wav; do
        [ -e "$audio_file" ] || continue
        
        # 检查文件年龄
        file_age=$(($(date +%s) - $(stat -f %m "$audio_file")))
        if [ $file_age -lt $SEGMENT_DURATION ]; then
            continue
        fi
        
        file_id=$(basename "$audio_file")
        
        # 检查是否已处理
        if [ -f "$BUFFER_DIR/text/${file_id}.done" ]; then
            rm -f "$audio_file"
            continue
        fi
        
        # 转录
        echo -e "${CYAN}🎤 识别中...${NC}"
        transcript=$(whisper-cli \
            -m "$MODEL_PATH" \
            -f "$audio_file" \
            --language "$SOURCE_LANG" \
            --no-timestamps \
            -otxt 2>/dev/null | tail -n 1)
        
        if [ -n "$transcript" ] && [ ${#transcript} -gt 2 ]; then
            echo -e "📝 原文: $transcript"
            
            # 翻译
            echo -e "${CYAN}🔄 翻译中...${NC}"
            translation=$(translate_text "$transcript")
            
            if [ -n "$translation" ]; then
                echo -e "${GREEN}✅ 翻译: $translation${NC}"
            fi
        fi
        
        # 标记为已处理
        touch "$BUFFER_DIR/text/${file_id}.done"
        rm -f "$audio_file"
    done
    
    sleep 1
done
