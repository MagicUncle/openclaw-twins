#!/bin/bash

# ============================================
# 实时音频翻译系统 - 安装脚本
# ============================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════╗"
echo "║      实时音频翻译系统 - 安装向导                  ║"
echo "╚═══════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ 未检测到 Homebrew${NC}"
    echo -e "请先安装: ${CYAN}/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"${NC}"
    exit 1
fi

echo -e "${BLUE}📦 正在安装依赖...${NC}"

# 安装核心依赖
echo -e "${CYAN}1/5 安装 ffmpeg...${NC}"
brew install ffmpeg

echo -e "${CYAN}2/5 安装 whisper.cpp...${NC}"
brew install whisper.cpp

echo -e "${CYAN}3/5 安装 translate-shell...${NC}"
brew install translate-shell

echo -e "${CYAN}4/5 安装 BlackHole（虚拟音频设备）...${NC}"
brew install blackhole-2ch

echo -e "${CYAN}5/5 可选：安装 MacWhisper（图形界面版）...${NC}"
echo -e "${YELLOW}   如需图形界面，请手动下载: ${CYAN}https://goodsnooze.gumroad.com/l/macwhisper${NC}"

# 下载默认模型
echo -e "${BLUE}📥 下载 Whisper 模型...${NC}"
whisper-cpp-model-download medium

echo -e "${GREEN}✅ 基础安装完成！${NC}"

echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}⚠️  重要：需要手动配置音频路由${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

echo -e "\n${CYAN}请按以下步骤设置：${NC}"
echo ""
echo "1. 打开 '音频 MIDI 设置'（按 Cmd+Space 搜索）"
echo ""
echo "2. 点击左下角 '+' 按钮，选择 '创建多输出设备'"
echo ""
echo "3. 在右侧勾选："
echo "   ☑️ BlackHole 2ch"
echo "   ☑️ 你的实际扬声器（如 MacBook Pro 扬声器）"
echo ""
echo "4. 关闭窗口"
echo ""
echo "5. 打开 系统设置 → 声音 → 输出"
echo "   选择刚才创建的 '多输出设备'"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 安装完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "使用方法："
echo -e "  ${CYAN}./realtime-translator.sh${NC}                    # 默认配置"
echo -e "  ${CYAN}./realtime-translator.sh -s ja -t zh${NC}        # 日语→中文"
echo -e "  ${CYAN}./realtime-translator.sh -s en -t zh -m base${NC} # 英语→中文(轻量)"
echo ""
echo -e "查看帮助：${CYAN}./realtime-translator.sh --help${NC}"
echo ""
