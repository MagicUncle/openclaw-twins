#!/bin/bash

# ============================================
# 实时音频字幕翻译系统
# Real-time Audio Caption & Translation
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 配置
WHISPER_MODEL="medium"
SOURCE_LANG="auto"  # 或指定: ja, zh, en 等
TARGET_LANG="zh"    # 翻译目标语言
SEGMENT_DURATION=5  # 每段音频长度（秒）
BUFFER_DIR="/tmp/audio_translator"
BLACKHOLE_DEVICE="BlackHole 2ch"

# 检查依赖
check_dependencies() {
    echo -e "${BLUE}🔍 检查依赖...${NC}"
    
    local deps=("ffmpeg" "whisper-cpp" "trans")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        echo -e "${RED}❌ 缺少依赖: ${missing[*]}${NC}"
        echo -e "${YELLOW}请运行安装命令:${NC}"
        echo "brew install ffmpeg whisper.cpp translate-shell"
        exit 1
    fi
    
    # 检查 BlackHole
    if ! ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | grep -q "$BLACKHOLE_DEVICE"; then
        echo -e "${YELLOW}⚠️  未检测到 BlackHole 2ch${NC}"
        echo -e "请先安装: ${CYAN}brew install blackhole-2ch${NC}"
        echo -e "然后在 音频 MIDI 设置 中配置多输出设备"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 所有依赖已就绪${NC}"
}

# 获取 BlackHole 设备索引
get_blackhole_index() {
    ffmpeg -f avfoundation -list_devices true -i "" 2>&1 | \
        grep -B 1 "$BLACKHOLE_DEVICE" | \
        grep "\\[\\d*\\]" | \
        head -1 | \
        sed -E 's/.*\[(.*)\].*/\1/'
}

# 创建缓冲区目录
setup_buffer() {
    rm -rf "$BUFFER_DIR"
    mkdir -p "$BUFFER_DIR"
    mkdir -p "$BUFFER_DIR/audio"
    mkdir -p "$BUFFER_DIR/text"
    echo -e "${GREEN}📁 工作目录: $BUFFER_DIR${NC}"
}

# 实时音频捕获
capture_audio() {
    local index=$(get_blackhole_index)
    local output_file="$BUFFER_DIR/audio/segment_%03d.wav"
    
    echo -e "${CYAN}🎙️  开始捕获音频 (设备: $index)...${NC}"
    echo -e "${YELLOW}💡 确保系统输出设置为 BlackHole 2ch 多输出设备${NC}"
    
    # 分段录制音频
    ffmpeg -f avfoundation -i ":$index" \
        -ar 16000 -ac 1 -c:a pcm_s16le \
        -f segment -segment_time $SEGMENT_DURATION \
        -reset_timestamps 1 \
        "$output_file" \
        -y 2>&1 | grep -E "(Output|Duration|size)" &
    
    echo $! > "$BUFFER_DIR/ffmpeg.pid"
}

# 获取 whisper 模型路径
get_whisper_model() {
    local model_path=$(whisper-cpp-model-path "$WHISPER_MODEL" 2>/dev/null || echo "")
    if [ -z "$model_path" ] || [ ! -f "$model_path" ]; then
        echo -e "${YELLOW}⬇️  下载 Whisper 模型...${NC}"
        whisper-cpp-model-download "$WHISPER_MODEL"
        model_path=$(whisper-cpp-model-path "$WHISPER_MODEL")
    fi
    echo "$model_path"
}

# 处理单个音频文件
process_audio_file() {
    local audio_file="$1"
    local base_name=$(basename "$audio_file" .wav)
    local text_file="$BUFFER_DIR/text/${base_name}.txt"
    local trans_file="$BUFFER_DIR/text/${base_name}_trans.txt"
    
    # 语音识别
    local transcript=$(whisper-cpp \
        -m "$WHISPER_MODEL_PATH" \
        -f "$audio_file" \
        -l "$SOURCE_LANG" \
        --no-timestamps \
        -otxt 2>/dev/null | tail -n 1)
    
    if [ -n "$transcript" ] && [ ${#transcript} -gt 2 ]; then
        echo "$transcript" > "$text_file"
        
        # 翻译
        local translation=$(echo "$transcript" | trans -brief -no-warn -no-autocorrect ":$TARGET_LANG" 2>/dev/null || echo "")
        
        if [ -n "$translation" ]; then
            echo "$translation" > "$trans_file"
            display_result "$transcript" "$translation"
        fi
    fi
    
    # 清理已处理的文件
    rm -f "$audio_file"
}

# 显示结果
display_result() {
    local original="$1"
    local translation="$2"
    
    clear
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}📝 原文:${NC} $original"
    echo -e "${GREEN}🔄 翻译:${NC} $translation"
    echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止${NC}"
}

# 监控新音频文件
monitor_and_process() {
    echo -e "${CYAN}🤖 开始实时处理...${NC}"
    
    local processed=()
    
    while true; do
        for audio_file in "$BUFFER_DIR/audio"/segment_*.wav; do
            [ -e "$audio_file" ] || continue
            
            # 检查文件是否已完成写入（至少比 segment_duration 旧）
            local file_age=$(($(date +%s) - $(stat -f %m "$audio_file")))
            if [ $file_age -ge $SEGMENT_DURATION ]; then
                if [[ ! " ${processed[*]} " =~ " ${audio_file} " ]]; then
                    processed+=("$audio_file")
                    process_audio_file "$audio_file" &
                fi
            fi
        done
        
        sleep 1
    done
}

# 使用 AppleScript 显示浮动窗口（可选）
show_floating_window() {
    osascript <<EOF
    tell application "System Events"
        display dialog "$1" with title "实时翻译" buttons {"确定"} default button "确定" giving up after 3
    end tell
EOF
}

# 发送通知
send_notification() {
    local title="$1"
    local subtitle="$2"
    
    osascript -e "display notification \"$subtitle\" with title \"$title\""
}

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}🛑 正在停止...${NC}"
    
    # 停止 ffmpeg
    if [ -f "$BUFFER_DIR/ffmpeg.pid" ]; then
        kill $(cat "$BUFFER_DIR/ffmpeg.pid") 2>/dev/null || true
        rm -f "$BUFFER_DIR/ffmpeg.pid"
    fi
    
    # 停止所有后台进程
    pkill -f "whisper-cpp.*$BUFFER_DIR" 2>/dev/null || true
    
    # 可选：保留或清理临时文件
    # rm -rf "$BUFFER_DIR"
    
    echo -e "${GREEN}✅ 已停止，临时文件保留在: $BUFFER_DIR${NC}"
    exit 0
}

# 显示帮助
show_help() {
    cat << 'EOF'
实时音频字幕翻译系统

用法: ./realtime-translator.sh [选项]

选项:
    -s, --source LANG    源语言 (默认: auto)
    -t, --target LANG    目标语言 (默认: zh)
    -m, --model MODEL    Whisper模型 (tiny/base/small/medium/large, 默认: medium)
    -d, --duration SEC   分段长度秒数 (默认: 5)
    -h, --help          显示帮助

示例:
    ./realtime-translator.sh                    # 默认配置 (任意语言 -> 中文)
    ./realtime-translator.sh -s ja -t zh        # 日语 -> 中文
    ./realtime-translator.sh -s en -t zh -m base # 英语 -> 中文, 使用轻量模型

语言代码:
    zh = 中文, ja = 日语, en = 英语, ko = 韩语
    fr = 法语, de = 德语, es = 西班牙语
EOF
}

# 解析参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -s|--source)
                SOURCE_LANG="$2"
                shift 2
                ;;
            -t|--target)
                TARGET_LANG="$2"
                shift 2
                ;;
            -m|--model)
                WHISPER_MODEL="$2"
                shift 2
                ;;
            -d|--duration)
                SEGMENT_DURATION="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}未知选项: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
}

# 主函数
main() {
    parse_args "$@"
    
    echo -e "${GREEN}"
    echo "╔═══════════════════════════════════════════════════╗"
    echo "║    实时音频字幕翻译系统 (Real-time Translator)    ║"
    echo "╚═══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "配置: ${CYAN}$SOURCE_LANG${NC} -> ${CYAN}$TARGET_LANG${NC} | 模型: ${CYAN}$WHISPER_MODEL${NC} | 分段: ${CYAN}${SEGMENT_DURATION}s${NC}"
    
    # 检查依赖
    check_dependencies
    
    # 设置环境
    setup_buffer
    
    # 获取模型路径
    WHISPER_MODEL_PATH=$(get_whisper_model)
    echo -e "${GREEN}📦 使用模型: $WHISPER_MODEL_PATH${NC}"
    
    # 设置清理钩子
    trap cleanup SIGINT SIGTERM EXIT
    
    # 启动音频捕获
    capture_audio
    
    # 等待 ffmpeg 开始录制
    sleep 2
    
    # 开始处理
    monitor_and_process
}

# 运行
main "$@"
