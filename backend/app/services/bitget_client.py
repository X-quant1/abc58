"""Bitget REST API 客户端

自动适配：Linux用 aiohttp(高并发)，Windows用 requests+线程(兼容)
"""
import hashlib, hmac, base64, json, os, sys
from datetime import datetime
from typing import Optional, Dict, Any, List

from app.services.logger import sys_logger

# 判断平台
IS_LINUX = sys.platform == 'linux'

if IS_LINUX:
    import aiohttp

class BitgetAPIError(Exception):
    def __init__(self, code: str, msg: str, data: Any = None):
        self.code = code; self.msg = msg; self.data = data
        super().__init__(f"Bitget API Error [{code}]: {msg}")


class BitgetClient:
    """Bitget REST API 客户端"""
    
    BASE_URL = "https://api.bitget.com"
    
    def __init__(self, api_key: str = None, secret_key: str = None, passphrase: str = None):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self._session = None  # aiohttp
    
    async def _ensure_session(self):
        if IS_LINUX and (self._session is None or self._session.closed):
            connector = aiohttp.TCPConnector(ssl=False, force_close=True)
            self._session = aiohttp.ClientSession(
                connector=connector, timeout=aiohttp.ClientTimeout(total=15))
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        if not self.secret_key:
            return ""
        message = f"{timestamp}{method}{path}{body}"
        mac = hmac.new(bytes(self.secret_key, 'utf8'), bytes(message, 'utf-8'),
                       digestmod=hashlib.sha256)
        return base64.b64encode(mac.digest()).decode('utf-8')
    
    def _headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        sign = self._sign(ts, method, path, body)
        return {
            "ACCESS-KEY": self.api_key, "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": ts, "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json", "locale": "zh-CN",
        }
    
    def _build_path(self, path: str, params: Dict = None) -> str:
        if params:
            pairs = [f"{k}={params[k]}" for k in sorted(params.keys())]
            return path + "?" + "&".join(pairs)
        return path
    
    async def _request(self, method: str, path: str, params: Dict = None, body: Dict = None) -> Dict:
        path_with_params = self._build_path(path, params)
        body_str = json.dumps(body) if body else ""
        url = self.BASE_URL + path_with_params
        headers = self._headers(method, path_with_params, body_str)
        
        if IS_LINUX:
            return await self._request_aiohttp(method, url, headers, body)
        else:
            return await self._request_sync(method, url, headers, body)
    
    async def _request_aiohttp(self, method: str, url: str, headers: Dict, body: Dict) -> Dict:
        await self._ensure_session()
        try:
            if method == "GET":
                async with self._session.get(url, headers=headers) as resp:
                    data = await resp.json()
            else:
                async with self._session.post(url, headers=headers, json=body) as resp:
                    data = await resp.json()
            if data.get("code") != "00000":
                raise BitgetAPIError(data.get("code", "?"), data.get("msg", "?"))
            return data.get("data", {})
        except BitgetAPIError:
            raise
        except Exception as e:
            raise BitgetAPIError(code="NETWORK", msg=str(e))
    
    async def _request_sync(self, method: str, url: str, headers: Dict, body: Dict) -> Dict:
        import asyncio
        def _do():
            import requests, urllib3, ssl
            from requests.adapters import HTTPAdapter
            from urllib3.util.ssl_ import create_urllib3_context

            class TLSAdapter(HTTPAdapter):
                """修复 Windows SSL 兼容性"""
                def init_poolmanager(self, *args, **kwargs):
                    ctx = create_urllib3_context()
                    ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    kwargs['ssl_context'] = ctx
                    return super().init_poolmanager(*args, **kwargs)

            urllib3.disable_warnings()
            try:
                session = requests.Session()
                session.mount('https://', TLSAdapter())
                if method == "GET":
                    resp = session.get(url, headers=headers, timeout=15, verify=False)
                else:
                    resp = session.post(url, headers=headers, json=body, timeout=15, verify=False)
                data = resp.json()
                if data.get("code") != "00000":
                    raise BitgetAPIError(data.get("code", "?"), data.get("msg", "?"))
                return data.get("data", {})
            except BitgetAPIError:
                raise
            except Exception as e:
                raise BitgetAPIError(code="NETWORK", msg=str(e))
        return await asyncio.to_thread(_do)
    
    # ─── 账户 ───
    async def get_account_info(self) -> Dict:
        return await self._request("GET", "/api/v2/spot/account/info")
    
    async def get_assets(self) -> List[Dict]:
        return await self._request("GET", "/api/v2/spot/account/assets")
    
    async def get_balance(self, coin: str = "USDT") -> float:
        try:
            assets = await self.get_assets()
            if isinstance(assets, list):
                for a in assets:
                    if a.get("coin") == coin:
                        return float(a.get("available", 0))
            return 0.0
        except Exception:
            return 0.0
    
    async def get_mix_account(self, symbol: str = "BTCUSDT", margin_coin: str = "USDT") -> Dict:
        return await self._request("GET", "/api/v2/mix/account/account",
            params={"symbol": symbol, "marginCoin": margin_coin, "productType": "USDT-FUTURES"})

    async def set_position_mode(self, pos_mode: str = "hedge_mode",
                                  margin_coin: str = "USDT") -> Dict:
        """设置持仓模式

        Args:
            pos_mode: "hedge_mode"（双向持仓）或 "one_way_mode"（单向持仓）
            margin_coin: 保证金币种
        """
        return await self._request("POST", "/api/v2/mix/account/set-position-mode",
            body={"posMode": pos_mode, "marginCoin": margin_coin, "productType": "USDT-FUTURES"})

    # ─── 行情 ───
    async def get_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        data = await self._request("GET", "/api/v2/mix/market/ticker",
            params={"symbol": symbol, "productType": "USDT-FUTURES"})
        if isinstance(data, list) and data:
            return data[0]
        return {}
    
    async def get_tickers(self, product_type: str = "USDT-FUTURES") -> List[Dict]:
        return await self._request("GET", "/api/v2/mix/market/tickers",
            params={"productType": product_type})
    
    async def get_klines(self, symbol: str, granularity: str = "1H", limit: int = 100) -> List:
        return await self._request("GET", "/api/v2/mix/market/candles",
            params={"symbol": symbol, "productType": "USDT-FUTURES",
                    "granularity": granularity, "limit": str(limit)})
    
    async def get_contracts(self, product_type: str = "USDT-FUTURES") -> List[Dict]:
        return await self._request("GET", "/api/v2/mix/market/contracts",
            params={"productType": product_type})


# 单例
_client_instance: Optional[BitgetClient] = None

def get_client() -> Optional[BitgetClient]:
    return _client_instance

def init_client(api_key: str, secret_key: str, passphrase: str):
    global _client_instance
    _client_instance = BitgetClient(api_key, secret_key, passphrase)
    return _client_instance

def reset_client():
    global _client_instance
    _client_instance = None
