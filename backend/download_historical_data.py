"""
从OKX下载历史K线数据
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import time
import os

def download_okx_klines(symbol="BTC-USDT-SWAP", bar="1H", start_date="2025-01-01", end_date="2026-04-26"):
    """
    从OKX API下载历史K线数据

    Args:
        symbol: 交易对
        bar: K线周期 (1m/5m/15m/1H/4H/1D)
        start_date: 开始日期
        end_date: 结束日期
    """
    base_url = "https://www.okx.com/api/v5/market/candles"

    # 转换日期为时间戳
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000)

    all_data = []
    current_ts = end_ts

    print(f"下载 {symbol} {bar} K线数据...")
    print(f"时间范围: {start_date} ~ {end_date}")

    while current_ts > start_ts:
        params = {
            "instId": symbol,
            "bar": bar,
            "before": current_ts,
            "limit": 300,  # OKX API限制每次最多300条
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()

            if data.get("code") != "0":
                print(f"API错误: {data.get('msg')}")
                break

            candles = data.get("data", [])
            if not candles:
                print("没有更多数据")
                break

            all_data.extend(candles)

            # 更新时间戳为最早的一根K线
            earliest_ts = int(candles[-1][0])
            current_ts = earliest_ts - 1

            print(f"已下载 {len(all_data)} 条，最早时间: {datetime.fromtimestamp(earliest_ts/1000)}")

            # 避免请求过快
            time.sleep(0.5)

            # 如果最早时间已经小于开始时间，停止
            if earliest_ts < start_ts:
                break

        except Exception as e:
            print(f"下载失败: {e}")
            break

    # 转换为DataFrame
    if all_data:
        df = pd.DataFrame(all_data, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "volCcy", "volCcyQuote", "confirm"
        ])

        # 数据类型转换
        df["timestamp"] = df["timestamp"].astype(int)
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["volume"] = df["volume"].astype(float)

        # 按时间排序
        df = df.sort_values("timestamp")

        # 保存为CSV
        output_dir = r"c:\LH\OKX\backend\historical_data"
        os.makedirs(output_dir, exist_ok=True)

        filename = f"{output_dir}/{symbol}_{bar}_{start_date}_{end_date}.csv"
        df.to_csv(filename, index=False)

        print(f"\n下载完成！")
        print(f"总数据: {len(df)} 条")
        print(f"时间范围: {datetime.fromtimestamp(df['timestamp'].min()/1000)} ~ {datetime.fromtimestamp(df['timestamp'].max()/1000)}")
        print(f"保存到: {filename}")

        return df
    else:
        print("没有下载到数据")
        return None

# 下载3个月的1小时K线数据（从现在往前推）
end_date = datetime.now().strftime("%Y-%m-%d")
start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

download_okx_klines(
    symbol="BTC-USDT-SWAP",
    bar="1H",
    start_date=start_date,
    end_date=end_date
)
