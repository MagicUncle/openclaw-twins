#!/bin/zsh
# 日历检查和钉钉推送 - 备用脚本
# 可以直接运行：./daily-calendar-check-and-notify.sh

TOMORROW=$(date -v+1d +"%Y年%m月%d日")

# 获取日历事件
CALENDAR_RESULT=$(osascript << 'EOF' 2>/dev/null
tell application "Calendar"
    set tomorrow to (current date) + 1 * days
    set startOfTomorrow to tomorrow - (time of tomorrow)
    set endOfTomorrow to startOfTomorrow + 1 * days - 1
    set eventList to {}
    repeat with cal in calendars
        try
            set calEvents to (every event of cal whose start date ≥ startOfTomorrow and start date ≤ endOfTomorrow)
            repeat with evt in calEvents
                set eventInfo to (time string of (start date of evt)) & " - " & (summary of evt)
                set end of eventList to eventInfo
            end repeat
        end try
    end repeat
    if length of eventList > 0 then
        set AppleScript's text item delimiters to return
        return ("明天的日历事件：" & return & return & (eventList as string))
    else
        return "明天没有日历事件"
    end if
end tell
EOF
)

# 获取提醒事项
REMINDERS_RESULT=$(osascript << 'EOF' 2>/dev/null
tell application "Reminders"
    set tomorrow to (current date) + 1 * days
    set startOfTomorrow to tomorrow - (time of tomorrow)
    set endOfTomorrow to startOfTomorrow + 1 * days - 1
    set reminderList to {}
    repeat with remList in lists
        try
            set listReminders to (every reminder of remList whose due date ≥ startOfTomorrow and due date ≤ endOfTomorrow and completed is false)
            repeat with rem in listReminders
                set remInfo to (time string of (due date of rem)) & " - " & (name of rem)
                set end of reminderList to remInfo
            end repeat
        end try
    end repeat
    if length of reminderList > 0 then
        set AppleScript's text item delimiters to return
        return ("明天的提醒事项：" & return & return & (reminderList as string))
    else
        return "明天没有提醒事项"
    end if
end tell
EOF
)

# 构建消息
if [[ "$CALENDAR_RESULT" == "明天没有日历事件" && "$REMINDERS_RESULT" == "明天没有提醒事项" ]]; then
    MESSAGE="📅 日历检查 - ${TOMORROW}

✅ 已检查日历，明天没有需要提醒您的事项

——MagicClaw"
else
    MESSAGE="📅 日历检查 - ${TOMORROW}

${CALENDAR_RESULT}

${REMINDERS_RESULT}

——MagicClaw"
fi

echo "$MESSAGE"

# 使用 openclaw 发送到钉钉
openclaw message send --channel dingtalk --message "$MESSAGE" 2>/dev/null || echo "钉钉发送失败，请检查配置"
