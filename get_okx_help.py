"""获取OKX CLI帮助信息"""
import subprocess
import sys

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

# 获取 swap algo place 的帮助
result = subprocess.run(
    [OKX_CLI, "swap", "algo", "place", "--help"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore'
)

print("=" * 60)
print("OKX CLI Help - swap algo place")
print("=" * 60)
print(result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)
