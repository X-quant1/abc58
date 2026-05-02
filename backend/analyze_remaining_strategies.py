"""分析剩余策略的优化潜力"""
import sys
sys.path.insert(0, '.')
from app.services.strategy import (
    KDJStrategy, SuperTrendStrategy, EMACrossVolumeStrategy, 
    DualEMAStrategy, VolumePriceBreakStrategy, RSIMACDStrategy
)
from app.services.market import MarketService

# 获取最近 7 天的 K线
market = MarketService()
klines = market.get_klines('BTC-USDT-SWAP', '1H', limit=200)

print(f'分析 {len(klines)} 根K线（约 {len(klines)//24} 天）\n')

# 定义策略和多种参数组合
strategies = [
    # KDJ - 当前参数太保守
    ("KDJ金叉死叉(当前)", KDJStrategy, {"k_period": 9, "d_period": 3, "j_smooth": 3, "overbought": 80, "oversold": 20}),
    ("KDJ金叉死叉(优化A)", KDJStrategy, {"k_period": 5, "d_period": 3, "j_smooth": 3, "overbought": 75, "oversold": 25}),
    ("KDJ金叉死叉(优化B)", KDJStrategy, {"k_period": 7, "d_period": 3, "j_smooth": 3, "overbought": 70, "oversold": 30}),
    
    # SuperTrend - 可以降低multiplier提高敏感度
    ("SuperTrend趋势(当前)", SuperTrendStrategy, {"atr_period": 10, "multiplier": 3}),
    ("SuperTrend趋势(优化A)", SuperTrendStrategy, {"atr_period": 7, "multiplier": 2.5}),
    ("SuperTrend趋势(优化B)", SuperTrendStrategy, {"atr_period": 10, "multiplier": 2.0}),
    
    # EMA量能确认 - 当前参数已经不错
    ("EMA量能确认(当前)", EMACrossVolumeStrategy, {"fast_period": 12, "slow_period": 26, "vol_period": 20, "vol_mult": 1.5}),
    ("EMA量能确认(优化A)", EMACrossVolumeStrategy, {"fast_period": 9, "slow_period": 21, "vol_period": 14, "vol_mult": 1.3}),
    
    # 双时间框架EMA - 可以缩短周期
    ("双时间框架EMA(当前)", DualEMAStrategy, {"trend_period": 50, "signal_period": 10}),
    ("双时间框架EMA(优化A)", DualEMAStrategy, {"trend_period": 30, "signal_period": 7}),
    ("双时间框架EMA(优化B)", DualEMAStrategy, {"trend_period": 21, "signal_period": 5}),
    
    # 量价突破 - 可以降低vol_mult
    ("量价突破(当前)", VolumePriceBreakStrategy, {"lookback": 20, "vol_mult": 1.5}),
    ("量价突破(优化A)", VolumePriceBreakStrategy, {"lookback": 14, "vol_mult": 1.2}),
    ("量价突破(优化B)", VolumePriceBreakStrategy, {"lookback": 10, "vol_mult": 1.0}),
    
    # RSI+MACD共振 - 这个策略信号极少，可能需要大改
    ("RSI+MACD共振(当前)", RSIMACDStrategy, {"rsi_period": 6, "macd_fast": 12, "macd_slow": 26, "macd_signal": 9}),
    ("RSI+MACD共振(优化A)", RSIMACDStrategy, {"rsi_period": 6, "macd_fast": 6, "macd_slow": 13, "macd_signal": 5}),
    ("RSI+MACD共振(优化B)", RSIMACDStrategy, {"rsi_period": 14, "macd_fast": 8, "macd_slow": 17, "macd_signal": 5}),
]

print("=" * 90)
print(f"{'策略名称':<30} {'信号数':<8} {'开多':<6} {'开空':<6} {'频率(次/天)':<12}")
print("=" * 90)

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
    
    # 标记优化效果
    marker = ""
    if "当前" in name:
        marker = " [基准]"
    elif freq > 1.5:
        marker = " [推荐]"
    
    print(f"{name:<30} {total:<8} {long_count:<6} {short_count:<6} {freq:<12.1f}{marker}")

print("=" * 90)
