"""策略筛选 - 基于历史回测结果

根据124天回测结果筛选策略：
1. 停止长期亏损的策略
2. 只保留表现好的策略
"""
import json
from app.database import SessionLocal
from app.models import Strategy, BacktestResult


def analyze_strategy_performance():
    """分析策略历史表现"""
    db = SessionLocal()
    
    # 查询所有已上架策略
    strategies = db.query(Strategy).filter(Strategy.published == True).all()
    
    print("=" * 70)
    print("策略筛选分析")
    print("=" * 70)
    
    results = []
    
    for strategy in strategies:
        # 查询最近的回测结果
        backtest = db.query(BacktestResult).filter(
            BacktestResult.strategy_type == strategy.strategy_type
        ).order_by(BacktestResult.created_at.desc()).first()
        
        if backtest:
            result_data = json.loads(backtest.result) if isinstance(backtest.result, str) else backtest.result
            
            total_return = result_data.get("total_return", 0)
            trade_count = result_data.get("trade_count", 0)
            win_rate = result_data.get("win_rate", 0)
            max_drawdown = result_data.get("max_drawdown", 0)
            sharpe = result_data.get("sharpe_ratio", 0)
            
            results.append({
                "id": strategy.id,
                "name": strategy.name,
                "type": strategy.strategy_type,
                "total_return": total_return,
                "trade_count": trade_count,
                "win_rate": win_rate,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe,
                "enabled": strategy.enabled,
            })
            
            print(f"\n{strategy.name}")
            print(f"  收益率: {total_return:.2f}%")
            print(f"  交易次数: {trade_count}")
            print(f"  胜率: {win_rate:.1f}%")
            print(f"  最大回撤: {max_drawdown:.2f}%")
            print(f"  夏普比率: {sharpe:.2f}")
            print(f"  状态: {'运行中' if strategy.enabled else '已停止'}")
        else:
            print(f"\n{strategy.name}")
            print(f"  无回测数据")
    
    # 按收益率排序
    results.sort(key=lambda x: x["total_return"], reverse=True)
    
    print("\n" + "=" * 70)
    print("策略排名（按收益率）")
    print("=" * 70)
    
    print(f"\n{'排名':<4} {'策略名称':<25} {'收益率':>10} {'胜率':>8} {'夏普':>8} {'建议':<10}")
    print("-" * 70)
    
    for i, r in enumerate(results, 1):
        if r["total_return"] > 0:
            suggest = "✅ 保留"
        elif r["total_return"] > -0.5:
            suggest = "⚠️ 观察"
        else:
            suggest = "❌ 停止"
        
        print(f"{i:<4} {r['name']:<25} {r['total_return']:>9.2f}% {r['win_rate']:>7.1f}% {r['sharpe_ratio']:>8.2f} {suggest:<10}")
    
    # 统计
    profitable = [r for r in results if r["total_return"] > 0]
    need_stop = [r for r in results if r["total_return"] < -0.5]
    
    print(f"\n盈利策略: {len(profitable)}/{len(results)}")
    print(f"建议停止: {len(need_stop)} 个")
    
    if need_stop:
        print("\n建议停止的策略：")
        for r in need_stop:
            print(f"  - {r['name']} (收益率: {r['total_return']:.2f}%)")
    
    db.close()
    
    return results


def stop_losing_strategies():
    """停止亏损策略"""
    db = SessionLocal()
    
    # 根据工作记忆中的124天回测结果
    # 盈利策略：趋势突破 +1.3%, 均线排列+MACD +0.8%, RSI+MACD共振 +0.8%, RSI超卖超买 +0.7%, 量价突破 +0.3%
    # 亏损策略：布林带 0%, 双时间EMA -0.3%, 其余策略
    
    keep_strategies = [
        "趋势突破-1H",
        "均线多空排列-1H",
        "RSI+MACD共振-1H",
        "RSI超卖超买-1H",
        "量价突破-1H",
    ]
    
    strategies = db.query(Strategy).filter(Strategy.published == True).all()
    
    stopped = []
    kept = []
    
    for strategy in strategies:
        if strategy.name not in keep_strategies:
            # 停止策略
            strategy.enabled = False
            stopped.append(strategy.name)
        else:
            kept.append(strategy.name)
    
    db.commit()
    
    print("\n" + "=" * 70)
    print("策略筛选完成")
    print("=" * 70)
    print(f"\n保留策略 ({len(kept)} 个):")
    for name in kept:
        print(f"  ✅ {name}")
    
    print(f"\n已停止策略 ({len(stopped)} 个):")
    for name in stopped:
        print(f"  ❌ {name}")
    
    db.close()


if __name__ == "__main__":
    # 先分析
    print("\n[步骤1] 分析策略表现...")
    results = analyze_strategy_performance()
    
    # 询问是否执行
    print("\n" + "=" * 70)
    user_input = input("\n是否停止亏损策略？(y/n): ").strip().lower()
    
    if user_input == "y":
        print("\n[步骤2] 停止亏损策略...")
        stop_losing_strategies()
    else:
        print("\n已取消操作")
