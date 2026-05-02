"""测试开多单 - 简化版"""
import subprocess
import json

# OKX CLI路径
OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

def run_okx(args):
    """执行OKX CLI命令"""
    cmd = [OKX_CLI] + args
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.stdout

print("=" * 60)
print("测试开多单 - 0.01张 BTC-USDT-SWAP")
print("=" * 60)

# 1. 获取当前价格
print("\n[1] 获取当前BTC价格...")
output = run_okx(["market", "ticker", "BTC-USDT-SWAP"])
print(output)

# 2. 设置杠杆
print("\n[2] 设置杠杆为100x（全仓）...")
output = run_okx(["swap", "leverage", "--instId", "BTC-USDT-SWAP", "--lever", "100", "--mgnMode", "cross", "--posSide", "long"])

# 3. 开多单（不带止盈止损，先测试基础功能）
print("\n[3] 开多单 0.01张...")
output = run_okx(["swap", "place", "--instId", "BTC-USDT-SWAP", "--side", "buy", "--ordType", "market", "--sz", "0.01", "--posSide", "long", "--tdMode", "cross"])

# 4. 查询持仓
print("\n[4] 查询持仓...")
output = run_okx(["swap", "positions", "--instId", "BTC-USDT-SWAP"])

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
