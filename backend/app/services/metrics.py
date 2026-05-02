"""OKX API 性能监控指标

轻量级 Prometheus 风格监控，无需额外依赖。
支持请求计数、延迟直方图、错误率、缓存命中率等指标。
"""
import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta


@dataclass
class RequestMetric:
    """单个请求指标"""
    endpoint: str
    method: str
    status: str  # success / error / timeout
    duration_ms: float
    timestamp: float
    cache_hit: bool = False
    error_code: str = ""


class MetricsCollector:
    """性能指标收集器（线程安全）
    
    收集的指标：
    - api_requests_total: API请求总数（按端点/方法/状态分组）
    - api_request_duration_ms: API请求延迟（毫秒）
    - api_errors_total: API错误总数
    - cache_hits_total: 缓存命中次数
    - cache_misses_total: 缓存未命中次数
    - active_connections: 活跃连接数
    - rate_limit_waits: 限频等待次数
    """
    
    def __init__(self, max_history: int = 10000):
        self._lock = threading.Lock()
        self._max_history = max_history
        
        # 请求记录（最近N条）
        self._history: List[RequestMetric] = []
        
        # 聚合计数器
        self._counters: Dict[str, int] = defaultdict(int)
        self._error_counts: Dict[str, int] = defaultdict(int)
        
        # 延迟统计（按端点分组）
        self._latencies: Dict[str, List[float]] = defaultdict(list)
        
        # 缓存统计
        self._cache_hits = 0
        self._cache_misses = 0
        
        # 限频统计
        self._rate_limit_waits = 0
        self._rate_limit_wait_time_ms = 0.0
        
        # 活跃连接
        self._active_connections = 0
        self._peak_connections = 0
        
        # 启动时间
        self._start_time = time.time()
    
    def record_request(
        self,
        endpoint: str,
        method: str = "GET",
        status: str = "success",
        duration_ms: float = 0,
        cache_hit: bool = False,
        error_code: str = "",
    ):
        """记录一次API请求
        
        Args:
            endpoint: API端点
            method: HTTP方法
            status: success / error / timeout
            duration_ms: 耗时（毫秒）
            cache_hit: 是否缓存命中
            error_code: OKX错误码
        """
        metric = RequestMetric(
            endpoint=endpoint,
            method=method,
            status=status,
            duration_ms=duration_ms,
            timestamp=time.time(),
            cache_hit=cache_hit,
            error_code=error_code,
        )
        
        with self._lock:
            # 记录历史
            self._history.append(metric)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            
            # 更新计数器
            key = f"{method}:{endpoint}:{status}"
            self._counters[key] += 1
            
            # 错误计数
            if status != "success":
                err_key = f"{error_code or status}:{endpoint}"
                self._error_counts[err_key] += 1
            
            # 延迟记录
            lat_key = f"{method}:{endpoint}"
            self._latencies[lat_key].append(duration_ms)
            # 只保留最近1000条延迟
            if len(self._latencies[lat_key]) > 1000:
                self._latencies[lat_key] = self._latencies[lat_key][-1000:]
            
            # 缓存统计
            if cache_hit:
                self._cache_hits += 1
            else:
                self._cache_misses += 1
    
    def record_rate_limit_wait(self, wait_ms: float):
        """记录限频等待"""
        with self._lock:
            self._rate_limit_waits += 1
            self._rate_limit_wait_time_ms += wait_ms
    
    def increment_connections(self):
        """活跃连接+1"""
        with self._lock:
            self._active_connections += 1
            if self._active_connections > self._peak_connections:
                self._peak_connections = self._active_connections
    
    def decrement_connections(self):
        """活跃连接-1"""
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)
    
    def get_summary(self, minutes: int = 5) -> dict:
        """获取指标摘要
        
        Args:
            minutes: 最近N分钟的统计
        
        Returns:
            指标摘要字典
        """
        now = time.time()
        cutoff = now - minutes * 60
        
        with self._lock:
            # 过滤最近N分钟的记录
            recent = [m for m in self._history if m.timestamp >= cutoff]
            
            if not recent:
                return {
                    "period_minutes": minutes,
                    "total_requests": 0,
                    "qps": 0,
                    "avg_latency_ms": 0,
                    "p50_latency_ms": 0,
                    "p95_latency_ms": 0,
                    "p99_latency_ms": 0,
                    "error_rate": 0,
                    "cache_hit_rate": 0,
                    "active_connections": self._active_connections,
                    "peak_connections": self._peak_connections,
                    "uptime_seconds": int(now - self._start_time),
                }
            
            # 总请求数
            total = len(recent)
            
            # QPS
            time_span = max(now - recent[0].timestamp, 1)
            qps = total / time_span
            
            # 延迟统计
            durations = [m.duration_ms for m in recent if m.duration_ms > 0]
            durations.sort()
            
            avg_latency = sum(durations) / len(durations) if durations else 0
            p50 = durations[len(durations) // 2] if durations else 0
            p95 = durations[int(len(durations) * 0.95)] if durations else 0
            p99 = durations[int(len(durations) * 0.99)] if durations else 0
            max_latency = durations[-1] if durations else 0
            min_latency = durations[0] if durations else 0
            
            # 错误率
            errors = len([m for m in recent if m.status != "success"])
            error_rate = errors / total * 100 if total > 0 else 0
            
            # 缓存命中率
            hits = len([m for m in recent if m.cache_hit])
            cache_rate = hits / total * 100 if total > 0 else 0
            
            # 按端点统计
            by_endpoint = defaultdict(lambda: {"count": 0, "errors": 0, "total_ms": 0})
            for m in recent:
                key = m.endpoint
                by_endpoint[key]["count"] += 1
                if m.status != "success":
                    by_endpoint[key]["errors"] += 1
                by_endpoint[key]["total_ms"] += m.duration_ms
            
            endpoint_stats = []
            for ep, stats in sorted(by_endpoint.items(), key=lambda x: -x[1]["count"]):
                avg_ep = stats["total_ms"] / stats["count"] if stats["count"] > 0 else 0
                endpoint_stats.append({
                    "endpoint": ep,
                    "requests": stats["count"],
                    "errors": stats["errors"],
                    "avg_latency_ms": round(avg_ep, 1),
                })
            
            # 错误分布
            error_distribution = {}
            for m in recent:
                if m.status != "success":
                    key = f"{m.error_code or m.status}"
                    error_distribution[key] = error_distribution.get(key, 0) + 1
            
            return {
                "period_minutes": minutes,
                "total_requests": total,
                "qps": round(qps, 2),
                "latency": {
                    "avg_ms": round(avg_latency, 1),
                    "p50_ms": round(p50, 1),
                    "p95_ms": round(p95, 1),
                    "p99_ms": round(p99, 1),
                    "max_ms": round(max_latency, 1),
                    "min_ms": round(min_latency, 1),
                },
                "error_rate": round(error_rate, 2),
                "errors": errors,
                "cache_hit_rate": round(cache_rate, 2),
                "active_connections": self._active_connections,
                "peak_connections": self._peak_connections,
                "rate_limit_waits": self._rate_limit_waits,
                "rate_limit_wait_time_ms": round(self._rate_limit_wait_time_ms, 1),
                "uptime_seconds": int(now - self._start_time),
                "by_endpoint": endpoint_stats[:20],
                "error_distribution": dict(sorted(error_distribution.items(), key=lambda x: -x[1])[:10]),
            }
    
    def get_prometheus_metrics(self) -> str:
        """输出 Prometheus 格式的指标
        
        Returns:
            Prometheus text format metrics
        """
        with self._lock:
            lines = []
            now = int(time.time())
            
            # 总请求数
            lines.append("# HELP okx_api_requests_total Total OKX API requests")
            lines.append("# TYPE okx_api_requests_total counter")
            for key, count in sorted(self._counters.items()):
                method, endpoint, status = key.split(":", 2)
                lines.append(
                    f'okx_api_requests_total{{method="{method}",endpoint="{endpoint}",status="{status}"}} {count}'
                )
            
            # 错误总数
            lines.append("")
            lines.append("# HELP okx_api_errors_total Total OKX API errors")
            lines.append("# TYPE okx_api_errors_total counter")
            for key, count in sorted(self._error_counts.items()):
                code, endpoint = key.split(":", 1)
                lines.append(
                    f'okx_api_errors_total{{code="{code}",endpoint="{endpoint}"}} {count}'
                )
            
            # 缓存
            lines.append("")
            lines.append("# HELP okx_api_cache_hits_total Cache hits")
            lines.append("# TYPE okx_api_cache_hits_total counter")
            lines.append(f"okx_api_cache_hits_total {self._cache_hits}")
            lines.append("")
            lines.append("# HELP okx_api_cache_misses_total Cache misses")
            lines.append("# TYPE okx_api_cache_misses_total counter")
            lines.append(f"okx_api_cache_misses_total {self._cache_misses}")
            
            # 限频
            lines.append("")
            lines.append("# HELP okx_api_rate_limit_waits_total Rate limit waits")
            lines.append("# TYPE okx_api_rate_limit_waits_total counter")
            lines.append(f"okx_api_rate_limit_waits_total {self._rate_limit_waits}")
            
            # 活跃连接
            lines.append("")
            lines.append("# HELP okx_api_active_connections Active connections")
            lines.append("# TYPE okx_api_active_connections gauge")
            lines.append(f"okx_api_active_connections {self._active_connections}")
            
            return "\n".join(lines)
    
    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._history.clear()
            self._counters.clear()
            self._error_counts.clear()
            self._latencies.clear()
            self._cache_hits = 0
            self._cache_misses = 0
            self._rate_limit_waits = 0
            self._rate_limit_wait_time_ms = 0
            self._active_connections = 0
            self._peak_connections = 0


# ─── 全局实例 ───

metrics = MetricsCollector()
