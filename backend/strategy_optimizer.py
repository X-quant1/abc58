"""策略参数优化 - 网格搜索最优参数

对4个盈利策略进行参数优化：
1. 趋势突破-1H
2. 均线多空排列-1H
3. RSI+MACD共振-1H
4. RSI超卖超买-1H
"""
import json
import itertools
from datetime import datetime
from app.database import SessionLocal
from app.models import Strategy
from app.services.backtest import BacktestEngine
from app.services.market import market_service


# 回测配置
INITIAL_CAPITAL = 10000
LEVERAGE = 100
SYMBOL = "BTC-USDT-SWAP"
TIMEFRAME = "1h"

# 策略参数网格
PARAM_GRIDS = {
    "trend_break": {
        "ema_period": [14, 21, 28],
        "boll_period": [10, 15, 20],
        "boll_std": [1.5, 2.0, 2.5],
        "vol_ma_period": [10, 15, 20],
    },
    "ma_cross": {
        "fast_period": [5, 7, 10],
        "slow_period": [20, 30, 40],
        "signal_period": [3, 5, 7],
    },
    "rsi_macd": {
        "rsi_period": [6, 9, 12],
        "rsi_overbought": [70, 75, 80],
        "rsi_oversold": [20, 25, 30],
        "macd_fast": [6, 9, 12],
        "macd_slow": [18, 21, 26],
        "macd_signal": [5, 7, 9],
    },
    "rsi": {
        "rsi_period": [6, 9, 12, 14],
        "rsi_overbought": [70, 75, 80],
        "rsi_oversold": [20, 25, 30],
    },
}

# 风控参数（固定）
RISK_PARAMS = {
    "take_profit_pct": 2.0,
    "stop_loss_pct": 0.8,
    "trailing_stop_pct": 0.5,
    "size": 0.01,
}


def get_strategy_type_from_name(name: str) -> str:
    """从策略名称推断策略类型"""
    if "趋势突破" in name or "trend_break" in name:
        return "trend_break"
    elif "均线" in name or "ma_cross" in name:
        return "ma_cross"
    elif "RSI+MACD" in name or "rsi_macd" in name:
        return "rsi_macd"
    elif "RSI" in name or "rsi" in name:
        return "rsi"
    return None


def generate_param_combinations(param_grid: dict) -> list:
    """生成参数组合"""
    keys = param_grid.keys()
    values = param_grid.values()
    combinations = list(itertools.product(*values))
    return [dict(zip(keys, combo)) for combo in combinations]


def optimize_strategy(strategy_id: int, strategy_name: str, strategy_type: str, klines: list):
    """优化单个策略"""
    print(f"\n{'='*70}")
    print(f"优化策略: {strategy_name} ({strategy_type})")
    print(f"{'='*70}")
    
    # 获取参数网格
    param_grid = PARAM_GRIDS.get(strategy_type)
    if not param_grid:
        print(f"[SKIP] 未找到策略 {strategy_type} 的参数网格")
        return None
    
    # 生成参数组合
    combinations = generate_param_combinations(param_grid)
    print(f"[INFO] 参数组合数: {len(combinations)}")
    
    # 运行回测
    engine = BacktestEngine()
    results = []
    
    for i, params in enumerate(combinations, 1):
        # 合并风控参数
        full_params = {**params, **RISK_PARAMS}
        
        # 运行回测
        result = engine.run(
            strategy_type=strategy_type,
            params=full_params,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            klines=klines,
            initial_capital=INITIAL_CAPITAL,
            leverage=LEVERAGE,
            regime_filter=True,
        )
        
        if result.get("ok"):
            total_return = result.get("total_return", 0)
            win_rate = result.get("win_rate", 0)
            trade_count = result.get("trade_count", 0)
            sharpe = result.get("sharpe_ratio", 0)
            
            results.append({
                "params": params,
                "total_return": total_return,
                "win_rate": win_rate,
                "trade_count": trade_count,
                "sharpe_ratio": sharpe,
            })
            
            # 每10个组合打印一次进度
            if i % 10 == 0:
                print(f"[PROGRESS] {i}/{len(combinations)} 完成")
    
    # 按收益率排序
    results.sort(key=lambda x: x["total_return"], reverse=True)
    
    # 打印Top 5结果
    print(f"\nTop 5 参数组合:")
    print(f"{'排名':<4} {'收益率':>10} {'胜率':>8} {'交易次数':>8} {'夏普':>8}")
    print("-" * 70)
    
    for i, r in enumerate(results[:5], 1):
        print(f"{i:<4} {r['total_return']:>9.2f}% {r['win_rate']:>7.1f}% {r['trade_count']:>8} {r['sharpe_ratio']:>8.2f}")
        print(f"     参数: {r['params']}")
    
    # 返回最优参数
    if results:
        best = results[0]
        return {
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "strategy_type": strategy_type,
            "best_params": best["params"],
            "best_return": best["total_return"],
            "best_win_rate": best["win_rate"],
            "best_sharpe": best["sharpe_ratio"],
            "all_results": results[:10],  # 保存Top 10
        }
    
    return None


def main():
    print("=" * 70)
    print("策略参数优化 - 网格搜索")
    print("=" * 70)
    print(f"初始资金: {INITIAL_CAPITAL} USDT")
    print(f"杠杆: {LEVERAGE}X")
    print(f"交易对: {SYMBOL}")
    print(f"周期: {TIMEFRAME}")
    print("=" * 70)
    
    # 获取K线数据
    print("\n[1/3] 获取K线数据...")
    spot_symbol = SYMBOL.replace("-SWAP", "")
    klines = market_service.get_klines(
        symbol=spot_symbol,
        timeframe=TIMEFRAME,
        limit=300,  # 获取最多300根K线
    )
    
    if not klines or len(klines) < 100:
        print(f"[ERROR] K线数据不足: {len(klines) if klines else 0}")
        return
    
    print(f"[OK] 获取到 {len(klines)} 根K线")
    
    # 查询数据库中的策略
    print("\n[2/3] 查询策略...")
    db = SessionLocal()
    strategies = db.query(Strategy).filter(
        Strategy.published == True,
        Strategy.enabled == True
    ).all()
    print(f"[OK] 找到 {len(strategies)} 个启用的策略")
    
    # 优化每个策略
    print("\n[3/3] 优化策略参数...")
    optimization_results = []
    
    for strategy in strategies:
        strategy_type = get_strategy_type_from_name(strategy.name)
        if not strategy_type:
            print(f"[SKIP] {strategy.name} - 无法推断策略类型")
            continue
        
        result = optimize_strategy(
            strategy.id,
            strategy.name,
            strategy_type,
            klines
        )
        
        if result:
            optimization_results.append(result)
    
    # 保存优化结果
    print("\n" + "=" * 70)
    print("优化完成")
    print("=" * 70)
    
    # 生成报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "initial_capital": INITIAL_CAPITAL,
            "leverage": LEVERAGE,
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "klines_count": len(klines),
        },
        "results": optimization_results,
    }
    
    # 保存到文件
    report_file = f"optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n优化报告已保存: {report_file}")
    
    db.close()


if __name__ == "__main__":
    main()
