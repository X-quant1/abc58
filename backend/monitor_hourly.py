"""策略监控脚本 - 每小时检查一次"""
import urllib.request
import json
import time
from datetime import datetime

def check_strategies():
    """检查策略状态"""
    try:
        # 1. 登录获取token
        login_data = json.dumps({"email": "admin", "password": "btc2026"}).encode()
        req = urllib.request.Request(
            'http://127.0.0.1:8000/api/auth/login',
            data=login_data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            login_result = json.loads(resp.read().decode())
            token = login_result['access_token']

        # 2. 获取策略运行状态
        req = urllib.request.Request(
            'http://127.0.0.1:8000/api/strategy/status',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
            status = result.get('status', {})

        # 3. 获取策略列表
        req = urllib.request.Request(
            'http://127.0.0.1:8000/api/admin/strategies/list',
            headers={'Authorization': f'Bearer {token}'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            strategies = {s['id']: s for s in data.get('strategies', [])}

        # 4. 检查交易记录
        total_trades = 0
        new_trades = []
        for sid in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
            req = urllib.request.Request(
                f'http://127.0.0.1:8000/api/strategy/{sid}/trades?limit=5',
                headers={'Authorization': f'Bearer {token}'}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                trades_data = json.loads(resp.read().decode())
            trades = trades_data if isinstance(trades_data, list) else trades_data.get('trades', [])
            total_trades += len(trades)
            if trades:
                new_trades.append((sid, trades[0]))

        # 5. 打印报告
        print()
        print('=' * 70)
        print(f'策略监控报告 - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print('=' * 70)

        running_count = sum(1 for s in status.values() if s.get('running', False))
        print(f'运行中策略: {running_count}/10')
        print(f'总交易数: {total_trades}')

        if new_trades:
            print()
            print('最近交易:')
            for sid, trade in new_trades:
                s = strategies.get(sid, {})
                time_str = trade.get('created_at', '')[:16]
                side = trade.get('side', '')
                direction = trade.get('direction', '')
                price = trade.get('price', 0)
                print(f'  #{sid} {s.get("name", ""):20s} | {time_str} | {side:4s} | {direction:15s} | {price:.2f}')

        # 6. 检查持仓
        positions = []
        for sid in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
            s = strategies.get(sid, {})
            pos = s.get('position', 'none')
            if pos != 'none':
                positions.append((sid, s.get('name', ''), pos))

        if positions:
            print()
            print('持仓状态:')
            for sid, name, pos in positions:
                print(f'  #{sid} {name:20s} | 持仓: {pos}')

        print('=' * 70)

        return total_trades, positions

    except Exception as e:
        print(f'[错误] {e}')
        return 0, []

# 主循环
print('策略监控启动')
print('每小时检查一次，按Ctrl+C停止')
print()

last_trades = 0
last_positions = []
check_count = 0

try:
    while True:
        check_count += 1
        print(f'\n[检查 #{check_count}]')

        total_trades, positions = check_strategies()

        # 检测新交易
        if total_trades > last_trades:
            print(f'\n>>> 检测到新交易！({last_trades} -> {total_trades}) <<<')
            last_trades = total_trades

        # 检测持仓变化
        if positions != last_positions:
            print(f'\n>>> 持仓状态变化！ <<<')
            last_positions = positions

        # 等待1小时
        print('\n等待下一小时...')
        time.sleep(3600)

except KeyboardInterrupt:
    print('\n\n监控已停止')
