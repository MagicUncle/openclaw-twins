#!/bin/zsh
# Daily Calendar & Reminders Check
# 每天晚上检查第二天的日历事件和提醒事项

# 获取明天的日期
TOMORROW=$(date -v+1d +%Y-%m-%d)
TOMORROW_DISPLAY=$(date -v+1d +"%Y年%m月%d日")

echo "📅 日历检查 - ${TOMORROW_DISPLAY}"
echo "================================"

# 使用 AppleScript 获取明天的日历事件
CALENDAR_EVENTS=$(osascript << 'EOF'
set tomorrow to (current date) + 1 * days
set startOfTomorrow to tomorrow - (time of tomorrow)
set endOfTomorrow to startOfTomorrow + 1 * days - 1

tell application "Calendar"
    set eventList to {}
    set allCalendars to calendars
    repeat with cal in allCalendars
        set calEvents to (every event of cal whose start date ≥ startOfTomorrow and start date ≤ endOfTomorrow)
        repeat with evt in calEvents
            set eventTitle to summary of evt
            set eventTime to time string of (start date of evt)
            set end of eventList to (eventTime & " - " & eventTitle)
        end repeat
    end repeat
    return eventList as string
end tell
EOF
)

# 使用 AppleScript 获取明天的提醒事项
REMINDERS=$(osascript << 'EOF'
set tomorrow to (current date) + 1 * days
set startOfTomorrow to tomorrow - (time of tomorrow)
set endOfTomorrow to startOfTomorrow + 1 * days - 1

tell application "Reminders"
    set reminderList to {}
    set allLists to lists
    repeat with reminderListItem in allLists
        set listReminders to (every reminder of reminderListItem whose due date ≥ startOfTomorrow and due date ≤ endOfTomorrow and completed is false)
        repeat with rem in listReminders
            set remName to name of rem
            set remTime to time string of (due date of rem)
            set end of reminderList to (remTime & " - " & remName)
        end repeat
    end repeat
    return reminderList as string
end tell
EOF
)

# 检查是否有内容
HAS_CONTENT=false

if [[ -n "$CALENDAR_EVENTS" && "$CALENDAR_EVENTS" != "missing value" ]]; then
    HAS_CONTENT=true
    echo ""
    echo "📆 明天日历事件："
    echo "$CALENDAR_EVENTS" | tr ',' '\n' | sed 's/^/  • /'
fi

if [[ -n "$REMINDERS" && "$REMINDERS" != "missing value" ]]; then
    HAS_CONTENT=true
    echo ""
    echo "🔔 明天提醒事项："
    echo "$REMINDERS" | tr ',' '\n' | sed 's/^/  • /'
fi

if [[ "$HAS_CONTENT" == false ]]; then
    echo ""
    echo "✅ 已检查日历，明天没有需要提醒您的事项"
fi

echo ""
echo "================================"
