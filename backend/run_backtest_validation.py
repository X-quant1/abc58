"""回测验证新参数 - 124天回测对比

对比新旧参数效果：
- 旧参数：TP=0%, SL=5%
- 新参数：趋势策略 TP=2%, SL=0.8%, 移动止损=0.5%
         震荡策略 TP=1.5%, SL=1%, 移动止损=0.3%
"""
import sys
import json
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Strategy
from app.services.backtest import BacktestEngine
from app.services.market import market_service


# 回测配置
BACKTEST_DAYS = 124  # 124天历史数据
INITIAL_CAPITAL = 10000  # 初始资金 10000 USDT
LEVERAGE = 100  # 100X杠杆
SYMBOL = "BTC-USDT-SWAP"
TIMEFRAME = "1h"

# 策略分类（实际可用的策略类型）
TREND_STRATEGIES = [
    "ma_cross",         # 均线交叉
    "ema_volume",       # EMA量能
    "supertrend",       # SuperTrend
    "dual_ema",         # 双EMA
    "ma_ribbon",        # 均线带
]

OSCILLATOR_STRATEGIES = [
    "rsi",              # RSI策略
    "macd",             # MACD
    "kdj",              # KDJ
    "cci",              # CCI
    "bollinger",        # 布林带
]


def get_strategy_params(strategy_type: str, strategy_name: str, db_strategy: Strategy) -> dict:
    """获取策略参数，合并数据库配置和默认参数"""
    
    # 从数据库策略读取基础参数
    base_params = json.loads(db_strategy.params) if db_strategy.params else {}
    
    # 根据策略类型设置默认参数
    if strategy_type in TREND_STRATEGIES:
        # 趋势策略参数
        defaults = {
            "take_profit_pct": 2.0,
            "stop_loss_pct": 0.8,
            "trailing_stop_pct": 0.5,
            "trailing_activation_pct": 0.5,
            "size": 0.01,  # 固定0.01张
        }
    else:
        # 震荡策略参数
        defaults = {
            "take_profit_pct": 1.5,
            "stop_loss_pct": 1.0,
            "trailing_stop_pct": 0.3,
            "trailing_activation_pct": 0.3,
            "size": 0.01,
        }
    
    # 合并参数（数据库配置优先）
    params = {**defaults, **base_params}
    return params


def run_backtest_for_strategy(strategy_type: str, strategy_name: str, params: dict, klines: list):
    """运行单个策略的回测"""
    engine = BacktestEngine()
    
    result = engine.run(
        strategy_type=strategy_type,
        params=params,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        klines=klines,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
        regime_filter=True,  # 启用市场状态过滤
    )
    
    return result


def main():
    print("=" * 70)
    print("回测验证新参数 - 124天历史数据")
    print("=" * 70)
    print(f"初始资金: {INITIAL_CAPITAL} USDT")
    print(f"杠杆: {LEVERAGE}X")
    print(f"交易对: {SYMBOL}")
    print(f"周期: {TIMEFRAME}")
    print(f"回测天数: {BACKTEST_DAYS}天")
    print("=" * 70)
    
    # 获取K线数据
    print("\n[1/3] 获取K线数据...")
    spot_symbol = SYMBOL.replace("-SWAP", "")
    klines = market_service.get_klines(
        symbol=spot_symbol,
        timeframe=TIMEFRAME,
        limit=BACKTEST_DAYS * 24,  # 1h周期，每天24根
    )
    
    if not klines or len(klines) < 100:
        print(f"[ERROR] K线数据不足: {len(klines) if klines else 0}")
        return
    
    print(f"[OK] 获取到 {len(klines)} 根K线")
    
    # 查询数据库中的策略
    print("\n[2/3] 查询策略配置...")
    db = SessionLocal()
    strategies = db.query(Strategy).filter(Strategy.published == True).all()
    print(f"[OK] 找到 {len(strategies)} 个已上架策略")
    
    # 策略映射（数据库策略名 -> 策略类型）
    strategy_map = {
        "均线多空排列-1H": "ma_cross",
        "双时间框架EMA-1H": "dual_ema",
        "EMA量能确认-1H": "ema_volume",
        "SuperTrend趋势-1H": "supertrend",
        "均线带策略-1H": "ma_ribbon",
        "MACD策略-1H": "macd",
        "KDJ金叉死叉-1H": "kdj",
        "CCI趋势反转-1H": "cci",
        "RSI超卖超买-1H": "rsi",
        "布林带策略-1H": "bollinger",
    }
    
    # 运行回测
    print("\n[3/3] 运行回测...")
    results = []
    
    for db_strategy in strategies:
        strategy_name = db_strategy.name
        strategy_type = strategy_map.get(strategy_name)
        
        if not strategy_type:
            print(f"[SKIP] {strategy_name} - 未找到对应策略类型")
            continue
        
        # 获取参数
        params = get_strategy_params(strategy_type, strategy_name, db_strategy)
        
        print(f"\n{'='*70}")
        print(f"策略: {strategy_name} ({strategy_type})")
        print(f"参数: TP={params.get('take_profit_pct')}%, SL={params.get('stop_loss_pct')}%, 移动止损={params.get('trailing_stop_pct')}%")
        
        # 运行回测
        result = run_backtest_for_strategy(strategy_type, strategy_name, params, klines)
        
        if result.get("ok"):
            total_return = result.get("total_return", 0)
            trade_count = result.get("trade_count", 0)
            win_rate = result.get("win_rate", 0)
            max_drawdown = result.get("max_drawdown", 0)
            sharpe = result.get("sharpe_ratio", 0)
            
            print(f"[OK] 收益率: {total_return:.2f}%")
            print(f"     交易次数: {trade_count}")
            print(f"     胜率: {win_rate:.1f}%")
            print(f"     最大回撤: {max_drawdown:.2f}%")
            print(f"     夏普比率: {sharpe:.2f}")
            
            results.append({
                "name": strategy_name,
                "type": strategy_type,
                "total_return": total_return,
                "trade_count": trade_count,
                "win_rate": win_rate,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe,
            })
        else:
            print(f"[ERROR] {result.get('msg', 'unknown error')}")
    
    # 汇总结果
    print("\n" + "=" * 70)
    print("回测结果汇总")
    print("=" * 70)
    
    # 按收益率排序
    results.sort(key=lambda x: x["total_return"], reverse=True)
    
    print(f"\n{'策略名称':<25} {'收益率':>10} {'交易次数':>8} {'胜率':>8} {'最大回撤':>10} {'夏普':>8}")
    print("-" * 70)
    
    for r in results:
        print(f"{r['name']:<25} {r['total_return']:>9.2f}% {r['trade_count']:>8} {r['win_rate']:>7.1f}% {r['max_drawdown']:>9.2f}% {r['sharpe_ratio']:>8.2f}")
    
    # 统计
    profitable = [r for r in results if r["total_return"] > 0]
    print(f"\n盈利策略: {len(profitable)}/{len(results)}")
    print(f"平均收益率: {sum(r['total_return'] for r in results) / len(results):.2f}%")
    
    db.close()


if __name__ == "__main__":
    main()
