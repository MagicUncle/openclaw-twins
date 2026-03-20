#!/usr/bin/env python3
"""
Overseer - 监控优化师核心脚本 v2.0
采集真实 Agent Session 数据，生成效能报告
数据源：~/.openclaw/agents/*/sessions/*.jsonl
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import asyncio

# 配置路径
WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"   # 真实 session 数据
METRICS_DIR = WORKSPACE / "metrics"
DAILY_DIR = METRICS_DIR / "daily"
REPORTS_DIR = METRICS_DIR / "reports"
DATA_DIR = WORKSPACE / "agents" / "overseer" / "data"

# 需要监控的 Agent 列表（自动发现 + 排除系统 agent）
EXCLUDE_AGENTS = {"overseer", "architect"}

# 确保目录存在
for d in [DAILY_DIR, REPORTS_DIR, DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)


class Overseer:
    """监控优化师核心类"""

    def __init__(self):
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.agent_stats: Dict[str, Dict] = {}

    def _discover_agents(self) -> List[str]:
        """自动发现所有 agent 目录"""
        agents = []
        if not OPENCLAW_AGENTS_DIR.exists():
            print(f"⚠️ Agent 目录不存在: {OPENCLAW_AGENTS_DIR}")
            return agents
        for entry in sorted(OPENCLAW_AGENTS_DIR.iterdir()):
            if entry.is_dir() and not entry.name.startswith('.') and entry.name not in EXCLUDE_AGENTS:
                agents.append(entry.name)
        return agents

    def _parse_jsonl_file(self, filepath: Path, agent_name: str,
                          cutoff: datetime) -> List[Dict]:
        """解析单个 JSONL session 文件，只返回 cutoff 之后的记录"""
        records = []
        parse_errors = 0
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                for lineno, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        parse_errors += 1
                        continue

                    # 时间过滤：只取 cutoff 之后的记录
                    ts_raw = record.get("timestamp") or record.get("created_at") or ""
                    if ts_raw:
                        try:
                            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                            ts = ts.replace(tzinfo=None)  # 统一 naive datetime
                            if ts < cutoff:
                                continue
                        except Exception:
                            pass  # 时间戳解析失败则不过滤

                    record["_agent"] = agent_name
                    record["_source_file"] = filepath.name
                    records.append(record)
        except Exception as e:
            print(f"  ⚠️ 读取失败 {filepath.name}: {e}")
        if parse_errors:
            print(f"  ⚠️ {filepath.name}: 跳过 {parse_errors} 条格式错误记录")
        return records

    async def collect_sessions(self) -> List[Dict]:
        """从真实 ~/.openclaw/agents/*/sessions/*.jsonl 采集过去 24h 数据"""
        print("🔍 正在采集真实 Agent Session 数据...")

        cutoff = datetime.now() - timedelta(hours=24)
        sessions = []
        agents_found = self._discover_agents()

        if not agents_found:
            print("⚠️ 未发现任何 Agent 目录，请检查路径配置")
            return sessions

        print(f"  发现 {len(agents_found)} 个 Agent: {', '.join(agents_found)}")

        for agent_name in agents_found:
            sessions_dir = OPENCLAW_AGENTS_DIR / agent_name / "sessions"
            if not sessions_dir.exists():
                print(f"  ⚪ {agent_name}: 无 sessions 目录，跳过")
                continue

            # 找到该 agent 的所有 .jsonl 文件，按修改时间倒序
            jsonl_files = sorted(
                sessions_dir.glob("*.jsonl"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if not jsonl_files:
                print(f"  ⚪ {agent_name}: sessions 目录为空，跳过")
                continue

            agent_records = []
            # 读取最新的 5 个文件（覆盖 24h 已足够）
            for f in jsonl_files[:5]:
                recs = self._parse_jsonl_file(f, agent_name, cutoff)
                agent_records.extend(recs)

            print(f"  ✅ {agent_name}: {len(agent_records)} 条记录（最近 {len(jsonl_files[:5])} 个文件）")
            sessions.extend(agent_records)

        print(f"\n✅ 共采集到 {len(sessions)} 条真实记录，覆盖 {len(agents_found)} 个 Agent")
        return sessions

    def analyze_sessions(self, sessions: List[Dict]) -> Dict[str, Dict]:
        """分析真实 JSONL 会话数据，计算各 Agent 指标"""
        print("📊 正在分析会话数据...")

        agent_stats = {}

        for record in sessions:
            # 真实 JSONL 格式适配：_agent 字段由采集时注入
            agent_name = record.get("_agent") or record.get("agent", "unknown")

            if agent_name not in agent_stats:
                agent_stats[agent_name] = {
                    "calls": 0,
                    "success": 0,
                    "total_duration_ms": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "tools_used": set(),
                    "errors": [],
                    "tool_call_count": 0,
                    "last_active": None,
                }

            stats = agent_stats[agent_name]
            role = record.get("role", "")

            # 只统计 assistant 消息作为一次"调用"
            if role == "assistant":
                stats["calls"] += 1

                # Token 消耗（从 usage 字段读取）
                usage = record.get("usage") or {}
                stats["total_input_tokens"] += usage.get("input_tokens", 0)
                stats["total_output_tokens"] += usage.get("output_tokens", 0)

                # 工具调用
                tool_calls = record.get("tool_calls") or []
                if tool_calls:
                    stats["tool_call_count"] += len(tool_calls)
                    for tc in tool_calls:
                        tool_name = tc.get("function", {}).get("name") or tc.get("name", "")
                        if tool_name:
                            stats["tools_used"].add(tool_name)

                # 错误检测
                err = record.get("error")
                if err:
                    stats["errors"].append(str(err)[:100])
                else:
                    stats["success"] += 1

                # 最后活跃时间
                ts = record.get("timestamp") or record.get("created_at")
                if ts:
                    if stats["last_active"] is None or ts > stats["last_active"]:
                        stats["last_active"] = ts

            elif role == "tool":
                # tool 结果消息：记录工具名
                tool_name = record.get("name") or record.get("tool_name", "")
                if tool_name:
                    stats["tools_used"].add(tool_name)

            # 兼容旧格式（非标准 JSONL）
            if role not in ("assistant", "user", "tool", "system", ""):
                stats["calls"] += 1
                if record.get("success", True):
                    stats["success"] += 1
                else:
                    err_list = record.get("errors", [])
                    stats["errors"].append(err_list[0] if err_list else "unknown")
                stats["total_input_tokens"] += record.get("input_tokens", 0)
                stats["total_output_tokens"] += record.get("output_tokens", 0)
                for t in record.get("tools_used", []):
                    stats["tools_used"].add(t)

        # 计算派生指标
        for agent, stats in agent_stats.items():
            calls = stats["calls"]
            stats["total_tokens"] = stats["total_input_tokens"] + stats["total_output_tokens"]
            # 预估成本（输入 $0.002/1K，输出 $0.006/1K）
            stats["estimated_cost_usd"] = round(
                stats["total_input_tokens"] / 1000 * 0.002 +
                stats["total_output_tokens"] / 1000 * 0.006, 4
            )

            if calls > 0:
                stats["success_rate"] = round(stats["success"] / calls, 3)
                stats["avg_input_tokens"] = round(stats["total_input_tokens"] / calls, 1)
                stats["avg_output_tokens"] = round(stats["total_output_tokens"] / calls, 1)

                # 效能评分公式：(调用次数 × 成功率) / (Token消耗/1000)
                token_k = max(stats["total_tokens"] / 1000, 0.1)
                stats["efficiency_score"] = round((calls * stats["success_rate"]) / token_k, 2)

                # 等级评定
                if stats["efficiency_score"] > 10 and stats["success_rate"] > 0.9:
                    stats["grade"] = "A"
                elif stats["efficiency_score"] >= 5 and stats["success_rate"] >= 0.7:
                    stats["grade"] = "B"
                else:
                    stats["grade"] = "C"
            else:
                stats["success_rate"] = 0.0
                stats["avg_input_tokens"] = 0.0
                stats["avg_output_tokens"] = 0.0
                stats["efficiency_score"] = 0.0
                stats["grade"] = "C"

            # set → list（JSON 序列化）
            stats["tools_used"] = sorted(stats["tools_used"])
            # 旧字段兼容（avg_duration_ms 在真实数据中无法直接获取）
            stats["avg_duration_ms"] = 0

        self.agent_stats = agent_stats
        print(f"✅ 分析了 {len(agent_stats)} 个Agent的数据")
        return agent_stats

    def generate_insights(self) -> List[Dict]:
        """生成洞察和建议"""
        print("💡 正在生成洞察...")

        insights = []

        # 1. 低成功率Agent
        low_success = [(name, s) for name, s in self.agent_stats.items()
                      if s["success_rate"] < 0.7]
        if low_success:
            insights.append({
                "type": "warning",
                "level": "P0",
                "title": "低成功率Agent",
                "description": f"发现 {len(low_success)} 个Agent成功率低于70%",
                "agents": [{"name": n, "rate": s["success_rate"]} for n, s in low_success],
                "suggestion": "建议检查这些Agent的错误日志，优化Prompt或添加重试逻辑"
            })

        # 2. 高Token消耗Agent
        high_cost = sorted(self.agent_stats.items(),
                          key=lambda x: x[1]["total_tokens"], reverse=True)[:3]
        if high_cost:
            insights.append({
                "type": "info",
                "level": "P1",
                "title": "高Token消耗Top3",
                "description": "这些Agent消耗了最多Token资源",
                "agents": [{"name": n, "tokens": s["total_tokens"]} for n, s in high_cost],
                "suggestion": "考虑优化工具调用链、引入缓存或使用更轻量模型"
            })

        # 3. C级Agent
        c_grade = [(name, s) for name, s in self.agent_stats.items() if s["grade"] == "C"]
        if c_grade:
            insights.append({
                "type": "warning",
                "level": "P1",
                "title": "C级效能Agent",
                "description": f"有 {len(c_grade)} 个Agent效能评分低于标准",
                "agents": [{"name": n, "score": s["efficiency_score"]} for n, s in c_grade],
                "suggestion": "需要全面优化这些Agent的设计和实现"
            })

        # 4. 最活跃Agent
        most_active = max(self.agent_stats.items(), key=lambda x: x[1]["calls"])
        insights.append({
            "type": "success",
            "level": "P2",
            "title": "最活跃Agent",
            "description": f"{most_active[0]} 今日被调用 {most_active[1]['calls']} 次",
            "suggestion": "该Agent承载主要业务，建议重点保障稳定性"
        })

        print(f"✅ 生成 {len(insights)} 条洞察")
        return insights

    def generate_json_report(self) -> Path:
        """生成JSON结构化报告"""
        print("📝 正在生成JSON报告...")

        # 计算汇总数据
        total_calls = sum(s["calls"] for s in self.agent_stats.values())
        total_tokens = sum(s["total_tokens"] for s in self.agent_stats.values())
        avg_success = sum(s["success_rate"] for s in self.agent_stats.values()) / len(self.agent_stats) if self.agent_stats else 0

        report = {
            "date": self.today,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_agents": len(self.agent_stats),
                "total_calls": total_calls,
                "total_tokens": total_tokens,
                "avg_success_rate": round(avg_success, 3),
                "avg_efficiency_score": round(sum(s["efficiency_score"] for s in self.agent_stats.values()) / len(self.agent_stats), 2) if self.agent_stats else 0
            },
            "agents": self.agent_stats,
            "insights": self.generate_insights(),
            "ranking": self._generate_ranking()
        }

        # 保存JSON
        json_path = DAILY_DIR / f"{self.today}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"✅ JSON报告已保存: {json_path}")
        return json_path

    def _generate_ranking(self) -> List[Dict]:
        """生成Agent排名"""
        ranked = sorted(
            self.agent_stats.items(),
            key=lambda x: x[1]["efficiency_score"],
            reverse=True
        )
        return [
            {
                "rank": i + 1,
                "name": name,
                "efficiency_score": stats["efficiency_score"],
                "success_rate": stats["success_rate"],
                "grade": stats["grade"],
                "calls": stats["calls"]
            }
            for i, (name, stats) in enumerate(ranked)
        ]

    def generate_markdown_report(self) -> Path:
        """生成Markdown可视化报告"""
        print("📝 正在生成Markdown报告...")

        # 计算汇总
        summary = {
            "total_agents": len(self.agent_stats),
            "total_calls": sum(s["calls"] for s in self.agent_stats.values()),
            "total_tokens": sum(s["total_tokens"] for s in self.agent_stats.values()),
            "avg_success_rate": sum(s["success_rate"] for s in self.agent_stats.values()) / len(self.agent_stats) if self.agent_stats else 0
        }

        # 生成排名表格
        ranking = self._generate_ranking()

        # 生成洞察
        insights = self.generate_insights()

        # 构建Markdown
        md_content = f"""# 📊 Overseer 监控报告 - {self.today}

**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**报告周期**: 过去24小时

---

## 📈 总体概览

| 指标 | 数值 | 说明 |
|------|------|------|
| 活跃Agent | {summary['total_agents']} | 今日有活动的Agent数量 |
| 总调用次数 | {summary['total_calls']} | 所有Agent调用次数合计 |
| 总Token消耗 | {summary['total_tokens']:,} | 估算总消耗 |
| 平均成功率 | {summary['avg_success_rate']:.1%} | 所有Agent平均 |

---

## 🏆 Agent效能排名

| 排名 | Agent | 效能分 | 成功率 | 等级 | 调用次数 |
|------|-------|--------|--------|------|----------|
"""

        for item in ranking:
            medal = "🥇" if item["rank"] == 1 else "🥈" if item["rank"] == 2 else "🥉" if item["rank"] == 3 else f"{item['rank']}"
            md_content += f"| {medal} | **{item['name']}** | {item['efficiency_score']} | {item['success_rate']:.1%} | {item['grade']} | {item['calls']} |\n"

        md_content += """
**等级说明**:
- 🅰️ A级: 效能分 > 10，成功率 > 90%（优秀）
- 🅱️ B级: 效能分 5-10，成功率 70-90%（良好）
- 🅲️ C级: 效能分 < 5，成功率 < 70%（需优化）

---

## 💡 洞察与建议

"""

        for insight in insights:
            icon = "⚠️" if insight["level"] == "P0" else "🔶" if insight["level"] == "P1" else "✅"
            md_content += f"### {icon} {insight['title']} [{insight['level']}]\n\n"
            md_content += f"**问题**: {insight['description']}\n\n"
            md_content += f"**建议**: {insight['suggestion']}\n\n"

            if "agents" in insight:
                md_content += "**涉及Agent**:\n"
                for agent in insight["agents"]:
                    if "rate" in agent:
                        md_content += f"- {agent['name']}: 成功率 {agent['rate']:.1%}\n"
                    elif "tokens" in agent:
                        md_content += f"- {agent['name']}: {agent['tokens']:,} tokens\n"
                    elif "score" in agent:
                        md_content += f"- {agent['name']}: 效能分 {agent['score']}\n"
                    else:
                        md_content += f"- {agent['name']}\n"
                md_content += "\n"

        md_content += """---

## 📋 Agent详细数据

"""

        for name, stats in sorted(self.agent_stats.items(), key=lambda x: x[1]["efficiency_score"], reverse=True):
            md_content += f"""### {name}

| 指标 | 数值 |
|------|------|
| 调用次数 | {stats['calls']} |
| 成功次数 | {stats['success']} |
| 成功率 | {stats['success_rate']:.1%} |
| 平均耗时 | {stats['avg_duration_ms']:.0f} ms |
| 总Token | {stats['total_tokens']:,} |
| 效能评分 | **{stats['efficiency_score']}** |
| 等级 | {stats['grade']} |
| 常用工具 | {', '.join(stats['tools_used'][:3])} |

"""

        md_content += """---

*🤖 本报告由 Overseer 监控优化师自动生成*
*📅 下次报告时间: 明日18:00*
"""

        # 保存Markdown
        md_path = REPORTS_DIR / f"{self.today}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        print(f"✅ Markdown报告已保存: {md_path}")
        return md_path

    def check_alerts(self) -> List[Dict]:
        """检查告警条件"""
        print("🚨 正在检查告警...")

        alerts = []

        # P0告警：成功率 < 50%
        for name, stats in self.agent_stats.items():
            if stats["success_rate"] < 0.5:
                alerts.append({
                    "level": "P0",
                    "agent": name,
                    "message": f"{name} 成功率仅 {stats['success_rate']:.1%}，需要立即关注",
                    "action": "检查错误日志，考虑暂停该Agent"
                })

        if alerts:
            print(f"⚠️ 发现 {len(alerts)} 个P0告警")
        else:
            print("✅ 无P0告警")

        return alerts

    async def send_notifications(self, alerts: List[Dict]):
        """发送告警通知"""
        if not alerts:
            return

        print("📤 正在发送告警通知...")

        # 构建通知消息
        message = "🚨 **Overseer 紧急告警**\n\n"
        for alert in alerts:
            message += f"**[{alert['level']}]** {alert['message']}\n"
            message += f"建议: {alert['action']}\n\n"

        # 实际调用message工具发送通知
        # 这里先打印到控制台
        print(message)

        # 后续可以调用：
        # await message({"action": "send", "message": message})

    async def run(self):
        """执行完整监控流程"""
        print(f"\n{'='*60}")
        print(f"🎯 Overseer 监控优化师 v1.0")
        print(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        try:
            # 1. 采集数据
            sessions = await self.collect_sessions()

            # 2. 分析数据
            self.analyze_sessions(sessions)

            # 3. 生成报告
            json_path = self.generate_json_report()
            md_path = self.generate_markdown_report()

            # 4. 检查告警
            alerts = self.check_alerts()
            await self.send_notifications(alerts)

            # 5. 记录执行日志
            execution_log = {
                "timestamp": datetime.now().isoformat(),
                "status": "success",
                "sessions_processed": len(sessions),
                "agents_analyzed": len(self.agent_stats),
                "alerts_generated": len(alerts),
                "outputs": {
                    "json": str(json_path),
                    "markdown": str(md_path)
                }
            }

            log_path = DATA_DIR / "execution.log"
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(execution_log) + '\n')

            print(f"\n{'='*60}")
            print(f"✅ Overseer 执行完成")
            print(f"📊 处理 {len(sessions)} 条会话，{len(self.agent_stats)} 个Agent")
            print(f"📝 报告: {json_path.name}")
            print(f"{'='*60}\n")

            return {
                "status": "success",
                "json_report": str(json_path),
                "markdown_report": str(md_path),
                "alerts": alerts
            }

        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}


async def main():
    """入口函数"""
    overseer = Overseer()
    result = await overseer.run()
    return result


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result["status"] == "success" else 1)
