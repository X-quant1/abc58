"""完整回测优化 - 多周期、多参数、多止盈止损组合

测试配置：
- 杠杆：100X
- 周期：15m, 30m, 1h
- 策略：4个盈利策略
- 止盈止损：多组参数对比
- 移动止盈：不同激活点和回调比例

100X杠杆计算示例：
- 70000点做多，40%止盈 = 70280 (280点)
- 70000点做多，25%止损 = 69825 (175点)
- 移动止盈30%激活 = 70210激活，回调30点 = 70180止盈
- 开1张平仓70210，收益2.1 USDT，收益率30%
- 手续费：挂单0.14 USDT，吃单0.35 USDT
"""
import json
from datetime import datetime
from app.database import SessionLocal
from app.models import Strategy
from app.services.backtest import BacktestEngine
from app.services.market import market_service


# 回测配置
INITIAL_CAPITAL = 10000  # 初始资金 10000 USDT
LEVERAGE = 100  # 100X杠杆
SYMBOL = "BTC-USDT-SWAP"
TIMEFRAMES = ["15m", "30m", "1h"]

# 止盈止损参数组合（100X杠杆）
# TP/SL百分比 = 价格变动百分比 * 杠杆倍数
# 例如：40%止盈 = 价格上涨0.4% = 280点（70000→70280）
TP_SL_COMBINATIONS = [
    # (止盈%, 止损%, 移动止盈激活%, 移动止盈回调%)
    (30, 20, 20, 10),   # 保守型
    (40, 25, 30, 15),   # 平衡型
    (50, 30, 40, 20),   # 激进型
    (60, 35, 50, 25),   # 超激进
]

# 策略参数网格
STRATEGY_PARAMS = {
    "rsi": {
        "rsi_period": [6, 9, 12, 14],
        "rsi_overbought": [70, 75, 80],
        "rsi_oversold": [20, 25, 30],
    },
    "rsi_macd": {
        "rsi_period": [6, 9, 12],
        "macd_fast": [6, 9, 12],
        "macd_slow": [18, 21, 26],
        "macd_signal": [5, 7, 9],
    },
    "ma_ribbon": {
        "ma_periods": ["3,7,13,21", "5,10,20,30", "7,14,21,28"],
    },
    "vol_break": {
        "vol_ma_period": [10, 15, 20],
        "break_threshold": [1.5, 2.0, 2.5],
    },
}


def get_strategy_type_from_name(name: str) -> str:
    """从策略名称推断策略类型"""
    if "RSI+MACD" in name:
        return "rsi_macd"
    elif "RSI" in name:
        return "rsi"
    elif "均线" in name or "MA" in name or "排列" in name:
        return "ma_ribbon"
    elif "量价" in name or "volume" in name.lower():
        return "vol_break"
    return None


def generate_param_combinations(param_grid: dict) -> list:
    """生成参数组合"""
    import itertools
    keys = param_grid.keys()
    values = param_grid.values()
    combinations = list(itertools.product(*values))
    return [dict(zip(keys, combo)) for combo in combinations]


def run_backtest(strategy_type: str, params: dict, klines: list, 
                 tp_pct: float, sl_pct: float, trailing_activation: float, trailing_callback: float):
    """运行单次回测"""
    # 合并参数
    full_params = {
        **params,
        "take_profit_pct": tp_pct,
        "stop_loss_pct": sl_pct,
        "trailing_stop_pct": trailing_callback,
        "trailing_activation_pct": trailing_activation,
        "size": 1,  # 固定1张合约（约700 USDT保证金@100X）
    }
    
    engine = BacktestEngine()
    result = engine.run(
        strategy_type=strategy_type,
        params=full_params,
        symbol=SYMBOL,
        timeframe=TIMEFRAMES[0],  # 会被klines覆盖
        klines=klines,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
        regime_filter=True,
    )
    
    return result


def main():
    print("=" * 80)
    print("完整回测优化 - 多周期、多参数、多止盈止损")
    print("=" * 80)
    print(f"初始资金: {INITIAL_CAPITAL} USDT")
    print(f"杠杆: {LEVERAGE}X")
    print(f"交易对: {SYMBOL}")
    print(f"周期: {TIMEFRAMES}")
    print("=" * 80)
    
    # 查询策略
    db = SessionLocal()
    strategies = db.query(Strategy).filter(
        Strategy.published == True,
        Strategy.enabled == True
    ).all()
    print(f"\n找到 {len(strategies)} 个启用的策略")
    
    all_results = []
    
    # 测试每个周期
    for timeframe in TIMEFRAMES:
        print(f"\n{'='*80}")
        print(f"测试周期: {timeframe}")
        print(f"{'='*80}")
        
        # 获取K线数据（尝试获取更多）
        spot_symbol = SYMBOL.replace("-SWAP", "")
        print(f"\n获取K线数据...")
        
        # 根据周期计算需要的K线数量
        # 15m: 需要更多数据才能覆盖足够天数
        # 30m: 1000根 ≈ 20天
        # 1h: 2000根 ≈ 83天
        klines_limit = {
            "15m": 2000,  # 约20天
            "30m": 2000,  # 约40天
            "1h": 2000,   # 约83天
        }.get(timeframe, 1000)
        
        klines = market_service.get_klines(
            symbol=spot_symbol,
            timeframe=timeframe,
            limit=klines_limit,
        )
        
        if not klines or len(klines) < 100:
            print(f"[ERROR] K线数据不足: {len(klines) if klines else 0}")
            continue
        
        print(f"[OK] 获取到 {len(klines)} 根K线")
        
        # 测试每个策略
        for strategy in strategies:
            strategy_type = get_strategy_type_from_name(strategy.name)
            if not strategy_type:
                print(f"[SKIP] {strategy.name} - 无法推断策略类型")
                continue
            
            print(f"\n{'='*80}")
            print(f"策略: {strategy.name} ({strategy_type})")
            print(f"{'='*80}")
            
            # 获取参数网格
            param_grid = STRATEGY_PARAMS.get(strategy_type)
            if not param_grid:
                print(f"[SKIP] 未找到参数网格")
                continue
            
            # 生成参数组合
            param_combinations = generate_param_combinations(param_grid)
            print(f"参数组合数: {len(param_combinations)}")
            
            # 测试每组止盈止损
            for tp_pct, sl_pct, trailing_act, trailing_cb in TP_SL_COMBINATIONS:
                print(f"\n止盈止损: TP={tp_pct}%, SL={sl_pct}%, 移动激活={trailing_act}%, 回调={trailing_cb}%")
                
                best_result = None
                best_params = None
                
                # 测试每个参数组合
                for i, params in enumerate(param_combinations[:10], 1):  # 限制为前10个组合
                    result = run_backtest(
                        strategy_type, params, klines,
                        tp_pct, sl_pct, trailing_act, trailing_cb
                    )
                    
                    if result.get("ok"):
                        total_return = result.get("total_return", 0)
                        win_rate = result.get("win_rate", 0)
                        trade_count = result.get("trade_count", 0)
                        sharpe = result.get("sharpe_ratio", 0)
                        
                        if best_result is None or total_return > best_result["total_return"]:
                            best_result = {
                                "params": params,
                                "total_return": total_return,
                                "win_rate": win_rate,
                                "trade_count": trade_count,
                                "sharpe_ratio": sharpe,
                            }
                
                if best_result:
                    print(f"  最优: 收益率={best_result['total_return']:.2f}%, "
                          f"胜率={best_result['win_rate']:.1f}%, "
                          f"交易={best_result['trade_count']}, "
                          f"夏普={best_result['sharpe_ratio']:.2f}")
                    
                    all_results.append({
                        "timeframe": timeframe,
                        "strategy": strategy.name,
                        "strategy_type": strategy_type,
                        "tp_pct": tp_pct,
                        "sl_pct": sl_pct,
                        "trailing_activation": trailing_act,
                        "trailing_callback": trailing_cb,
                        "best_params": best_result["params"],
                        "total_return": best_result["total_return"],
                        "win_rate": best_result["win_rate"],
                        "trade_count": best_result["trade_count"],
                        "sharpe_ratio": best_result["sharpe_ratio"],
                        "klines_count": len(klines),
                    })
    
    # 生成报告
    print("\n" + "=" * 80)
    print("回测优化完成")
    print("=" * 80)
    
    # 按收益率排序
    all_results.sort(key=lambda x: x["total_return"], reverse=True)
    
    # 打印Top 20
    print(f"\nTop 20 策略配置:")
    print(f"{'排名':<4} {'周期':<6} {'策略':<20} {'TP%':>5} {'SL%':>5} {'收益%':>8} {'胜率':>6} {'交易':>6}")
    print("-" * 80)
    
    for i, r in enumerate(all_results[:20], 1):
        print(f"{i:<4} {r['timeframe']:<6} {r['strategy']:<20} {r['tp_pct']:>5} {r['sl_pct']:>5} "
              f"{r['total_return']:>7.2f}% {r['win_rate']:>5.1f}% {r['trade_count']:>6}")
    
    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "initial_capital": INITIAL_CAPITAL,
            "leverage": LEVERAGE,
            "symbol": SYMBOL,
            "timeframes": TIMEFRAMES,
        },
        "results": all_results,
    }
    
    report_file = f"comprehensive_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存: {report_file}")
    
    db.close()


if __name__ == "__main__":
    main()
