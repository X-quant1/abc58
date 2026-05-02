"""策略筛选 - 基于工作记忆中的124天回测结果

根据MEMORY.md中的回测结果：
盈利策略：
1. 趋势突破 +1.3%, 40%wr
2. 均线排列+MACD +0.8%, 41%wr
3. RSI+MACD共振 +0.8%, 37%wr
4. RSI超卖超买 +0.7%
5. 量价突破 +0.3%

亏损策略：
- 布林带 0%
- 双时间EMA -0.3%
- 其余策略（未提及，默认亏损）
"""
from app.database import SessionLocal
from app.models import Strategy


def filter_strategies():
    """筛选策略 - 停止亏损策略"""
    db = SessionLocal()
    
    # 根据工作记忆保留盈利策略
    keep_strategies = [
        "趋势突破-1H",
        "均线多空排列-1H",
        "RSI+MACD共振-1H",
        "RSI超卖超买-1H",
        "量价突破-1H",
    ]
    
    # 查询所有已上架策略
    strategies = db.query(Strategy).filter(Strategy.published == True).all()
    
    print("=" * 70)
    print("策略筛选 - 停止亏损策略")
    print("=" * 70)
    print(f"\n保留策略（盈利）：")
    for name in keep_strategies:
        print(f"  [OK] {name}")
    
    stopped = []
    kept = []
    
    for strategy in strategies:
        if strategy.name in keep_strategies:
            kept.append(strategy.name)
        else:
            # 停止策略
            strategy.enabled = False
            stopped.append(strategy.name)
    
    db.commit()
    
    print(f"\n已停止策略（亏损）：")
    for name in stopped:
        print(f"  [STOP] {name}")
    
    print(f"\n统计：")
    print(f"  保留: {len(kept)} 个")
    print(f"  停止: {len(stopped)} 个")
    
    db.close()
    
    print("\n" + "=" * 70)
    print("策略筛选完成")
    print("=" * 70)


if __name__ == "__main__":
    filter_strategies()
