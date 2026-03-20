# 🎙️ 实时音频字幕翻译系统

捕获 macOS 扬声器输出，实时语音识别并翻译显示。

## 📋 功能

- 🔴 实时捕获系统音频（扬声器输出）
- 🎯 使用 Whisper 本地语音识别
- 🌐 支持多种语言互译
- 💻 终端或 GUI 界面显示
- 🔒 完全本地运行，无需联网（除翻译外）

## 🚀 快速开始

### 1. 一键安装

```bash
# 进入脚本目录
cd ~/.openclaw/workspace/scripts

# 运行安装脚本
./install-translator.sh
```

### 2. 配置音频路由（关键步骤）

安装脚本会提示，也可以手动配置：

1. 按 `Cmd + Space` 搜索打开 **"音频 MIDI 设置"**
2. 点击左下角 `+` → **创建多输出设备**
3. 在右侧勾选：
   - ☑️ **BlackHole 2ch**（捕获音频）
   - ☑️ **MacBook Pro 扬声器**（听到声音）
4. 关闭窗口
5. 打开 **系统设置 → 声音 → 输出**
6. 选择刚才创建的 **"多输出设备"**

> 💡 配置完成后，你的系统音频会被同时输出到扬声器和 BlackHole（用于识别）

### 3. 运行翻译

#### 方式一：终端版（轻量）

```bash
./realtime-translator.sh
```

#### 方式二：GUI版（推荐，有浮动窗口）

```bash
python3 realtime-translator-gui.py
```

## 📝 使用示例

### 日语视频 → 中文字幕

```bash
# 终端版
./realtime-translator.sh -s ja -t zh

# GUI版
python3 realtime-translator-gui.py -s ja -t zh
```

### 英语会议 → 中文字幕

```bash
./realtime-translator.sh -s en -t zh -m base
```

### 中文 → 英语

```bash
./realtime-translator.sh -s zh -t en
```

## ⚙️ 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-s, --source` | 源语言代码 | `auto` (自动检测) |
| `-t, --target` | 目标语言代码 | `zh` (中文) |
| `-m, --model` | Whisper模型 | `medium` |
| `-d, --duration` | 音频分段长度(秒) | `5` |

### 语言代码

- `zh` - 中文
- `ja` - 日语
- `en` - 英语
- `ko` - 韩语
- `fr` - 法语
- `de` - 德语
- `es` - 西班牙语
- `ru` - 俄语

### Whisper 模型选择

| 模型 | 大小 | 速度 | 准确度 | 适用场景 |
|------|------|------|--------|----------|
| `tiny` | 39 MB | ⚡ 最快 | ⭐ | 快速测试 |
| `base` | 74 MB | 🚀 快 | ⭐⭐ | 实时性要求高 |
| `small` | 244 MB | ⚡ 较快 | ⭐⭐⭐ | 平衡选择 |
| `medium` | 769 MB | 🐢 中等 | ⭐⭐⭐⭐ | **推荐** |
| `large` | 1550 MB | 🐌 慢 | ⭐⭐⭐⭐⭐ | 准确度优先 |

## 🎮 GUI 操作

- **置顶窗口**: 字幕窗口始终在最前面
- **快捷键**:
  - `Cmd + Q` 或 `Esc` - 退出程序
- **自动清理**: 自动删除已处理的临时文件

## 🔧 故障排除

### "未找到 BlackHole 设备"

```bash
# 重新安装 BlackHole
brew reinstall blackhole-2ch

# 重启音频 MIDI 设置应用
```

### "听不到声音了"

检查系统声音输出是否仍设置为"多输出设备"：
```bash
# 快速修复
osascript -e 'set volume output volume 50'  # 确保音量不是0
```

### 识别准确率低

1. 尝试更换模型：`--model large`
2. 指定源语言：`--source ja` 而不是 `auto`
3. 检查音频质量（确保扬声器音量适中）

### 翻译速度慢

```bash
# 使用轻量模型，牺牲一点准确度换取速度
./realtime-translator.sh -m base
```

## 📁 文件结构

```
scripts/
├── install-translator.sh          # 安装脚本
├── realtime-translator.sh         # 终端版主程序
├── realtime-translator-gui.py     # GUI版主程序
└── README.md                      # 本文件
```

## ⚠️ 已知限制

1. **延迟**: 由于分段处理，有 5-10 秒延迟
2. **翻译依赖网络**: translate-shell 需要联网（除中英互译有本地缓存）
3. **准确度**: 受音频质量、背景噪音影响
4. **不支持**: 实时连续流式识别（是分段处理）

## 🔄 工作流程

```
系统音频 → BlackHole 2ch → ffmpeg分段录制 → Whisper识别 → translate翻译 → 显示
```

## 🛠️ 手动安装（如脚本失败）

```bash
# 1. 安装依赖
brew install ffmpeg whisper.cpp translate-shell blackhole-2ch

# 2. 下载模型
whisper-cpp-model-download medium

# 3. 运行
./realtime-translator.sh
```

## 📝 日志与调试

```bash
# 查看实时日志
tail -f /tmp/audio_translator/*.log

# 测试音频捕获
ffmpeg -f avfoundation -i ":0" -t 5 test.wav
```

## 🙏 致谢

- [OpenAI Whisper](https://github.com/openai/whisper) - 语音识别
- [ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp) - C++ 移植版
- [BlackHole](https://github.com/ExistentialAudio/BlackHole) - 虚拟音频设备
- [translate-shell](https://github.com/soimort/translate-shell) - 翻译引擎

## 📄 许可证

MIT License - 自由使用，自负风险
