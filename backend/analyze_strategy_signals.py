"""分析策略信号生成频率"""
import sys
sys.path.insert(0, '.')
from app.services.strategy import (
    RSIStrategy, KDJStrategy, CCIStrategy, RSIMACDStrategy,
    SuperTrendStrategy, EMACrossVolumeStrategy, DualEMAStrategy,
    MARibbonStrategy, VolumePriceBreakStrategy
)
from app.services.market import MarketService

# 获取最近 7 天的 K线
market = MarketService()
klines = market.get_klines('BTC-USDT-SWAP', '1H', limit=200)

print(f'分析 {len(klines)} 根K线（约 {len(klines)//24} 天）\n')

# 定义策略和参数（当前参数 vs 优化参数）
strategies = [
    ("RSI超卖超买", RSIStrategy, {"period": 14, "oversold": 30, "overbought": 70}),
    ("RSI超卖超买(优化)", RSIStrategy, {"period": 6, "oversold": 40, "overbought": 60}),
    
    ("KDJ金叉死叉", KDJStrategy, {"k_period": 9, "d_period": 3, "j_smooth": 3, "overbought": 80, "oversold": 20}),
    ("KDJ金叉死叉(优化)", KDJStrategy, {"k_period": 5, "d_period": 3, "j_smooth": 3, "overbought": 75, "oversold": 25}),
    
    ("CCI趋势反转", CCIStrategy, {"period": 20, "overbought": 100, "oversold": -100}),
    ("CCI趋势反转(优化)", CCIStrategy, {"period": 10, "overbought": 80, "oversold": -80}),
    
    ("RSI+MACD共振", RSIMACDStrategy, {"rsi_period": 6, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9}),
    ("RSI+MACD共振(优化)", RSIMACDStrategy, {"rsi_period": 6, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5}),
    
    ("SuperTrend趋势", SuperTrendStrategy, {"atr_period": 10, "multiplier": 3}),
    ("SuperTrend趋势(优化)", SuperTrendStrategy, {"atr_period": 7, "multiplier": 2.5}),
    
    ("EMA量能确认", EMACrossVolumeStrategy, {"fast_period": 12, "slow_period": 26, "vol_period": 20, "vol_mult": 1.5}),
    ("EMA量能确认(优化)", EMACrossVolumeStrategy, {"fast_period": 7, "slow_period": 21, "vol_period": 14, "vol_mult": 1.2}),
    
    ("双时间框架EMA", DualEMAStrategy, {"trend_period": 50, "signal_period": 10}),
    ("双时间框架EMA(优化)", DualEMAStrategy, {"trend_period": 30, "signal_period": 7}),
    
    ("均线多空排列", MARibbonStrategy, {"period1": 5, "period2": 10, "period3": 20, "period4": 60}),
    ("均线多空排列(优化)", MARibbonStrategy, {"period1": 3, "period2": 7, "period3": 13, "period4": 21}),
    
    ("量价突破", VolumePriceBreakStrategy, {"lookback": 20, "vol_mult": 1.5}),
    ("量价突破(优化)", VolumePriceBreakStrategy, {"lookback": 14, "vol_mult": 1.2}),
]

print("=" * 80)
print(f"{'策略名称':<25} {'信号数':<8} {'开多':<6} {'开空':<6} {'频率(次/天)':<12}")
print("=" * 80)

for name, strategy_class, params in strategies:
    strategy = strategy_class(params)
    
    signals = []
    long_count = 0
    short_count = 0
    
    # 滑动窗口模拟
    for i in range(60, len(klines)):
        window = klines[:i+1]
        signal = strategy.generate_signal(window)
        
        if signal in ("open_long", "open_short"):
            signals.append((i, signal))
            if signal == "open_long":
                long_count += 1
            else:
                short_count += 1
    
    total = long_count + short_count
    freq = total / (len(klines) / 24)
    
    print(f"{name:<25} {total:<8} {long_count:<6} {short_count:<6} {freq:<12.1f}")

print("=" * 80)
