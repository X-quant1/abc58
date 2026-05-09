"""AI自动分析定时任务"""
import threading
import time
import asyncio
import re
from datetime import datetime, timedelta


def _save_judge_record(db, judge_content, period, current_price):
    """从裁决内容中提取判断并保存记录"""
    from app.models import AiJudgeRecord
    
    # 解析判断方向
    direction = "hold"
    if "做多" in judge_content or "开多" in judge_content or "买入" in judge_content:
        direction = "long"
    elif "做空" in judge_content or "开空" in judge_content or "卖出" in judge_content:
        direction = "short"
    
    # 解析入场价
    entry_price = None
    price_patterns = [
        r'入场价[：:]\s*([\d,]+(?:\.\d+)?)',
        r'建议入场[：:]\s*([\d,]+(?:\.\d+)?)',
        r'入场价位[：:]\s*([\d,]+(?:\.\d+)?)',
    ]
    for pattern in price_patterns:
        match = re.search(pattern, judge_content)
        if match:
            try:
                entry_price = float(match.group(1).replace(',', ''))
                break
            except:
                pass
    
    # 如果没找到入场价，用当前价格
    if not entry_price and current_price:
        entry_price = float(current_price)
    
    # 解析止损位
    stop_loss = None
    sl_patterns = [
        r'止损[：:]\s*([\d,]+(?:\.\d+)?)',
        r'止损位[：:]\s*([\d,]+(?:\.\d+)?)',
    ]
    for pattern in sl_patterns:
        match = re.search(pattern, judge_content)
        if match:
            try:
                stop_loss = float(match.group(1).replace(',', ''))
                break
            except:
                pass
    
    # 如果是观望，不保存记录
    if direction == "hold":
        return
    
    # 限制止损止盈在300-600点范围
    if entry_price and stop_loss:
        diff = abs(entry_price - stop_loss)
        if diff < 300:
            ratio = 300 / diff if diff > 0 else 1
            stop_loss = round(entry_price + (stop_loss - entry_price) * ratio)
            print(f"[AutoAnalysis] Stop loss clamped to 300pts: {stop_loss}")
        elif diff > 600:
            ratio = 600 / diff
            stop_loss = round(entry_price + (stop_loss - entry_price) * ratio)
            print(f"[AutoAnalysis] Stop loss clamped to 600pts: {stop_loss}")
    
    # 提取判断理由
    reason = judge_content[:200] if len(judge_content) > 200 else judge_content
    
    # 保存到数据库
    try:
        record = AiJudgeRecord(
            period=period,
            direction=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            reason=reason,
            verify_after=datetime.now() + timedelta(hours=3),
            verified=False,
            result="pending"
        )
        db.add(record)
        db.commit()
        print(f"[AutoAnalysis] Saved judge record: {direction} @ {entry_price}, SL: {stop_loss}")
    except Exception as e:
        db.rollback()
        print(f"[AutoAnalysis] Save judge record error: {e}")


def start_auto_analysis():
    """启动后台定时任务：每30分钟自动调用AI分析"""
    
    def _run_periodically():
        while True:
            try:
                # 计算下一个整点或半点的时间
                now = datetime.now()
                current_minute = now.minute
                
                # 如果当前分钟 < 30，下次执行时间是30分
                # 如果当前分钟 >= 30，下次执行时间是下一个小时的0分
                if current_minute < 30:
                    next_minute = 30
                    next_hour = now.hour
                else:
                    next_minute = 0
                    next_hour = (now.hour + 1) % 24
                
                # 计算等待秒数
                next_time = now.replace(minute=next_minute, second=0, microsecond=0)
                if next_hour < now.hour:  # 跨天
                    next_time = next_time.replace(hour=next_hour)
                
                wait_seconds = (next_time - now).total_seconds()
                if wait_seconds < 0:
                    wait_seconds += 3600  # 加一个小时
                
                print(f"[AutoAnalysis] Next run at {next_time.strftime('%H:%M')}, waiting {int(wait_seconds)}s...")
                time.sleep(wait_seconds)
                
                # 执行AI分析
                print(f"[AutoAnalysis] Running auto analysis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                asyncio.run(_run_ai_analysis())
                
            except Exception as e:
                print(f"[AutoAnalysis] Error: {e}")
                time.sleep(60)  # 出错后等待1分钟重试
    
    # 启动后台线程
    thread = threading.Thread(target=_run_periodically, daemon=True, name="AutoAnalysisThread")
    thread.start()


async def _run_ai_analysis():
    """执行一次AI团队分析"""
    try:
        from app.routers.dashboard import get_market_regime
        from app.services.ai_analysis import (
            get_configured_analysts, call_analyst, call_judge, build_market_prompt,
            get_historical_context,
        )
        from app.database import SessionLocal
        from app.models import AiChatHistory, AiJudgeRecord
        import json
        
        # 检查是否有配置的分析师
        configured = get_configured_analysts()
        if not configured:
            print("[AutoAnalysis] No analysts configured, skipping")
            return
        
        # 获取市场数据
        regime_data = await get_market_regime()
        
        # 获取历史学习上下文
        historical_context = get_historical_context()
        
        # 构建提示词
        market_prompt = build_market_prompt(regime_data, historical_context)
        
        # 并行调用所有分析师（第一轮：独立分析）
        opinions = {}
        for analyst_key in configured:
            try:
                full_content = ""
                for chunk in call_analyst(analyst_key, market_prompt, timeout=30.0):
                    full_content += chunk
                opinions[analyst_key] = full_content
            except Exception as e:
                print(f"[AutoAnalysis] Analyst {analyst_key} error: {e}")
                opinions[analyst_key] = f"分析失败: {str(e)}"

        # 第二轮：辩论环节（每个分析师看到其他人观点后补充评论）
        print("[AutoAnalysis] Starting debate round...")
        debate_opinions = {}
        for analyst_key in configured:
            try:
                # 构建其他分析师观点
                other_views = "\n\n".join([
                    f"【{opinions.get(k, '')[:100]}...】"
                    for k in configured if k != analyst_key
                ])

                full_content = ""
                for chunk in call_analyst(analyst_key, market_prompt, timeout=20.0, other_opinions=other_views):
                    full_content += chunk

                # 只保留辩论补充的关键观点，不重复原始观点
                debate_opinions[analyst_key] = opinions[analyst_key] + "\n\n【辩论观点】" + full_content[:200]
            except Exception as e:
                print(f"[AutoAnalysis] Debate {analyst_key} error: {e}")
                debate_opinions[analyst_key] = opinions[analyst_key]  # 失败则用原始观点

        # 使用辩论后的观点
        final_opinions = debate_opinions if any(debate_opinions.values()) else opinions

        # 调用裁决者
        judge_content = ""
        try:
            for chunk in call_judge(final_opinions, market_prompt, timeout=35.0):
                judge_content += chunk
        except Exception as e:
            print(f"[AutoAnalysis] Judge error: {e}")
            judge_content = f"裁决失败: {str(e)}"

        # 保存到数据库
        db = SessionLocal()
        try:
            now = datetime.now()
            minute = now.minute
            period = "1h" if minute < 30 else "30m"

            history = AiChatHistory(
                period=period,
                opinions=json.dumps(final_opinions, ensure_ascii=False),
                judge=judge_content,
                market_data=json.dumps(regime_data, ensure_ascii=False),
            )
            db.add(history)
            db.commit()
            print(f"[AutoAnalysis] Analysis saved to history (id={history.id})")

            # 保存判断记录
            _save_judge_record(db, judge_content, period, regime_data.get("btc_price"))
        except Exception as e:
            print(f"[AutoAnalysis] Save error: {e}")
            db.rollback()
        finally:
            db.close()
            
    except Exception as e:
        print(f"[AutoAnalysis] Run error: {e}")
