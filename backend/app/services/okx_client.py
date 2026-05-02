"""OKX REST API 客户端

直接调用OKX REST API，无需依赖CLI工具。
支持异步调用，适合高并发场景。
内置限频和429重试机制。
"""
import hashlib
import hmac
import base64
import json
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import aiohttp
import requests

from app import config
from app.services.logger import sys_logger


class OKXAPIError(Exception):
    """OKX API业务错误"""
    def __init__(self, code: str, msg: str, data: Any = None):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(f"OKX API Error [{code}]: {msg}")


class AsyncRateLimiter:
    """异步限频器
    
    OKX REST API 限频规则：
    - 公开接口：20次/2秒
    - 私有接口：10次/2秒
    本限频器采用更保守的策略，避免429错误。
    """
    
    def __init__(self, max_calls: int = 8, window_sec: float = 2.0):
        self._max_calls = max_calls
        self._window_sec = window_sec
        self._timestamps: List[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """获取一个请求令牌，如果超限则等待"""
        async with self._lock:
            now = time.time()
            # 清理过期的记录
            cutoff = now - self._window_sec
            self._timestamps = [t for t in self._timestamps if t > cutoff]
            
            if len(self._timestamps) >= self._max_calls:
                # 需要等待最早的请求过期
                wait_time = self._timestamps[0] + self._window_sec - now + 0.1
                if wait_time > 0:
                    sys_logger.info("rate_limit", f"Rate limit: waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)
            
            self._timestamps.append(time.time())


class OKXClient:
    """OKX REST API 客户端
    
    支持同步和异步两种调用方式。
    异步方式适合高并发场景（1000+用户）。
    """
    
    BASE_URL = "https://www.okx.com"
    
    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        passphrase: str = None,
        sandbox: bool = None,
    ):
        """初始化客户端
        
        Args:
            api_key: API Key（不传则使用全局配置）
            secret_key: Secret Key
            passphrase: Passphrase
            sandbox: 是否使用模拟盘
        """
        self.api_key = api_key or config.OKX_API_KEY
        self.secret_key = secret_key or config.OKX_SECRET_KEY
        self.passphrase = passphrase or config.OKX_PASSPHRASE
        self.sandbox = sandbox if sandbox is not None else (config.OKX_SANDBOX.lower() == "true")
        
        # 异步限频器（8次/2秒，保守策略）
        self._rate_limiter = AsyncRateLimiter(max_calls=8, window_sec=2.0)
        
        # 标记是否已配置 API Key（公开接口不需要）
        self.has_credentials = all([self.api_key, self.secret_key, self.passphrase])
    
    def _generate_signature(self, timestamp: str, method: str, endpoint: str, body: str = "") -> str:
        """生成API签名
        
        Args:
            timestamp: 时间戳
            method: HTTP方法
            endpoint: API路径
            body: 请求体
        
        Returns:
            签名字符串
        """
        pre_hash = timestamp + method + endpoint + body
        secret = self.secret_key.encode('utf-8')
        msg = pre_hash.encode('utf-8')
        signature = base64.b64encode(hmac.new(secret, msg, hashlib.sha256).digest()).decode('utf-8')
        return signature
    
    def _get_headers(self, method: str, endpoint: str, body: str = "") -> Dict[str, str]:
        """生成请求头
        
        Args:
            method: HTTP方法
            endpoint: API路径
            body: 请求体
        
        Returns:
            请求头字典
        """
        headers = {
            'Content-Type': 'application/json',
        }
        
        # 只有在有 API Key 时才添加签名（私有接口需要）
        if self.has_credentials:
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            signature = self._generate_signature(timestamp, method, endpoint, body)
            
            headers['OK-ACCESS-KEY'] = self.api_key
            headers['OK-ACCESS-SIGN'] = signature
            headers['OK-ACCESS-TIMESTAMP'] = timestamp
            headers['OK-ACCESS-PASSPHRASE'] = self.passphrase
            
            if self.sandbox:
                headers['x-simulated-trading'] = '1'
        
        return headers
    
    def _handle_response(self, response_data: Dict) -> Any:
        """处理API响应
        
        Args:
            response_data: 响应数据
        
        Returns:
            data字段的内容
        
        Raises:
            OKXAPIError: API业务错误
        """
        code = response_data.get("code", "")
        msg = response_data.get("msg", "")
        data = response_data.get("data", [])
        
        if code != "0":
            sys_logger.error("okx_api", f"API error: [{code}] {msg}")
            raise OKXAPIError(code, msg, data)
        
        return data
    
    # ─── 同步方法 ───
    
    def request(self, method: str, endpoint: str, body: Dict = None) -> Any:
        """同步请求（兼容现有代码）
        
        Args:
            method: HTTP方法 (GET/POST)
            endpoint: API路径
            body: 请求体
        
        Returns:
            API响应数据
        """
        body_str = json.dumps(body, separators=(',', ':')) if body and method == "POST" else ""
        headers = self._get_headers(method, endpoint, body_str)
        url = self.BASE_URL + endpoint
        
        try:
            sys_logger.info("okx_api", f"Request: {method} {endpoint}")
            
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=(3, 10))
            elif method == "POST":
                response = requests.post(url, headers=headers, data=body_str, timeout=(3, 10))
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            data = response.json()
            
            return self._handle_response(data)
        
        except requests.exceptions.RequestException as e:
            sys_logger.error("okx_api", f"Request failed: {e}")
            raise RuntimeError(f"OKX API request failed: {e}")
    
    # ─── 异步方法 ───
    
    async def async_request(self, method: str, endpoint: str, body: Dict = None, session: aiohttp.ClientSession = None) -> Any:
        """异步请求（高并发场景，带限频和429重试）
        
        Args:
            method: HTTP方法 (GET/POST)
            endpoint: API路径
            body: 请求体
            session: aiohttp会话（复用连接，强烈建议传入）
        
        Returns:
            API响应数据
        """
        body_str = json.dumps(body, separators=(',', ':')) if body and method == "POST" else ""
        url = self.BASE_URL + endpoint
        
        # 是否使用外部session
        own_session = session is None
        timeout = aiohttp.ClientTimeout(total=30, connect=15, sock_read=20)
        
        # 最大重试次数
        max_retries = 3
        
        try:
            if own_session:
                connector = aiohttp.TCPConnector(
                    limit=100,
                    limit_per_host=20,
                    ttl_dns_cache=300,
                    use_dns_cache=True,
                )
                session = aiohttp.ClientSession(connector=connector, trust_env=True)
            
            for attempt in range(max_retries):
                # 限频等待
                await self._rate_limiter.acquire()
                
                # 每次重试需要新的签名（时间戳不同）
                headers = self._get_headers(method, endpoint, body_str)
                
                try:
                    if method == "GET":
                        async with session.get(url, headers=headers, timeout=timeout) as response:
                            if response.status == 429:
                                retry_after = float(response.headers.get("Retry-After", "1"))
                                sys_logger.warn("okx_api", f"429 rate limited, retry after {retry_after}s (attempt {attempt+1}/{max_retries})")
                                await asyncio.sleep(retry_after + 0.5)
                                continue
                            response.raise_for_status()
                            data = await response.json()
                    elif method == "POST":
                        async with session.post(url, headers=headers, data=body_str, timeout=timeout) as response:
                            if response.status == 429:
                                retry_after = float(response.headers.get("Retry-After", "1"))
                                sys_logger.warn("okx_api", f"429 rate limited, retry after {retry_after}s (attempt {attempt+1}/{max_retries})")
                                await asyncio.sleep(retry_after + 0.5)
                                continue
                            response.raise_for_status()
                            data = await response.json()
                    else:
                        raise ValueError(f"Unsupported method: {method}")
                    
                    return self._handle_response(data)
                
                except aiohttp.ClientResponseError as e:
                    if e.status == 429 and attempt < max_retries - 1:
                        wait = 2 ** (attempt + 1)  # 指数退避: 2, 4, 8
                        sys_logger.warn("okx_api", f"429 error, backing off {wait}s (attempt {attempt+1}/{max_retries})")
                        await asyncio.sleep(wait)
                        continue
                    raise
            
            # 所有重试失败
            raise RuntimeError(f"OKX API request failed after {max_retries} retries: {endpoint}")
        
        except aiohttp.ClientError as e:
            sys_logger.error("okx_api", f"Async request failed: {e}")
            raise RuntimeError(f"OKX API async request failed: {e}")
        
        finally:
            if own_session and session:
                await session.close()
    
    # ─── 便捷方法 ───
    
    def get(self, endpoint: str) -> Any:
        """GET请求"""
        return self.request("GET", endpoint)
    
    def post(self, endpoint: str, body: Dict) -> Any:
        """POST请求"""
        return self.request("POST", endpoint, body)
    
    async def async_get(self, endpoint: str, session: aiohttp.ClientSession = None) -> Any:
        """异步GET请求"""
        return await self.async_request("GET", endpoint, session=session)
    
    async def async_post(self, endpoint: str, body: Dict, session: aiohttp.ClientSession = None) -> Any:
        """异步POST请求"""
        return await self.async_request("POST", endpoint, body, session)


# ─── 全局客户端实例（使用全局配置）───

_client: Optional[OKXClient] = None

def get_client() -> OKXClient:
    """获取全局客户端实例"""
    global _client
    if _client is None:
        _client = OKXClient()
    return _client

def reset_client():
    """重置客户端（配置变更时调用）"""
    global _client
    _client = None
