"""Bitget REST API 客户端

直接调用Bitget REST API，支持账户信息和余额查询。
使用HMAC-SHA256签名认证。
"""
import hashlib
import hmac
import base64
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from app.services.logger import sys_logger


class BitgetAPIError(Exception):
    """Bitget API业务错误"""
    def __init__(self, code: str, msg: str, data: Any = None):
        self.code = code
        self.msg = msg
        self.data = data
        super().__init__(f"Bitget API Error [{code}]: {msg}")


class BitgetClient:
    """Bitget REST API 客户端
    
    文档：https://www.bitget.com/api-doc/common/intro
    """
    
    BASE_URL = "https://api.bitget.com"
    
    def __init__(
        self,
        api_key: str = None,
        secret_key: str = None,
        passphrase: str = None,
    ):
        """初始化客户端
        
        Args:
            api_key: API Key
            secret_key: Secret Key
            passphrase: Passphrase
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        """生成签名
        
        Bitget签名算法：
        1. 拼接字符串：timestamp + method + path + body
        2. 使用HMAC-SHA256签名
        3. Base64编码
        
        Args:
            timestamp: 时间戳字符串
            method: HTTP方法（GET/POST）
            path: 请求路径
            body: 请求体（GET请求为空字符串）
            
        Returns:
            Base64编码的签名字符串
        """
        if not self.secret_key:
            return ""
        message = f"{timestamp}{method}{path}{body}"
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        d = mac.digest()
        return base64.b64encode(d).decode('utf-8')
    
    def _headers(self, method: str, path: str, body: str = "") -> Dict[str, str]:
        """生成请求头
        
        Args:
            method: HTTP方法
            path: 请求路径
            body: 请求体
            
        Returns:
            包含认证信息的请求头字典
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
        sign = self._sign(timestamp, method, path, body)
        
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "zh-CN",
        }
    
    def _request(self, method: str, path: str, params: Dict = None, body: Dict = None) -> Dict:
        """发送HTTP请求
        
        Args:
            method: HTTP方法
            path: 请求路径
            params: URL参数（GET请求）
            body: 请求体（POST请求）
            
        Returns:
            API响应数据
            
        Raises:
            BitgetAPIError: API错误
        """
        body_str = json.dumps(body) if body else ""
        
        # 构建完整URL（参数按key排序用于签名）
        if params:
            param_pairs = []
            for k in sorted(params.keys()):
                param_pairs.append(f"{k}={params[k]}")
            path_with_params = path + "?" + "&".join(param_pairs)
        else:
            path_with_params = path
        
        url = self.BASE_URL + path_with_params
        headers = self._headers(method, path_with_params, body_str)
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10, verify=False)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=body, timeout=10, verify=False)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            data = resp.json()
            
            # Bitget返回格式：{"code": "00000", "msg": "success", "data": {...}}
            if data.get("code") != "00000":
                raise BitgetAPIError(
                    code=data.get("code", "UNKNOWN"),
                    msg=data.get("msg", "Unknown error"),
                    data=data.get("data")
                )
            
            return data.get("data", {})
            
        except requests.exceptions.RequestException as e:
            # 尝试从响应体中提取Bitget错误信息
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    err_data = e.response.json()
                    if err_data.get("msg"):
                        error_msg = f"[{err_data.get('code')}] {err_data.get('msg')}"
                except Exception:
                    pass
            sys_logger.error("bitget_api", f"Request failed: {error_msg}")
            raise BitgetAPIError(code="NETWORK", msg=error_msg)
    
    def get_account_info(self) -> Dict:
        """获取账户信息
        
        Returns:
            账户信息字典，包含用户ID等
        """
        path = "/api/v2/spot/account/info"
        return self._request("GET", path)
    
    def get_assets(self, coin: str = None) -> List[Dict]:
        """获取账户资产
        
        Args:
            coin: 币种（可选，不传则返回所有）
            
        Returns:
            资产列表
        """
        path = "/api/v2/spot/account/assets"
        params = {}
        if coin:
            params["coin"] = coin
        return self._request("GET", path, params=params)
    
    def get_balance(self, coin: str = "USDT") -> float:
        """获取指定币种余额
        
        Args:
            coin: 币种（默认USDT）
            
        Returns:
            余额（浮点数）
        """
        try:
            # 获取所有资产，不传coin参数避免API错误
            assets = self.get_assets()
            if isinstance(assets, list):
                for asset in assets:
                    if asset.get("coin") == coin:
                        return float(asset.get("available", 0))
            return 0.0
        except Exception as e:
            sys_logger.error("bitget_api", f"Get balance failed: {e}")
            return 0.0

    # ─── 行情数据（公开API） ───
    
    def get_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """获取单个合约实时行情
        
        Args:
            symbol: 合约符号，如 BTCUSDT
            
        Returns:
            ticker数据
        """
        data = self._request("GET", "/api/v2/mix/market/ticker",
                            params={"symbol": symbol, "productType": "USDT-FUTURES"})
        # API返回数组，取第一个
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return {}
    
    def get_tickers(self, product_type: str = "USDT-FUTURES") -> List[Dict]:
        """获取所有合约实时行情
        
        Args:
            product_type: 产品类型，默认 USDT-FUTURES
            
        Returns:
            ticker列表
        """
        return self._request("GET", "/api/v2/mix/market/tickers",
                            params={"productType": product_type})
    
    def get_klines(self, symbol: str, granularity: str = "1H", limit: int = 100) -> List:
        """获取K线数据
        
        Args:
            symbol: 合约符号
            granularity: 周期，1m/5m/15m/30m/1H/4H/1D/1W
            limit: 返回条数
            
        Returns:
            K线数据列表，每根K线: [时间, 开, 高, 低, 收, 成交量, 成交额]
        """
        return self._request("GET", "/api/v2/mix/market/candles",
                            params={"symbol": symbol, "productType": "USDT-FUTURES",
                                   "granularity": granularity, "limit": str(limit)})
    
    def get_contracts(self, product_type: str = "USDT-FUTURES") -> List[Dict]:
        """获取合约列表"""
        return self._request("GET", "/api/v2/mix/market/contracts",
                            params={"productType": product_type})
    
    def get_mix_account(self, symbol: str = "BTCUSDT", margin_coin: str = "USDT") -> Dict:
        """获取合约账户信息（含余额、保证金、杠杆等）
        
        Returns:
            accountEquity: 账户权益
            available: 可用余额
            marginMode: 保证金模式
            posMode: 持仓模式
        """
        return self._request("GET", "/api/v2/mix/account/account",
                            params={"symbol": symbol, "marginCoin": margin_coin, "productType": "USDT-FUTURES"})


# 单例模式
_client_instance: Optional[BitgetClient] = None


def get_client() -> Optional[BitgetClient]:
    """获取全局客户端实例"""
    return _client_instance


def init_client(api_key: str, secret_key: str, passphrase: str):
    """初始化全局客户端"""
    global _client_instance
    _client_instance = BitgetClient(api_key, secret_key, passphrase)
    return _client_instance


def reset_client():
    """重置客户端实例"""
    global _client_instance
    _client_instance = None
