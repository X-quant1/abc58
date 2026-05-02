"""组合策略回测 - 测试多策略确认机制

测试配置：
- 杠杆：100X
- 周期：1h（最佳周期）
- 策略：3个组合策略
- 对比：单策略 vs 组合策略
"""
import json
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

# 组合策略配置
COMBO_STRATEGIES = [
    {
        "name": "趋势突破组合",
        "type": "trend_break_combo",
        "desc": "趋势突破 + RSI+MACD确认",
        "params": {
            "primary_strategy": "trend_break",
            "confirm_strategies": ["rsi_macd"],
            "confirm_threshold": 2,
            "regime_filter": True,
            "take_profit_pct": 60,
            "stop_loss_pct": 35,
            "trailing_activation_pct": 50,
            "trailing_callback_pct": 25,
            "size": 1,
        },
    },
    {
        "name": "多策略确认组合",
        "type": "multi_confirm_combo",
        "desc": "趋势突破 + 3策略确认",
        "params": {
            "primary_strategy": "trend_break",
            "confirm_strategies": ["rsi_macd", "ma_ribbon", "supertrend"],
            "confirm_threshold": 3,
            "regime_filter": True,
            "take_profit_pct": 80,
            "stop_loss_pct": 40,
            "trailing_activation_pct": 60,
            "trailing_callback_pct": 30,
            "size": 1,
        },
    },
    {
        "name": "保守型组合",
        "type": "conservative_combo",
        "desc": "均线排列 + 双重确认",
        "params": {
            "primary_strategy": "ma_ribbon",
            "confirm_strategies": ["rsi_macd", "trend_break"],
            "confirm_threshold": 2,
            "regime_filter": True,
            "take_profit_pct": 50,
            "stop_loss_pct": 30,
            "trailing_activation_pct": 40,
            "trailing_callback_pct": 20,
            "size": 1,
        },
    },
]

# 对比单策略配置
SINGLE_STRATEGIES = [
    {
        "name": "趋势突破（单策略）",
        "type": "trend_break",
        "params": {
            "ema_period": 21,
            "boll_period": 10,
            "boll_std": 1.5,
            "vol_ma_period": 10,
            "take_profit_pct": 60,
            "stop_loss_pct": 35,
            "trailing_activation_pct": 50,
            "trailing_callback_pct": 25,
            "size": 1,
        },
    },
    {
        "name": "RSI+MACD（单策略）",
        "type": "rsi_macd",
        "params": {
            "rsi_period": 6,
            "macd_fast": 6,
            "macd_slow": 26,
            "macd_signal": 9,
            "take_profit_pct": 60,
            "stop_loss_pct": 35,
            "trailing_activation_pct": 50,
            "trailing_callback_pct": 25,
            "size": 1,
        },
    },
]


def run_backtest(strategy_type: str, params: dict, klines: list):
    """运行单次回测"""
    engine = BacktestEngine()
    result = engine.run(
        strategy_type=strategy_type,
        params=params,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        klines=klines,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
        regime_filter=params.get("regime_filter", False),
    )
    return result


def main():
    print("=" * 80)
    print("组合策略回测 - 多策略确认机制")
    print("=" * 80)
    print(f"初始资金: {INITIAL_CAPITAL} USDT")
    print(f"杠杆: {LEVERAGE}X")
    print(f"交易对: {SYMBOL}")
    print(f"周期: {TIMEFRAME}")
    print("=" * 80)
    
    # 获取K线数据
    print("\n获取K线数据...")
    spot_symbol = SYMBOL.replace("-SWAP", "")
    klines = market_service.get_klines(
        symbol=spot_symbol,
        timeframe=TIMEFRAME,
        limit=2000,
    )
    
    if not klines or len(klines) < 100:
        print(f"[ERROR] K线数据不足: {len(klines) if klines else 0}")
        return
    
    print(f"[OK] 获取到 {len(klines)} 根K线")
    
    all_results = []
    
    # 测试组合策略
    print("\n" + "=" * 80)
    print("测试组合策略")
    print("=" * 80)
    
    for strategy in COMBO_STRATEGIES:
        print(f"\n策略: {strategy['name']}")
        print(f"描述: {strategy['desc']}")
        
        result = run_backtest(
            strategy["type"],
            strategy["params"],
            klines
        )
        
        if result.get("ok"):
            total_return = result.get("total_return", 0)
            win_rate = result.get("win_rate", 0)
            trade_count = result.get("trade_count", 0)
            sharpe = result.get("sharpe_ratio", 0)
            max_dd = result.get("max_drawdown", 0)
            
            print(f"  收益率: {total_return:.2f}%")
            print(f"  胜率: {win_rate:.1f}%")
            print(f"  交易次数: {trade_count}")
            print(f"  夏普比率: {sharpe:.2f}")
            print(f"  最大回撤: {max_dd:.2f}%")
            
            all_results.append({
                "category": "组合策略",
                "name": strategy["name"],
                "type": strategy["type"],
                "total_return": total_return,
                "win_rate": win_rate,
                "trade_count": trade_count,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
            })
        else:
            print(f"  [ERROR] {result.get('msg', 'unknown error')}")
    
    # 测试单策略（对比）
    print("\n" + "=" * 80)
    print("测试单策略（对比）")
    print("=" * 80)
    
    for strategy in SINGLE_STRATEGIES:
        print(f"\n策略: {strategy['name']}")
        
        result = run_backtest(
            strategy["type"],
            strategy["params"],
            klines
        )
        
        if result.get("ok"):
            total_return = result.get("total_return", 0)
            win_rate = result.get("win_rate", 0)
            trade_count = result.get("trade_count", 0)
            sharpe = result.get("sharpe_ratio", 0)
            max_dd = result.get("max_drawdown", 0)
            
            print(f"  收益率: {total_return:.2f}%")
            print(f"  胜率: {win_rate:.1f}%")
            print(f"  交易次数: {trade_count}")
            print(f"  夏普比率: {sharpe:.2f}")
            print(f"  最大回撤: {max_dd:.2f}%")
            
            all_results.append({
                "category": "单策略",
                "name": strategy["name"],
                "type": strategy["type"],
                "total_return": total_return,
                "win_rate": win_rate,
                "trade_count": trade_count,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_dd,
            })
        else:
            print(f"  [ERROR] {result.get('msg', 'unknown error')}")
    
    # 生成报告
    print("\n" + "=" * 80)
    print("回测完成")
    print("=" * 80)
    
    # 按收益率排序
    all_results.sort(key=lambda x: x["total_return"], reverse=True)
    
    # 打印对比表
    print(f"\n策略对比（按收益率排序）:")
    print(f"{'排名':<4} {'类别':<8} {'策略':<20} {'收益%':>8} {'胜率':>6} {'交易':>6} {'夏普':>6} {'回撤%':>6}")
    print("-" * 80)
    
    for i, r in enumerate(all_results, 1):
        print(f"{i:<4} {r['category']:<8} {r['name']:<20} {r['total_return']:>7.2f}% "
              f"{r['win_rate']:>5.1f}% {r['trade_count']:>6} {r['sharpe_ratio']:>5.2f} "
              f"{r['max_drawdown']:>5.2f}%")
    
    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "initial_capital": INITIAL_CAPITAL,
            "leverage": LEVERAGE,
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "klines_count": len(klines),
        },
        "results": all_results,
    }
    
    report_file = f"combo_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n报告已保存: {report_file}")


if __name__ == "__main__":
    main()
