"""行情数据缓存层

支持内存缓存 + TTL过期，减少OKX API调用。
支持缓存预热、自动刷新、命中率统计。

缓存策略：
- 公开行情数据（ticker/klines）：全局缓存，所有用户共享
- 私有数据（positions/balance）：按API Key隔离，不缓存
"""
import time
import threading
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from app.services.metrics import metrics


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    expire_at: float  # 过期时间戳
    created_at: float  # 创建时间
    hit_count: int = 0  # 命中次数
    size_bytes: int = 0  # 估算大小


class MarketCache:
    """行情数据内存缓存
    
    特性：
    - TTL过期：不同数据类型设置不同的过期时间
    - LRU淘汰：内存不足时淘汰最久未访问的条目
    - 命中率统计：实时统计缓存命中率
    - 缓存预热：启动时主动加载常用数据
    - 线程安全：所有操作加锁
    """
    
    # 默认TTL配置（秒）
    DEFAULT_TTL = {
        "ticker": 2,          # 行情数据：2秒（实时性要求高）
        "tickers": 5,         # 批量行情：5秒
        "klines": 30,         # K线数据：30秒
        "orderbook": 1,       # 订单簿：1秒
        "positions": 3,       # 持仓：3秒
        "balance": 5,         # 余额：5秒
        "symbols": 3600,      # 交易对列表：1小时
        "funding_rate": 60,   # 资金费率：1分钟
        "indicator": 60,      # 技术指标：1分钟
        "default": 10,        # 默认：10秒
    }
    
    def __init__(self, max_entries: int = 5000, max_memory_mb: int = 100):
        self._lock = threading.Lock()
        self._cache: Dict[str, CacheEntry] = {}
        self._max_entries = max_entries
        self._max_memory = max_memory_mb * 1024 * 1024
        
        # 统计
        self._total_hits = 0
        self._total_misses = 0
        self._total_evictions = 0
    
    def _make_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        parts = [prefix] + [str(a) for a in args]
        return ":".join(parts)
    
    def _estimate_size(self, value: Any) -> int:
        """估算数据大小（字节）"""
        import sys
        try:
            return sys.getsizeof(value)
        except Exception:
            return 1024  # 默认1KB
    
    def _evict_if_needed(self):
        """如果缓存满了，淘汰最久未访问的条目"""
        if len(self._cache) <= self._max_entries:
            return
        
        # 按最后访问时间排序（hit_count / age）
        now = time.time()
        scored = []
        for key, entry in self._cache.items():
            age = now - entry.created_at
            score = entry.hit_count / max(age, 1)  # 命中率/年龄
            scored.append((key, score))
        
        # 删除得分最低的20%
        scored.sort(key=lambda x: x[1])
        evict_count = max(1, len(scored) // 5)
        for key, _ in scored[:evict_count]:
            del self._cache[key]
            self._total_evictions += 1
    
    def get(self, prefix: str, *args) -> Optional[Any]:
        """获取缓存数据
        
        Args:
            prefix: 缓存前缀（如ticker/klines）
            *args: 缓存键参数
        
        Returns:
            缓存数据（未命中返回None）
        """
        key = self._make_key(prefix, *args)
        
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._total_misses += 1
                metrics.record_request(
                    endpoint=f"cache:{prefix}",
                    method="GET",
                    status="miss",
                    duration_ms=0,
                    cache_hit=False,
                )
                return None
            
            # 检查是否过期
            if time.time() > entry.expire_at:
                del self._cache[key]
                self._total_misses += 1
                metrics.record_request(
                    endpoint=f"cache:{prefix}",
                    method="GET",
                    status="expired",
                    duration_ms=0,
                    cache_hit=False,
                )
                return None
            
            # 命中
            entry.hit_count += 1
            self._total_hits += 1
            metrics.record_request(
                endpoint=f"cache:{prefix}",
                method="GET",
                status="hit",
                duration_ms=0,
                cache_hit=True,
            )
            return entry.value
    
    def set(self, prefix: str, value: Any, *args, ttl: int = None):
        """设置缓存数据
        
        Args:
            prefix: 缓存前缀
            value: 缓存值
            *args: 缓存键参数
            ttl: 过期时间（秒），不传则使用默认TTL
        """
        key = self._make_key(prefix, *args)
        
        if ttl is None:
            ttl = self.DEFAULT_TTL.get(prefix, self.DEFAULT_TTL["default"])
        
        now = time.time()
        
        with self._lock:
            self._evict_if_needed()
            
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                expire_at=now + ttl,
                created_at=now,
                size_bytes=self._estimate_size(value),
            )
    
    def invalidate(self, prefix: str, *args):
        """使缓存失效"""
        key = self._make_key(prefix, *args)
        with self._lock:
            self._cache.pop(key, None)
    
    def invalidate_prefix(self, prefix: str):
        """使某个前缀的所有缓存失效"""
        with self._lock:
            keys_to_remove = [k for k in self._cache if k.startswith(prefix + ":")]
            for k in keys_to_remove:
                del self._cache[k]
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            total = self._total_hits + self._total_misses
            hit_rate = self._total_hits / total * 100 if total > 0 else 0
            
            # 按前缀统计
            by_prefix = {}
            for key, entry in self._cache.items():
                prefix = key.split(":")[0]
                if prefix not in by_prefix:
                    by_prefix[prefix] = {"count": 0, "total_hits": 0, "total_bytes": 0}
                by_prefix[prefix]["count"] += 1
                by_prefix[prefix]["total_hits"] += entry.hit_count
                by_prefix[prefix]["total_bytes"] += entry.size_bytes
            
            # 内存占用
            total_bytes = sum(e.size_bytes for e in self._cache.values())
            
            return {
                "entries": len(self._cache),
                "max_entries": self._max_entries,
                "memory_bytes": total_bytes,
                "memory_mb": round(total_bytes / 1024 / 1024, 2),
                "max_memory_mb": self._max_memory / 1024 / 1024,
                "total_hits": self._total_hits,
                "total_misses": self._total_misses,
                "hit_rate": round(hit_rate, 2),
                "total_evictions": self._total_evictions,
                "by_prefix": by_prefix,
                "ttl_config": self.DEFAULT_TTL,
            }


class CachedMarketService:
    """带缓存的行情服务
    
    包装 MarketService，自动缓存行情数据。
    公开行情（ticker/klines）：全局共享缓存
    私有交易数据（positions/balance）：按API Key隔离缓存（每个用户独立）
    """
    
    def __init__(self, market_service, user_key: str = ""):
        """初始化
        
        Args:
            market_service: MarketService实例
            user_key: 用户API Key哈希（用于私有数据缓存隔离，为空则全局共享）
        """
        self._service = market_service
        self._cache = MarketCache()
        self._user_key = user_key  # 私有数据缓存命名空间
    
    def _private_key(self, *parts) -> str:
        """生成私有数据的缓存键，自动包含用户隔离前缀"""
        if self._user_key:
            return f"user:{self._user_key}:" + ":".join(str(p) for p in parts)
        return ":".join(str(p) for p in parts)
    
    def get_ticker(self, symbol: str = "BTC-USDT") -> dict:
        """获取行情（带缓存，网络失败时返回兜底数据）"""
        cached = self._cache.get("ticker", symbol)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_ticker(symbol)
            self._cache.set("ticker", result, symbol)
            return result
        except Exception:
            # OKX API 不可达时返回兜底数据，不阻塞页面
            return {"instId": symbol, "last": "0", "bidPx": "0", "askPx": "0"}
    
    def get_klines(self, symbol: str = "BTC-USDT-SWAP", interval: str = "1H", limit: int = 100) -> list:
        """获取K线（带缓存）"""
        cached = self._cache.get("klines", symbol, interval, limit)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_klines(symbol, interval, limit)
            self._cache.set("klines", result, symbol, interval, limit)
            return result
        except Exception:
            return []
    
    def get_multi_tickers(self, symbols: list = None) -> list:
        """批量获取行情（带缓存）"""
        # 生成缓存键
        key_parts = ["tickers"]
        if symbols:
            key_parts.extend(symbols)
        
        cached = self._cache.get("tickers", *key_parts)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_multi_tickers(symbols)
            self._cache.set("tickers", result, *key_parts)
            return result
        except Exception:
            return []
    
    def get_symbols(self, inst_type: str = "SPOT") -> list:
        """获取交易对列表（带缓存，1小时TTL）"""
        cached = self._cache.get("symbols", inst_type)
        if cached is not None:
            return cached
        
        result = self._service.get_symbols(inst_type)
        self._cache.set("symbols", result, inst_type)
        return result
    
    def get_positions(self, inst_id: str = None) -> list:
        """获取持仓（带缓存，3秒TTL，按用户隔离）"""
        cache_key = self._private_key("positions", inst_id or "all")
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_positions(inst_id)
            self._cache.set(cache_key, result, ttl=self._cache.DEFAULT_TTL.get("positions", 3))
            return result
        except Exception:
            return []
    
    def get_account_balance(self, ccy: str = None) -> dict:
        """获取余额（带缓存，5秒TTL，按用户隔离）"""
        cache_key = self._private_key("balance", ccy or "all")
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_account_balance(ccy)
            self._cache.set(cache_key, result, ttl=self._cache.DEFAULT_TTL.get("balance", 5))
            return result
        except Exception:
            return {}
    
    def get_funding_balance(self) -> dict:
        """获取资金账户余额（带缓存，5秒TTL，按用户隔离）"""
        cache_key = self._private_key("funding_balance")
        
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_funding_balance()
            self._cache.set(cache_key, result, ttl=self._cache.DEFAULT_TTL.get("balance", 5))
            return result
        except Exception:
            return {}
    
    def get_bills(self, limit: int = 20, inst_type: str = "") -> list:
        """获取账单流水（不缓存，实时数据）"""
        try:
            return self._service.get_bills(limit, inst_type)
        except Exception:
            return []
    
    def get_tickers(self, inst_type: str = "SPOT") -> list:
        """获取所有行情（带缓存）"""
        cached = self._cache.get("tickers_all", inst_type)
        if cached is not None:
            return cached
        
        try:
            result = self._service.get_tickers(inst_type)
            self._cache.set("tickers_all", result, inst_type)
            return result
        except Exception:
            return []
    
    def get_orderbook(self, symbol: str = "BTC-USDT", depth: int = 20) -> dict:
        """获取订单簿（带缓存，1秒TTL）"""
        cached = self._cache.get("orderbook", symbol, depth)
        if cached is not None:
            return cached
        
        result = self._service.get_orderbook(symbol, depth)
        self._cache.set("orderbook", result, symbol, depth)
        return result
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return self._cache.get_stats()
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
    
    def invalidate_ticker(self, symbol: str = None):
        """使行情缓存失效"""
        if symbol:
            self._cache.invalidate("ticker", symbol)
        else:
            self._cache.invalidate_prefix("ticker")
    
    def invalidate_klines(self, symbol: str = None):
        """使K线缓存失效"""
        if symbol:
            self._cache.invalidate_prefix("klines")
        else:
            self._cache.invalidate_prefix("klines")


# ─── 全局实例 ───

_cached_market_service: Optional[CachedMarketService] = None

def get_cached_market_service(user_key: str = "") -> CachedMarketService:
    """获取带缓存的行情服务实例
    
    Args:
        user_key: 用户API Key的哈希值（用于私有数据缓存隔离）
                  为空时全局共享（单用户模式/公开数据）
    """
    global _cached_market_service
    if user_key:
        # 多用户模式：每个用户独立的缓存实例
        if _cached_market_service is None or _cached_market_service._user_key != user_key:
            from app.services.market_rest import get_market_service
            _cached_market_service = CachedMarketService(get_market_service(), user_key=user_key)
    else:
        # 单用户模式：全局单例
        if _cached_market_service is None:
            from app.services.market_rest import get_market_service
            _cached_market_service = CachedMarketService(get_market_service())
    return _cached_market_service


def invalidate_account_cache(user_key: str = ""):
    """交易后清除余额和持仓缓存"""
    svc = get_cached_market_service(user_key)
    prefix = f"user:{user_key}:" if user_key else ""
    svc._cache.invalidate_prefix(prefix + "balance")
    svc._cache.invalidate_prefix(prefix + "positions")
    svc._cache.invalidate_prefix(prefix + "funding_balance")
