"""行情数据服务 - OKX CLI (okx-trade-cli)

使用 OKX 官方 CLI 工具获取行情和执行交易，
比手写 requests 更稳定、功能更全（107个工具）。

公开接口无需 API Key，认证接口需要配置 okx config init。
"""
import json
import subprocess
import time
import threading
import hashlib
import hmac
import base64
from datetime import datetime
from typing import Optional
import requests

from app import config
from app.services.logger import sys_logger


# ─── API 限频器（令牌桶）───

class RateLimiter:
    """令牌桶限频器 — 确保 OKX API 调用不超过限制

    OKX 限制: 20次/2秒 (读取类), 10次/2秒 (交易类)
    我们统一使用 15次/2秒 的保守值，避免触发。
    """

    def __init__(self, max_calls: int = 15, window_sec: float = 2.0):
        self.max_calls = max_calls
        self.window_sec = window_sec
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self):
        """阻塞等待直到可以发起请求"""
        while True:
            with self._lock:
                now = time.monotonic()
                # 清除过期时间戳
                cutoff = now - self.window_sec
                self._timestamps = [t for t in self._timestamps if t > cutoff]

                if len(self._timestamps) < self.max_calls:
                    self._timestamps.append(now)
                    return  # 可以请求

                # 计算需要等待的时间
                wait = self._timestamps[0] - cutoff + 0.05  # 多等50ms缓冲
            time.sleep(wait)


# 全局限频器
_api_limiter = RateLimiter(max_calls=15, window_sec=2.0)


# ─── OKX 错误码 ───

# 余额不足
OKX_ERR_INSUFFICIENT_BALANCE = "51000"
# 仓位不存在
OKX_ERR_POSITION_NOT_FOUND = "51116"
# 订单不存在
OKX_ERR_ORDER_NOT_FOUND = "51113"
# 限频
OKX_ERR_RATE_LIMIT = "51111"

# 可重试的错误码（网络/限频类）
RETRYABLE_ERRORS = {OKX_ERR_RATE_LIMIT}

# 不应重试的业务错误码
NON_RETRYABLE_ERRORS = {
    OKX_ERR_INSUFFICIENT_BALANCE,
    OKX_ERR_POSITION_NOT_FOUND,
    OKX_ERR_ORDER_NOT_FOUND,
}

# okx CLI 绝对路径
OKX_CLI = r"C:\LH\OKX\tools\node-v20.18.0-win-x64\okx.cmd"

# Node.js 需要在 PATH 中
import os
_node_dir = r"C:\LH\OKX\tools\node-v20.18.0-win-x64"
if _node_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _node_dir + ";" + os.environ.get("PATH", "")

# K线周期映射（OKX 格式：1H 而非 1h）
TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "10m": "10m", "15m": "15m", "30m": "30m",
    "1h": "1H", "4h": "4H", "1d": "1D", "1w": "1W", "1M": "1M",
}

# 主流币种
POPULAR_SYMBOLS = [
    {"symbol": "BTC-USDT", "base": "BTC", "name": "Bitcoin"},
    {"symbol": "ETH-USDT", "base": "ETH", "name": "Ethereum"},
    {"symbol": "SOL-USDT", "base": "SOL", "name": "Solana"},
    {"symbol": "XRP-USDT", "base": "XRP", "name": "XRP"},
    {"symbol": "DOGE-USDT", "base": "DOGE", "name": "Dogecoin"},
    {"symbol": "ADA-USDT", "base": "ADA", "name": "Cardano"},
    {"symbol": "AVAX-USDT", "base": "AVAX", "name": "Avalanche"},
    {"symbol": "DOT-USDT", "base": "DOT", "name": "Polkadot"},
    {"symbol": "LINK-USDT", "base": "LINK", "name": "Chainlink"},
    {"symbol": "SUI-USDT", "base": "SUI", "name": "Sui"},
]


class OKXAPIError(Exception):
    """OKX 业务错误（区分网络错误和业务错误）"""
    def __init__(self, code: str, msg: str, retryable: bool = False):
        self.code = code
        self.msg = msg
        self.retryable = retryable
        super().__init__(f"OKX [{code}] {msg}")


def _run_okx(args: list, timeout: int = 30, max_retries: int = 2) -> dict:
    """执行 okx CLI 命令，返回 JSON 结果

    增强:
    - 全局限频（令牌桶，15次/2秒）
    - 指数退避重试（网络超时/限频/5xx 自动重试）
    - OKX 错误码检查（区分业务错误和网络错误）
    - 余额不足等业务错误不重试
    """
    _api_limiter.acquire()  # 限频

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                # 指数退避: 1s, 2s, 4s...
                wait = min(2 ** attempt, 8)
                sys_logger.warn("okx_api", f"Retry {attempt}/{max_retries} after {wait}s: {last_error}")
                time.sleep(wait)
                _api_limiter.acquire()  # 重试也要限频

            result = subprocess.run(
                [OKX_CLI] + args + ["--json"],
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env=_build_env(),
            )

            if result.returncode != 0:
                err_msg = result.stderr.strip() or result.stdout.strip()
                raise RuntimeError(f"okx CLI error: {err_msg[:300]}")

            # 解析 JSON 输出
            output = result.stdout.strip()
            if not output:
                return {}

            data = json.loads(output)

            # 检查 OKX 错误码（--json 包装格式或直接返回）
            if isinstance(data, dict):
                # 格式1: {"env":..., "data":...}
                if "data" in data and "code" not in data:
                    return data["data"]
                # 格式2: {"code": "0", "data": [...]}
                code = str(data.get("code", "0"))
                if code != "0":
                    msg = data.get("msg", data.get("message", "unknown"))
                    retryable = code in RETRYABLE_ERRORS
                    raise OKXAPIError(code, msg[:200], retryable)

            return data

        except OKXAPIError as e:
            if not e.retryable or attempt >= max_retries:
                raise
            last_error = str(e)

        except subprocess.TimeoutExpired:
            if attempt >= max_retries:
                raise RuntimeError(f"okx CLI timeout ({timeout}s) after {max_retries + 1} attempts")
            last_error = f"timeout ({timeout}s)"

        except json.JSONDecodeError as e:
            if attempt >= max_retries:
                raise RuntimeError(f"okx CLI JSON parse error: {e}")
            last_error = f"JSON error: {e}"

        except RuntimeError as e:
            if "CLI error" in str(e) and attempt < max_retries:
                # CLI 进程返回非0，可能是临时错误
                if "rate" in str(e).lower() or "limit" in str(e).lower():
                    last_error = str(e)
                else:
                    raise  # 其他 CLI 错误不重试
            else:
                raise

    # 不应该到这里
    raise last_error or RuntimeError("unknown error")


def _build_env() -> dict:
    """构建 subprocess 环境变量（含 OKX 认证信息）"""
    env = os.environ.copy()
    env["OKX_API_KEY"] = config.OKX_API_KEY or ""
    env["OKX_SECRET_KEY"] = config.OKX_SECRET_KEY or ""
    env["OKX_PASSPHRASE"] = config.OKX_PASSPHRASE or ""
    # OKX CLI 用 OKX_DEMO 而不是 OKX_SANDBOX
    env["OKX_DEMO"] = "1" if config.OKX_SANDBOX.lower() == "true" else "0"
    env["OKX_SITE"] = "global"
    return env


def _to_okx_instId(symbol: str) -> str:
    """BTC-USDT / BTC/USDT -> BTC-USDT"""
    return symbol.replace("/", "-").upper()


def _call_okx_api(method: str, endpoint: str, body: dict = None) -> dict:
    """直接调用OKX REST API（绕过CLI限制）
    
    Args:
        method: HTTP方法 (GET/POST)
        endpoint: API路径 (如 /api/v5/trade/order-algo)
        body: 请求体（POST时）
    
    Returns:
        API响应数据
    """
    # OKX API基础URL
    base_url = "https://www.okx.com"
    
    # 生成签名
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    # 请求体
    body_str = ""
    if body and method == "POST":
        body_str = json.dumps(body, separators=(',', ':'))
    
    # 签名字符串
    pre_hash = timestamp + method + endpoint + body_str
    
    # HMAC-SHA256签名
    secret = config.OKX_SECRET_KEY.encode('utf-8')
    msg = pre_hash.encode('utf-8')
    signature = base64.b64encode(hmac.new(secret, msg, hashlib.sha256).digest()).decode('utf-8')
    
    # 请求头
    headers = {
        'OK-ACCESS-KEY': config.OKX_API_KEY,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': config.OKX_PASSPHRASE,
        'Content-Type': 'application/json',
    }
    
    # 模拟盘标识
    if config.OKX_SANDBOX.lower() == "true":
        headers['x-simulated-trading'] = '1'
    
    # 发送请求
    url = base_url + endpoint
    try:
        sys_logger.info("okx_api", f"Calling API: {method} {endpoint}")
        sys_logger.info("okx_api", f"Body: {body_str}")
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=body_str, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        sys_logger.info("okx_api", f"Response status: {response.status_code}")
        sys_logger.info("okx_api", f"Response: {response.text[:500]}")
        
        response.raise_for_status()
        data = response.json()
        
        # 检查API错误
        if data.get("code") != "0":
            raise OKXAPIError(data.get("code", ""), data.get("msg", ""))
        
        return data.get("data", [])
    
    except requests.exceptions.RequestException as e:
        sys_logger.error("okx_api", f"API request failed: {e}")
        raise RuntimeError(f"OKX API request failed: {e}")


class MarketService:
    """OKX 行情数据服务（基于 okx CLI）"""

    # ─── 公开接口（无需 API Key）───

    def get_ticker(self, symbol: str = "BTC-USDT") -> dict:
        """获取单个交易对最新行情"""
        inst_id = _to_okx_instId(symbol)
        data = _run_okx(["market", "ticker", inst_id])
        if isinstance(data, list):
            data = data[0] if data else {}
        if not data:
            raise RuntimeError(f"No data for {inst_id}")

        last = float(data.get("last", 0))
        open_24h = float(data.get("open24h", 0))
        change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h else 0

        return {
            "symbol": inst_id,
            "price": last,
            "open": open_24h,
            "high": float(data.get("high24h", 0)),
            "low": float(data.get("low24h", 0)),
            "volume": float(data.get("vol24h", 0)),
            "quote_volume": float(data.get("volCcy24h", 0)),
            "change_24h": change_pct,
            "best_bid": float(data.get("bidPx", 0)) if data.get("bidPx") else None,
            "best_ask": float(data.get("askPx", 0)) if data.get("askPx") else None,
            "timestamp": int(data.get("ts", 0)),
        }

    def get_klines(
        self,
        symbol: str = "BTC-USDT",
        timeframe: str = "1h",
        limit: int = 200,
    ) -> list:
        """获取K线数据（支持分页获取超过300根）"""
        inst_id = _to_okx_instId(symbol)
        bar = TIMEFRAME_MAP.get(timeframe, "1H")

        # OKX API限制每次最多300根，需要分页获取
        all_klines = []
        max_per_request = 300
        after_ts = None  # 使用after参数获取更早的数据

        while len(all_klines) < limit:
            # 计算本次获取数量
            fetch_limit = min(max_per_request, limit - len(all_klines))

            # 构建命令
            args = ["market", "candles", inst_id, "--bar", bar, "--limit", str(fetch_limit)]
            if after_ts:
                args.extend(["--after", str(after_ts)])

            data = _run_okx(args)

            if not isinstance(data, list) or len(data) == 0:
                break

            # 解析K线
            batch = []
            for candle in data:
                if isinstance(candle, dict):
                    ts_ms = int(candle.get("ts", 0))
                    batch.append({
                        "timestamp": ts_ms,
                        "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
                        "open": float(candle.get("o", 0)),
                        "high": float(candle.get("h", 0)),
                        "low": float(candle.get("l", 0)),
                        "close": float(candle.get("c", 0)),
                        "volume": float(candle.get("vol", 0)),
                        "quote_volume": float(candle.get("volCcy", 0)),
                    })
                elif isinstance(candle, (list, tuple)) and len(candle) >= 6:
                    ts_ms = int(candle[0])
                    batch.append({
                        "timestamp": ts_ms,
                        "time": datetime.fromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d %H:%M"),
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": float(candle[5]),
                        "quote_volume": float(candle[6]) if len(candle) > 6 else 0,
                    })

            all_klines.extend(batch)

            # OKX返回倒序（最新在前），最早的在最后
            # 使用after参数获取更早的数据，传入当前最早的时间戳
            if batch:
                after_ts = min(k["timestamp"] for k in batch)
            else:
                break

            # 如果本次获取的数据为空，说明没有更多数据了
            if len(data) == 0:
                break

        # OKX 返回倒序（最新在前），反转为时间正序
        all_klines.sort(key=lambda x: x["timestamp"])
        return all_klines[:limit]

    def get_symbols(self, inst_type: str = "SPOT") -> list:
        """获取支持的交易对列表"""
        data = _run_okx(["market", "instruments", "--instType", inst_type])
        if not isinstance(data, list):
            return POPULAR_SYMBOLS

        usdt_pairs = []
        for item in data:
            if isinstance(item, dict) and item.get("quoteCcy") == "USDT" and item.get("state") == "live":
                base = item.get("baseCcy", "")
                name = next((s["name"] for s in POPULAR_SYMBOLS if s["base"] == base), base)
                usdt_pairs.append({
                    "symbol": item.get("instId", ""),
                    "base": base,
                    "name": name,
                    "min_size": item.get("minSz", ""),
                    "tick_size": item.get("tickSz", ""),
                })

        known = {s["symbol"] for s in POPULAR_SYMBOLS}
        usdt_pairs.sort(key=lambda x: (x["symbol"] not in known, x["symbol"]))
        return usdt_pairs

    def get_multi_tickers(self, symbols: list = None) -> list:
        """批量获取行情（用 tickers 命令一次拉所有 SPOT）"""
        if symbols is None:
            symbols = [s["symbol"] for s in POPULAR_SYMBOLS[:10]]

        data = _run_okx(["market", "tickers", "SPOT"])
        if not isinstance(data, list):
            # fallback: 逐个查
            results = []
            for sym in symbols:
                try:
                    results.append(self.get_ticker(sym))
                except Exception:
                    pass
            return results

        ticker_map = {}
        for t in data:
            if isinstance(t, dict):
                ticker_map[t.get("instId", "")] = t

        results = []
        for sym in symbols:
            inst_id = _to_okx_instId(sym)
            t = ticker_map.get(inst_id)
            if not t:
                continue
            last = float(t.get("last", 0))
            open_24h = float(t.get("open24h", 0))
            change_pct = round((last - open_24h) / open_24h * 100, 2) if open_24h else 0
            results.append({
                "symbol": inst_id,
                "price": last,
                "open": open_24h,
                "high": float(t.get("high24h", 0)),
                "low": float(t.get("low24h", 0)),
                "volume": float(t.get("vol24h", 0)),
                "quote_volume": float(t.get("volCcy24h", 0)),
                "change_24h": change_pct,
                "timestamp": int(t.get("ts", 0)),
            })
        return results

    def get_indicator(self, symbol: str, indicator: str, bar: str = "1D", limit: int = 10) -> list:
        """获取技术指标数据"""
        inst_id = _to_okx_instId(symbol)
        # 合约 instId 需要加 -SWAP
        if "-SWAP" not in inst_id and "-SWAP" not in indicator:
            inst_id = inst_id.replace("-USDT", "-USDT-SWAP")
        data = _run_okx(["market", "indicator", indicator, inst_id, "--bar", bar, "--limit", str(limit)])
        return data if isinstance(data, list) else []

    def get_funding_rate(self, symbol: str = "BTC-USDT-SWAP", history: bool = False, limit: int = 10) -> list:
        """获取资金费率"""
        args = ["market", "funding-rate", symbol, "--limit", str(limit)]
        if history:
            args.append("--history")
        data = _run_okx(args)
        return data if isinstance(data, list) else []

    # ─── 认证接口（需要 API Key，通过环境变量传递给 OKX CLI）───

    def get_account_balance(self, ccy: str = "") -> dict:
        """获取账户余额（OKX CLI 通过 OKX_DEMO 环境变量区分模拟/实盘）"""
        args = ["account", "balance"]
        if ccy:
            args.append(ccy)
        data = _run_okx(args)

        if isinstance(data, list) and data:
            acc = data[0] if isinstance(data[0], dict) else {}
            details = []
            for d in acc.get("details", []):
                if float(d.get("eq", 0)) > 0:
                    details.append({
                        "currency": d["ccy"],
                        "equity": float(d["eq"]),
                        "available": float(d.get("availBal", 0)),
                        "frozen": float(d.get("frozenBal", 0)),
                    })
            return {
                "total_equity": float(acc.get("totalEq", 0)),
                "total_margin": float(acc.get("totalMargin", 0)),
                "total_unrealized_pnl": float(acc.get("totalUTwProfit", 0)),
                "details": details,
            }
        return {"total_equity": 0, "details": []}

    def get_account_uid(self) -> Optional[str]:
        """获取OKX账户UID（通过account config命令）"""
        try:
            # account config 返回的是表格格式，不是JSON
            result = subprocess.run(
                [OKX_CLI, "account", "config"],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
                env=_build_env(),
            )

            if result.returncode != 0:
                sys_logger.error(f"[Market] account config失败: {result.stderr}")
                return None

            # 解析表格格式: "uid                   386026878689006840"
            output = result.stdout.strip()
            for line in output.split("\n"):
                if line.strip().startswith("uid"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
        except Exception as e:
            sys_logger.error(f"[Market] 获取UID失败: {e}")
        return None

    def get_positions(self) -> list:
        """获取持仓列表"""
        data = _run_okx(["account", "positions"])
        if not isinstance(data, list):
            return []
        results = []
        for p in data:
            if isinstance(p, dict):
                def _sf(val, default=0.0):
                    """Safe float: handle OKX empty string values"""
                    try:
                        return float(val) if val not in (None, "", "None") else default
                    except (ValueError, TypeError):
                        return default
                results.append({
                    "symbol": p.get("instId", ""),
                    "side": p.get("posSide", ""),
                    "size": _sf(p.get("pos", 0)),
                    "avg_price": _sf(p.get("avgPx", 0)),
                    "unrealized_pnl": _sf(p.get("upl", 0)),
                    "leverage": p.get("lever", ""),
                    "margin": _sf(p.get("margin", 0)),
                })
        return results

    def get_orders_pending(self, inst_type: str = "SPOT") -> list:
        """获取未成交委托"""
        data = _run_okx(["spot", "orders"])
        if not isinstance(data, list):
            return []
        results = []
        for o in data:
            if isinstance(o, dict):
                results.append({
                    "order_id": o.get("ordId", ""),
                    "symbol": o.get("instId", ""),
                    "side": o.get("side", ""),
                    "type": o.get("ordType", ""),
                    "price": float(o.get("px", 0)),
                    "size": float(o.get("sz", 0)),
                    "filled": float(o.get("fillSz", 0)),
                    "state": o.get("state", ""),
                    "created_at": int(o.get("cTime", 0)),
                })
        return results

    def get_funding_balance(self) -> dict:
        """获取资金账户余额"""
        data = _run_okx(["account", "asset-balance"])
        if isinstance(data, list) and data:
            acc = data[0] if isinstance(data[0], dict) else {}
            details = []
            for d in acc.get("details", []):
                bal = float(d.get("bal", 0))
                avail = float(d.get("availBal", 0))
                if bal > 0 or avail > 0:
                    details.append({
                        "currency": d.get("ccy", ""),
                        "balance": bal,
                        "available": avail,
                        "frozen": float(d.get("frozenBal", 0)),
                    })
            return {
                "total_equity": float(acc.get("totalBal", 0)),
                "details": details,
            }
        return {"total_equity": 0, "details": []}

    def get_bills(self, limit: int = 20, inst_type: str = "") -> list:
        """获取账户账单流水"""
        args = ["account", "bills", "--limit", str(limit)]
        if inst_type:
            args.extend(["--instType", inst_type])
        data = _run_okx(args)
        if not isinstance(data, list):
            return []
        results = []
        for b in data:
            if isinstance(b, dict):
                results.append({
                    "bill_id": b.get("billId", ""),
                    "symbol": b.get("instId", ""),
                    "type": b.get("type", ""),
                    "side": b.get("side", ""),
                    "currency": b.get("ccy", ""),
                    "amount": float(b.get("balChg", 0) or 0),
                    "pnl": float(b.get("pnl", 0) or 0),
                    "fee": float(b.get("fee", 0) or 0),
                    "px": float(b.get("px", 0) or 0),
                    "sz": float(b.get("sz", 0) or 0),
                    "fill_px": float(b.get("fillPx", 0) or 0),
                    "fill_sz": float(b.get("fillSz", 0) or 0),
                    "account_equity": float(b.get("accountEq", 0) or 0),
                    "timestamp": int(b.get("ts", 0) or 0),
                })
        return results


# 单例
market_service = MarketService()
