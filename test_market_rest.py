"""测试 market_rest.py 服务"""
import sys
sys.path.insert(0, r"c:\LH\OKX\backend")

# 先导入settings路由以加载API配置
from app.routers import settings
from app.services.market_rest import get_market_service

def test_market_service():
    ms = get_market_service()
    
    # 测试1: 获取BTC行情
    print("=== 测试1: 获取BTC行情 ===")
    ticker = ms.get_ticker('BTC-USDT')
    print(f"BTC价格: {ticker['price']} USDT")
    print(f"24h涨跌: {ticker['change_24h']}%")
    print(f"24h最高: {ticker['high']}")
    print(f"24h最低: {ticker['low']}")
    print()
    
    # 测试2: 获取K线
    print("=== 测试2: 获取K线 ===")
    klines = ms.get_klines('BTC-USDT-SWAP', '1H', 5)
    print(f"获取到 {len(klines)} 根K线")
    for k in klines[-3:]:
        print(f"  时间: {k['timestamp']}, 收盘: {k['close']}, 成交量: {k['volume']}")
    print()
    
    # 测试3: 获取账户余额
    print("=== 测试3: 获取账户余额 ===")
    balance = ms.get_account_balance('USDT')
    print(f"总权益: {balance['total_equity']} USDT")
    for detail in balance['details']:
        print(f"  币种: {detail['ccy']}, 余额: {detail['bal']}, 可用: {detail['availBal']}")
    print()
    
    # 测试4: 获取持仓
    print("=== 测试4: 获取持仓 ===")
    positions = ms.get_positions()
    print(f"当前持仓数: {len(positions)}")
    for pos in positions:
        print(f"  合约: {pos['instId']}, 方向: {pos['posSide']}, 数量: {pos['pos']}, 未实现盈亏: {pos['upl']}")
    print()
    
    # 测试5: 获取主流币种行情
    print("=== 测试5: 获取主流币种行情 ===")
    tickers = ms.get_multi_tickers()
    print(f"获取到 {len(tickers)} 个币种行情")
    for t in tickers[:3]:
        print(f"  {t['symbol']}: {t['price']} USDT ({t['change_24h']}%)")
    print()
    
    print("所有测试通过!")

if __name__ == "__main__":
    test_market_service()
