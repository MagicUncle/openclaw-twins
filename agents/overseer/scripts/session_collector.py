#!/usr/bin/env python3
"""
SessionCollector - OpenClaw真实会话数据采集器 v2.0
支持多种数据源：API调用、本地日志、混合模式
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import asyncio

WORKSPACE = Path("/Users/magicuncle/.openclaw/workspace")
SESSIONS_DIR = WORKSPACE / "sessions"
AGENTS_DIR = WORKSPACE / "agents"


class SessionCollector:
    """会话数据采集器"""
    
    def __init__(self):
        self.session_data = []
        self.agent_stats = {}
        
    async def collect_from_api(self, hours: int = 24) -> List[Dict]:
        """通过OpenClaw API获取会话数据"""
        print("🔌 尝试通过API获取会话数据...")
        
        sessions = []
        
        try:
            # 使用sessions_list获取活跃会话
            # 注意：这里模拟API调用，实际部署时需要使用正确的OpenClaw API
            
            # 方法1: 通过shell调用openclaw命令
            result = subprocess.run(
                ["openclaw", "sessions", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                session_list = json.loads(result.stdout)
                print(f"  ✓ 获取到 {len(session_list)} 个活跃会话")
                
                # 获取每个会话的详细历史
                for session_meta in session_list:
                    session_key = session_meta.get("key")
                    if session_key:
                        history = await self._get_session_history(session_key)
                        if history:
                            sessions.extend(history)
            else:
                print(f"  ⚠️ API调用失败: {result.stderr}")
                
        except Exception as e:
            print(f"  ⚠️ API获取失败: {e}")
        
        return sessions
    
    async def _get_session_history(self, session_key: str) -> Optional[List[Dict]]:
        """获取单个会话的历史"""
        try:
            result = subprocess.run(
                ["openclaw", "sessions", "history", session_key, "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            
        except Exception as e:
            print(f"  ⚠️ 获取会话历史失败 {session_key}: {e}")
        
        return None
    
    def collect_from_files(self, hours: int = 24) -> List[Dict]:
        """从本地日志文件收集会话数据"""
        print("📁 从本地日志文件收集数据...")
        
        sessions = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 扫描多个可能的日志位置
        log_paths = [
            WORKSPACE / "sessions",
            WORKSPACE / "logs",
            WORKSPACE / ".openclaw" / "sessions",
            Path.home() / ".openclaw" / "sessions",
        ]
        
        for log_dir in log_paths:
            if not log_dir.exists():
                continue
            
            print(f"  🔍 扫描: {log_dir}")
            
            # 查找.jsonl文件
            for jsonl_file in log_dir.rglob("*.jsonl"):
                try:
                    # 检查文件修改时间
                    mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
                    if mtime < cutoff_time:
                        continue
                    
                    # 读取文件
                    file_sessions = self._parse_jsonl(jsonl_file, cutoff_time)
                    sessions.extend(file_sessions)
                    
                except Exception as e:
                    print(f"    ⚠️ 读取失败 {jsonl_file.name}: {e}")
            
            # 查找.json文件
            for json_file in log_dir.rglob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
                    if mtime < cutoff_time:
                        continue
                    
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            sessions.extend(data)
                        elif isinstance(data, dict):
                            sessions.append(data)
                            
                except Exception as e:
                    print(f"    ⚠️ 读取失败 {json_file.name}: {e}")
        
        print(f"  ✓ 从文件收集到 {len(sessions)} 条记录")
        return sessions
    
    def _parse_jsonl(self, file_path: Path, cutoff_time: datetime) -> List[Dict]:
        """解析JSONL文件"""
        sessions = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    
                    # 时间过滤
                    if 'timestamp' in record:
                        try:
                            ts = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00'))
                            if ts < cutoff_time:
                                continue
                        except:
                            pass
                    
                    # 添加元数据
                    record['_source_file'] = file_path.name
                    record['_line_num'] = line_num
                    
                    sessions.append(record)
                    
                except json.JSONDecodeError:
                    continue
        
        return sessions
    
    def collect_from_agent_logs(self, hours: int = 24) -> List[Dict]:
        """从各Agent的日志目录收集"""
        print("🤖 从Agent日志收集数据...")
        
        sessions = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # OpenClaw原生Agent路径（在用户目录下）
        OPENCLAW_AGENTS_DIR = Path.home() / ".openclaw" / "agents"
        
        if OPENCLAW_AGENTS_DIR.exists():
            for agent_dir in OPENCLAW_AGENTS_DIR.iterdir():
                if not agent_dir.is_dir():
                    continue
                
                # 检查Agent的sessions目录
                agent_sessions = agent_dir / "sessions"
                if agent_sessions.exists():
                    jsonl_files = list(agent_sessions.glob("*.jsonl"))
                    
                    if jsonl_files:
                        print(f"    📁 {agent_dir.name}: {len(jsonl_files)} 个日志文件")
                    
                    for log_file in jsonl_files:
                        try:
                            # 跳过.deleted和.reset文件
                            if ".deleted." in log_file.name or ".reset." in log_file.name:
                                continue
                                
                            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                            if mtime < cutoff_time:
                                continue
                            
                            records = self._parse_jsonl(log_file, cutoff_time)
                            
                            # 标记Agent来源
                            for r in records:
                                r['_agent_source'] = agent_dir.name
                            
                            sessions.extend(records)
                            
                            if records:
                                print(f"      ✅ {log_file.name}: {len(records)} 条记录")
                            
                        except Exception as e:
                            print(f"      ⚠️ 读取失败: {e}")
        else:
            print(f"    ⚠️ 原生Agent目录不存在: {OPENCLAW_AGENTS_DIR}")
        
        print(f"  ✓ 从原生Agent日志收集到 {len(sessions)} 条记录")
        return sessions
    
    async def collect_all(self, hours: int = 24, prefer_api: bool = True) -> List[Dict]:
        """采集所有可用数据源"""
        print(f"\n{'='*60}")
        print(f"📊 SessionCollector v2.0")
        print(f"⏱️  采集范围: 过去{hours}小时")
        print(f"{'='*60}\n")
        
        all_sessions = []
        
        # 方法1: API采集（如果可用）
        if prefer_api:
            api_sessions = await self.collect_from_api(hours)
            all_sessions.extend(api_sessions)
        
        # 方法2: 全局日志文件
        file_sessions = self.collect_from_files(hours)
        all_sessions.extend(file_sessions)
        
        # 方法3: Agent特定日志
        agent_sessions = self.collect_from_agent_logs(hours)
        all_sessions.extend(agent_sessions)
        
        # 去重（基于session_id）
        seen_ids = set()
        unique_sessions = []
        
        for s in all_sessions:
            sid = s.get('session_id') or s.get('id') or hash(str(s))
            if sid not in seen_ids:
                seen_ids.add(sid)
                unique_sessions.append(s)
        
        print(f"\n📈 采集汇总:")
        print(f"  - API数据: {len(api_sessions) if prefer_api else 0} 条")
        print(f"  - 全局日志: {len(file_sessions)} 条")
        print(f"  - Agent日志: {len(agent_sessions)} 条")
        print(f"  - 去重后: {len(unique_sessions)} 条")
        
        self.session_data = unique_sessions
        return unique_sessions
    
    def analyze_sessions_v2(self) -> Dict[str, Dict]:
        """增强版会话分析"""
        print("\n🔍 分析会话数据...")
        
        agent_stats = {}
        
        for session in self.session_data:
            # 确定Agent名称
            agent_name = self._extract_agent_name(session)
            
            if agent_name not in agent_stats:
                agent_stats[agent_name] = {
                    "calls": 0,
                    "success": 0,
                    "failures": 0,
                    "total_duration_ms": 0,
                    "total_input_tokens": 0,
                    "total_output_tokens": 0,
                    "tools_used": {},
                    "models_used": {},
                    "error_types": {},
                    "hourly_distribution": {},
                    "response_times": []
                }
            
            stats = agent_stats[agent_name]
            stats["calls"] += 1
            
            # 成功/失败判定
            if self._is_success(session):
                stats["success"] += 1
            else:
                stats["failures"] += 1
                error_type = self._extract_error_type(session)
                stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1
            
            # 时长统计
            duration = self._extract_duration(session)
            stats["total_duration_ms"] += duration
            stats["response_times"].append(duration)
            
            # Token统计
            input_tokens, output_tokens = self._extract_tokens(session)
            stats["total_input_tokens"] += input_tokens
            stats["total_output_tokens"] += output_tokens
            
            # 工具使用统计
            tools = self._extract_tools(session)
            for tool in tools:
                stats["tools_used"][tool] = stats["tools_used"].get(tool, 0) + 1
            
            # 模型使用统计
            model = self._extract_model(session)
            if model:
                stats["models_used"][model] = stats["models_used"].get(model, 0) + 1
            
            # 时间分布
            hour = self._extract_hour(session)
            if hour is not None:
                stats["hourly_distribution"][hour] = stats["hourly_distribution"].get(hour, 0) + 1
        
        # 计算派生指标
        for agent, stats in agent_stats.items():
            calls = stats["calls"]
            if calls > 0:
                stats["success_rate"] = round(stats["success"] / calls, 3)
                stats["avg_duration_ms"] = round(stats["total_duration_ms"] / calls, 1)
                stats["avg_input_tokens"] = round(stats["total_input_tokens"] / calls, 1)
                stats["avg_output_tokens"] = round(stats["total_output_tokens"] / calls, 1)
                stats["total_tokens"] = stats["total_input_tokens"] + stats["total_output_tokens"]
                
                # 响应时间分位数
                if stats["response_times"]:
                    sorted_times = sorted(stats["response_times"])
                    stats["p50_response_time"] = sorted_times[len(sorted_times) // 2]
                    stats["p95_response_time"] = sorted_times[int(len(sorted_times) * 0.95)]
                
                # 效能评分（增强版）
                token_k = max(stats["total_tokens"] / 1000, 0.1)
                success_weight = stats["success_rate"] ** 2  # 成功率平方加权
                stats["efficiency_score"] = round((calls * success_weight) / token_k, 2)
                
                # 等级评定（更细粒度）
                if stats["efficiency_score"] > 15 and stats["success_rate"] > 0.95:
                    stats["grade"] = "S"
                elif stats["efficiency_score"] > 10 and stats["success_rate"] > 0.9:
                    stats["grade"] = "A"
                elif stats["efficiency_score"] >= 5 and stats["success_rate"] >= 0.75:
                    stats["grade"] = "B"
                elif stats["efficiency_score"] >= 2 and stats["success_rate"] >= 0.6:
                    stats["grade"] = "C"
                else:
                    stats["grade"] = "D"
        
        self.agent_stats = agent_stats
        print(f"✅ 分析了 {len(agent_stats)} 个Agent的数据")
        return agent_stats
    
    # 辅助方法
    def _extract_agent_name(self, session: Dict) -> str:
        """提取Agent名称"""
        # 尝试多个可能的字段
        for key in ['agent', 'agent_name', 'agent_id', 'source', '_agent_source']:
            if key in session:
                return session[key]
        
        # 从会话ID推断
        session_id = session.get('session_id', session.get('id', ''))
        if 'wenyuan' in session_id.lower():
            return 'wenyuan'
        elif 'shangqing' in session_id.lower():
            return 'shangqing'
        
        return 'unknown'
    
    def _is_success(self, session: Dict) -> bool:
        """判断会话是否成功"""
        # 检查显式状态
        if 'status' in session:
            return session['status'] in ['success', 'completed', 'done']
        
        # 检查错误字段
        if 'error' in session and session['error']:
            return False
        if 'errors' in session and session['errors']:
            return False
        
        # 检查result是否存在
        if 'result' in session and session['result']:
            return True
        
        # 默认成功
        return True
    
    def _extract_duration(self, session: Dict) -> int:
        """提取执行时长（毫秒）"""
        # 直接字段
        for key in ['duration_ms', 'duration', 'elapsed_ms', 'time_ms']:
            if key in session:
                return int(session[key])
        
        # 从时间戳计算
        if 'start_time' in session and 'end_time' in session:
            try:
                start = datetime.fromisoformat(session['start_time'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(session['end_time'].replace('Z', '+00:00'))
                return int((end - start).total_seconds() * 1000)
            except:
                pass
        
        return 0
    
    def _extract_tokens(self, session: Dict) -> Tuple[int, int]:
        """提取Token消耗"""
        input_tokens = 0
        output_tokens = 0
        
        # 直接字段
        if 'input_tokens' in session:
            input_tokens = int(session['input_tokens'])
        if 'output_tokens' in session:
            output_tokens = int(session['output_tokens'])
        
        # 嵌套字段
        if 'tokens' in session:
            tokens = session['tokens']
            if isinstance(tokens, dict):
                input_tokens = tokens.get('input', tokens.get('input_tokens', 0))
                output_tokens = tokens.get('output', tokens.get('output_tokens', 0))
        
        # 从usage字段提取
        if 'usage' in session:
            usage = session['usage']
            if isinstance(usage, dict):
                input_tokens = usage.get('prompt_tokens', usage.get('input', 0))
                output_tokens = usage.get('completion_tokens', usage.get('output', 0))
        
        # 估算（如果无准确数据）
        if input_tokens == 0 and 'input' in session:
            text = str(session['input'])
            # 中文按1.5字符/token，英文按4字符/token
            cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            en_chars = len(text) - cn_chars
            input_tokens = int(cn_chars / 1.5 + en_chars / 4)
        
        if output_tokens == 0 and 'output' in session:
            text = str(session['output'])
            cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
            en_chars = len(text) - cn_chars
            output_tokens = int(cn_chars / 1.5 + en_chars / 4)
        
        return input_tokens, output_tokens
    
    def _extract_tools(self, session: Dict) -> List[str]:
        """提取使用的工具"""
        tools = []
        
        # 直接字段
        if 'tools_used' in session:
            if isinstance(session['tools_used'], list):
                tools = session['tools_used']
            elif isinstance(session['tools_used'], str):
                tools = [session['tools_used']]
        
        # 从tool_calls提取
        if 'tool_calls' in session and isinstance(session['tool_calls'], list):
            for call in session['tool_calls']:
                if isinstance(call, dict) and 'name' in call:
                    tools.append(call['name'])
                elif isinstance(call, str):
                    tools.append(call)
        
        return tools
    
    def _extract_model(self, session: Dict) -> Optional[str]:
        """提取使用的模型"""
        for key in ['model', 'model_name', 'llm_model']:
            if key in session:
                return session[key]
        return None
    
    def _extract_error_type(self, session: Dict) -> str:
        """提取错误类型"""
        if 'error' in session:
            error = session['error']
            if isinstance(error, str):
                return error.split(':')[0]
            elif isinstance(error, dict):
                return error.get('type', error.get('code', 'unknown'))
        
        if 'errors' in session and isinstance(session['errors'], list):
            return session['errors'][0] if session['errors'] else 'unknown'
        
        return 'unknown'
    
    def _extract_hour(self, session: Dict) -> Optional[int]:
        """提取小时"""
        for key in ['timestamp', 'start_time', 'created_at', 'time']:
            if key in session:
                try:
                    ts = datetime.fromisoformat(session[key].replace('Z', '+00:00'))
                    return ts.hour
                except:
                    pass
        return None


async def test_collector():
    """测试采集器"""
    collector = SessionCollector()
    
    # 采集数据
    sessions = await collector.collect_all(hours=24, prefer_api=False)
    
    # 分析
    if sessions:
        stats = collector.analyze_sessions_v2()
        
        # 打印结果
        print("\n" + "="*60)
        print("📊 采集结果")
        print("="*60)
        
        for agent, s in sorted(stats.items(), key=lambda x: x[1]['efficiency_score'], reverse=True):
            print(f"\n🤖 {agent}")
            print(f"  调用: {s['calls']} | 成功: {s['success_rate']:.1%} | 效能: {s['efficiency_score']}")
            print(f"  Token: {s['total_tokens']:,} | 等级: {s['grade']}")
            if s['tools_used']:
                print(f"  工具: {', '.join(s['tools_used'].keys())}")
    else:
        print("\n⚠️ 未采集到数据，使用模拟数据测试")
        # 使用模拟数据
        from overseer import Overseer
        overseer = Overseer()
        sessions = overseer._generate_mock_data()
        overseer.analyze_sessions(sessions)
        
        print("\n模拟数据统计:")
        for agent, s in sorted(overseer.agent_stats.items(), key=lambda x: x[1]['efficiency_score'], reverse=True):
            print(f"  {agent}: 效能分={s['efficiency_score']}, 等级={s['grade']}")


if __name__ == "__main__":
    asyncio.run(test_collector())
