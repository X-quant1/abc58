"""获取OKX CLI trail命令详细帮助"""
import subprocess

OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

# 尝试获取更详细的帮助
result = subprocess.run(
    [OKX_CLI, "swap", "algo", "trail", "--help"],
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='ignore'
)

print("=" * 60)
print("OKX CLI Help - swap algo trail")
print("=" * 60)
print(result.stdout)
if result.stderr:
    print("\nSTDERR:")
    print(result.stderr)
