"""AI分析服务 - 多模型协作系统"""
import json
from pathlib import Path
from typing import Optional
import requests

# 配置文件路径
AI_CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "ai_config.json"

# 默认配置模板
DEFAULT_CONFIG = {
    "analysts": {
        "aggressive": {
            "name": "激进派",
            "emoji": "🚀",
            "role_desc": "你是一个激进的分析师，偏向做多，看重趋势动能，敢于追涨。分析时重点关注：突破信号、动能指标、上涨空间。给出明确的开多/加仓建议。",
            "api_key": "",
            "base_url": "",
            "model": "",
        },
        "conservative": {
            "name": "稳健派",
            "emoji": "🛡️",
            "role_desc": "你是一个稳健的分析师，风险优先，强调止损，谨慎入场。分析时重点关注：支撑压力、风险收益比、止损位。给出明确的风险提示和保守建议。",
            "api_key": "",
            "base_url": "",
            "model": "",
        },
        "technical": {
            "name": "技术派",
            "emoji": "📊",
            "role_desc": "你是一个技术分析专家，纯指标导向，关注均线、形态、量价关系。分析时重点关注：K线形态、均线系统、技术指标背离。给出纯技术面的判断。",
            "api_key": "",
            "base_url": "",
            "model": "",
        },
    },
    "judge": {
        "name": "裁决者",
        "emoji": "⚖️",
        "role_desc": "你是投资决策主持人，需要综合所有分析师的观点做出最终判断。阅读所有分析师的观点后，分析：1)多空投票比例 2)主要分歧点 3)共识观点 4)最终操作建议（做多/做空/观望）+ 理由 + 建议入场价和止损位。",
        "api_key": "",
        "base_url": "",
        "model": "",
    },
    "quick_analysis": {
        "name": "快速分析",
        "role_desc": "你是专业的BTC行情分析师，根据当前市场数据给出简洁有力的判断。输出格式：【观点】50字内分析【判断】做多/做空/观望【入场】XXXXX【止损】XXXXX【止盈】XXXXX。",
        "api_key": "",
        "base_url": "",
        "model": "",
    },
}


def _load_ai_config() -> dict:
    """加载AI配置"""
    if AI_CONFIG_FILE.exists():
        try:
            with open(AI_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并默认配置（新增字段自动补全）
            merged = json.loads(json.dumps(DEFAULT_CONFIG))
            for key in ["analysts", "judge", "quick_analysis"]:
                if key in saved:
                    if key == "analysts":
                        for akey in merged["analysts"]:
                            if akey in saved["analysts"]:
                                merged["analysts"][akey].update(saved["analysts"][akey])
                    else:
                        merged[key].update(saved[key])
            return merged
        except Exception:
            pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def _save_ai_config(data: dict):
    """保存AI配置"""
    AI_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(AI_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_ai_config() -> dict:
    """获取当前AI配置（供外部调用）"""
    return _load_ai_config()


def update_ai_config(config: dict):
    """更新AI配置（整体更新）"""
    _save_ai_config(config)


def is_analyst_configured(analyst_key: str) -> bool:
    """检查指定分析师是否已配置"""
    cfg = _load_ai_config()
    a = cfg.get("analysts", {}).get(analyst_key, {})
    return bool(a.get("api_key") and a.get("base_url") and a.get("model"))


def is_judge_configured() -> bool:
    """检查裁决者是否已配置"""
    cfg = _load_ai_config()
    j = cfg.get("judge", {})
    return bool(j.get("api_key") and j.get("base_url") and j.get("model"))


def get_configured_analysts() -> list:
    """获取已配置的分析师列表"""
    cfg = _load_ai_config()
    result = []
    for key, a in cfg.get("analysts", {}).items():
        if a.get("api_key") and a.get("base_url") and a.get("model"):
            result.append(key)
    return result


def _build_url(base_url: str) -> str:
    """智能构建API URL"""
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def call_llm_stream(
    api_key: str,
    base_url: str,
    model: str,
    messages: list,
    timeout: float = 30.0,
):
    """
    流式调用LLM（OpenAI兼容格式）

    Yields:
        str: 逐块文本片段
    """
    url = _build_url(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
        "max_tokens": 2048,  # 增加token限制支持完整输出
    }

    resp = requests.post(url, json=payload, headers=headers, stream=True, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        line = line.strip()
        if line.startswith("data: "):
            data_str = line[6:]
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                # 分别处理reasoning和content
                reasoning = delta.get("reasoning_content", "")
                content = delta.get("content", "")
                if reasoning or content:
                    yield (reasoning, content)
            except (json.JSONDecodeError, IndexError, KeyError):
                continue


def call_analyst(analyst_key: str, market_prompt: str, timeout: float = 25.0, other_opinions: str = ""):
    """
    调用指定分析师

    Args:
        analyst_key: aggressive / conservative / technical
        market_prompt: 市场数据提示词
        timeout: 超时秒数
        other_opinions: 其他分析师观点（用于辩论）

    Yields:
        str: 分析师观点片段
    """
    cfg = _load_ai_config()
    a = cfg.get("analysts", {}).get(analyst_key, {})

    if not a.get("api_key") or not a.get("base_url") or not a.get("model"):
        yield f"[{a.get('name', analyst_key)}] 未配置，跳过"
        return

    messages = [
        {"role": "system", "content": a["role_desc"]},
        {"role": "user", "content": market_prompt},
    ]

    # 如果有其他分析师观点，添加辩论提示
    if other_opinions:
        debate_prompt = f"""

【其他分析师观点】
{other_opinions}

请基于以上观点，发表你的看法（支持/反对/补充），并给出最终建议。如果不同意，请指出逻辑漏洞。"""
        messages.append({"role": "user", "content": debate_prompt})

    try:
        # 收集完整响应
        full_reasoning = ""
        full_content = ""
        found_format = False
        format_buffer = ""

        for chunk in call_llm_stream(a["api_key"], a["base_url"], a["model"], messages, timeout):
            # call_llm_stream现在返回(reasoning, content)元组
            if isinstance(chunk, tuple):
                reasoning, content = chunk
                if reasoning:
                    full_reasoning += reasoning
                    # 在reasoning中检测格式化输出
                    if "【观点】" in reasoning:
                        found_format = True
                    if found_format:
                        format_buffer += reasoning
                if content:
                    full_content += content
                    yield content
            else:
                # 兼容旧格式
                full_content += chunk
                yield chunk

        # 如果content为空，但reasoning中有格式化输出，补充输出
        if not full_content and format_buffer:
            # 提取【观点】开始的格式化输出
            import re
            match = re.search(r'【观点】.*', format_buffer, re.DOTALL)
            if match:
                yield match.group(0)

    except Exception as e:
        yield f"[调用失败: {str(e)[:50]}]"


def call_quick_analysis(market_prompt: str, timeout: float = 30.0):
    """
    调用快速分析API

    Args:
        market_prompt: 市场数据提示词
        timeout: 超时秒数

    Yields:
        str: 分析结果片段
    """
    cfg = _load_ai_config()
    qa = cfg.get("quick_analysis", {})

    if not qa.get("api_key") or not qa.get("base_url") or not qa.get("model"):
        yield "[快速分析未配置，请先在管理后台配置API]"
        return

    messages = [
        {"role": "system", "content": qa.get("role_desc", "你是专业的BTC行情分析师。")},
        {"role": "user", "content": market_prompt},
    ]

    try:
        for chunk in call_llm_stream(qa["api_key"], qa["base_url"], qa["model"], messages, timeout):
            yield chunk
    except Exception as e:
        yield f"[调用失败: {str(e)[:50]}]"


def call_judge(analyst_opinions: dict, market_prompt: str, timeout: float = 30.0):
    """
    调用裁决者综合判断

    Args:
        analyst_opinions: {"aggressive": "观点1", "conservative": "观点2", ...}
        market_prompt: 市场数据提示词
        timeout: 超时秒数

    Yields:
        str: 裁决结论片段
    """
    cfg = _load_ai_config()
    j = cfg.get("judge", {})

    # 如果裁决者未配置，使用第一个已配置的分析师
    if not j.get("api_key") or not j.get("base_url") or not j.get("model"):
        analysts = get_configured_analysts()
        if analysts:
            j = cfg["analysts"][analysts[0]]
        else:
            yield "[裁决者未配置]"
            return

    # 构建裁决提示
    opinions_text = ""
    for key, opinion in analyst_opinions.items():
        name = cfg["analysts"].get(key, {}).get("name", key)
        opinions_text += f"\n【{name}】\n{opinion}\n"

    judge_prompt = f"""{market_prompt}

═══════════════════════════════════════
以下是各分析师的观点：

{opinions_text}
═══════════════════════════════════════

请综合以上分析师的观点，做出最终判断：
1. 多空投票比例
2. 主要分歧点
3. 共识观点
4. 最终操作建议（明确给出：做多/做空/观望 + 入场价 + 止损位 + 理由）"""

    messages = [
        {"role": "system", "content": j["role_desc"]},
        {"role": "user", "content": judge_prompt},
    ]

    try:
        for chunk in call_llm_stream(j["api_key"], j["base_url"], j["model"], messages, timeout):
            yield chunk
    except Exception as e:
        yield f"[裁决调用失败: {str(e)[:50]}]"


def get_historical_context() -> str:
    """获取历史判断表现统计"""
    from app.database import SessionLocal
    from app.models import AiJudgeRecord

    db = SessionLocal()
    try:
        # 查询最近20条已验证记录
        records = db.query(AiJudgeRecord)\
            .filter(AiJudgeRecord.verified == True)\
            .order_by(AiJudgeRecord.created_at.desc())\
            .limit(20)\
            .all()

        if not records:
            return ""

        total = len(records)
        correct = sum(1 for r in records if r.result == "correct")
        wrong = total - correct
        win_rate = (correct / total * 100) if total > 0 else 0

        # 统计多空胜率
        long_records = [r for r in records if r.direction == "long"]
        short_records = [r for r in records if r.direction == "short"]

        long_wins = sum(1 for r in long_records if r.result == "correct")
        short_wins = sum(1 for r in short_records if r.result == "correct")

        long_rate = (long_wins / len(long_records) * 100) if long_records else 0
        short_rate = (short_wins / len(short_records) * 100) if short_records else 0

        # 找最近3次错误案例
        errors = [r for r in records if r.result == "wrong"][:3]
        error_reasons = []
        if errors:
            error_reasons.append("最近失败案例：")
            for i, e in enumerate(errors, 1):
                error_reasons.append(f"{i}. {e.direction} @{e.entry_price:.0f} - {e.reason[:30]}...")

        context = f"""【历史表现参考】
• 总胜率：{win_rate:.0f}%（{correct}胜{wrong}负，共{total}次）
• 做多胜率：{long_rate:.0f}%（{long_wins}/{len(long_records)}）
• 做空胜率：{short_rate:.0f}%（{short_wins}/{len(short_records)}）
{chr(10).join(error_reasons) if error_reasons else '暂无失败案例'}

请根据历史表现调整本次判断策略！"""

        return context
    except Exception as e:
        print(f"[AI] Get historical context error: {e}")
        return ""
    finally:
        db.close()


def build_market_prompt(market_data: dict, historical_context: str = "") -> str:
    """构建市场数据提示词（增强版）"""
    def _num(val, default=0):
        if isinstance(val, dict):
            return val.get("value", default) or default
        return val if val is not None else default

    regime = market_data.get("regime", "ranging")
    score = market_data.get("score", 0) or 0
    details = market_data.get("details", {}) or {}
    btc_price = _num(market_data.get("btc_price"), 0)
    btc_change = _num(market_data.get("btc_change_24h"), 0)
    funding = _num(market_data.get("funding_rate"), 0)
    fear_greed = market_data.get("fear_greed", 50) or 50
    direction = market_data.get("trend_direction", "")
    regime_label = market_data.get("regime_label", "震荡")

    adx = _num(details.get("adx"), 0)
    vol_ratio = _num(details.get("vol_ratio"), 0)
    deviation = _num(details.get("deviation"), 0)
    atr_change = _num(details.get("atr_change"), 0)

    # 计算RSI (简化版，基于ADX和波动率推算)
    rsi_estimate = min(100, max(0, 50 + (adx - 20) * 1.5))

    # 计算支撑压力位
    support = btc_price * 0.98 if direction == "up" else btc_price * 0.97
    resistance = btc_price * 1.02 if direction == "up" else btc_price * 1.03

    prompt = f"""【市场全景分析】

📊 当前状态：{regime_label}（趋势评分 {round(score*100)}分）
💰 BTC价格：${btc_price:,.0f}（24h {btc_change:+.2f}%）
📈 趋势方向：{'上涨' if direction == 'up' else '下跌' if direction == 'down' else '横盘'}

【关键技术指标】
• ADX趋势强度：{adx:.1f} {'(强趋势)' if adx > 25 else '(弱趋势/震荡)'}
• RSI(14)：{rsi_estimate:.0f} {'(超买)' if rsi_estimate > 70 else '(超卖)' if rsi_estimate < 30 else '(中性)'}
• 波动率比：{vol_ratio:.2f} {'(高波动)' if vol_ratio > 1.3 else '(低波动)'}
• 成交量能：{'放量' if vol_ratio > 1.2 else '缩量' if vol_ratio < 0.8 else '正常'}
• 均线偏离：{deviation:+.2f}%

【资金面】
• 资金费率：{funding*100:.4f}% {'(多头付费)' if funding > 0 else '(空头付费)' if funding < 0 else '(平衡)'}
• 恐惧贪婪：{fear_greed} {'(贪婪区)' if fear_greed > 60 else '(恐惧区)' if fear_greed < 40 else '(中性)'}

【关键价位】
• 支撑位：${support:,.0f}
• 压力位：${resistance:,.0f}
• 当前价：${btc_price:,.0f}

{historical_context}

【输出要求】
必须明确回答：
1. 判断：做多/做空/观望（三选一）
2. 入场价：具体数字
3. 止损价：具体数字
4. 止盈价：至少1个目标位
5. 理由：不超过30字

禁止模糊表述！"""

    return prompt
