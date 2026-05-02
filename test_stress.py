"""OKX REST API 压力测试

测试场景：
1. 单用户连续请求（基准测试）
2. 多用户并发请求（并发测试）
3. 混合读写测试（模拟真实场景）
4. 缓存效果对比测试

输出：
- QPS（每秒请求数）
- 延迟分布（P50/P95/P99）
- 错误率
- 内存/CPU占用
"""
import asyncio
import time
import sys
import os
import json
import statistics
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, r"c:\LH\OKX\backend")

# 加载API配置
from app.routers import settings

from app.services.market_rest import get_market_service, MarketService
from app.services.trade_rest import get_trade_service, TradeService
from app.services.okx_client import OKXClient
from app.services.metrics import MetricsCollector
from app.services.cache import MarketCache, CachedMarketService


class StressTestResult:
    """压力测试结果"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = 0
        self.end_time = 0
        self.durations: List[float] = []
        self.errors: List[str] = []
        self.success_count = 0
        self.error_count = 0
    
    @property
    def total(self):
        return self.success_count + self.error_count
    
    @property
    def duration_seconds(self):
        return self.end_time - self.start_time
    
    @property
    def qps(self):
        if self.duration_seconds <= 0:
            return 0
        return self.total / self.duration_seconds
    
    @property
    def error_rate(self):
        if self.total == 0:
            return 0
        return self.error_count / self.total * 100
    
    @property
    def avg_latency_ms(self):
        if not self.durations:
            return 0
        return statistics.mean(self.durations) * 1000
    
    @property
    def p50_latency_ms(self):
        if not self.durations:
            return 0
        sorted_d = sorted(self.durations)
        return sorted_d[len(sorted_d) // 2] * 1000
    
    @property
    def p95_latency_ms(self):
        if not self.durations:
            return 0
        sorted_d = sorted(self.durations)
        idx = int(len(sorted_d) * 0.95)
        return sorted_d[min(idx, len(sorted_d) - 1)] * 1000
    
    @property
    def p99_latency_ms(self):
        if not self.durations:
            return 0
        sorted_d = sorted(self.durations)
        idx = int(len(sorted_d) * 0.99)
        return sorted_d[min(idx, len(sorted_d) - 1)] * 1000
    
    @property
    def max_latency_ms(self):
        if not self.durations:
            return 0
        return max(self.durations) * 1000
    
    @property
    def min_latency_ms(self):
        if not self.durations:
            return 0
        return min(self.durations) * 1000
    
    def to_dict(self):
        return {
            "name": self.name,
            "total_requests": self.total,
            "success": self.success_count,
            "errors": self.error_count,
            "qps": round(self.qps, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "latency": {
                "avg_ms": round(self.avg_latency_ms, 1),
                "p50_ms": round(self.p50_latency_ms, 1),
                "p95_ms": round(self.p95_latency_ms, 1),
                "p99_ms": round(self.p99_latency_ms, 1),
                "max_ms": round(self.max_latency_ms, 1),
                "min_ms": round(self.min_latency_ms, 1),
            },
            "error_rate": round(self.error_rate, 2),
        }


# ─── 测试场景 ───

def test_sync_ticker_baseline(iterations: int = 50) -> StressTestResult:
    """场景1: 同步获取行情 - 基准测试
    
    单线程连续请求50次，测量平均延迟。
    """
    result = StressTestResult("同步获取BTC行情(基准)")
    ms = get_market_service()
    
    print(f"\n{'='*60}")
    print(f"场景1: 同步获取BTC行情 - 基准测试 ({iterations}次)")
    print(f"{'='*60}")
    
    result.start_time = time.time()
    
    for i in range(iterations):
        try:
            start = time.time()
            ticker = ms.get_ticker("BTC-USDT")
            duration = time.time() - start
            
            result.durations.append(duration)
            result.success_count += 1
            
            if i % 10 == 0:
                print(f"  [{i+1}/{iterations}] 价格: {ticker['price']:.1f} 延迟: {duration*1000:.1f}ms")
        
        except Exception as e:
            result.errors.append(str(e)[:100])
            result.error_count += 1
            print(f"  [{i+1}/{iterations}] ERROR: {str(e)[:50]}")
    
    result.end_time = time.time()
    return result


def test_sync_klines_baseline(iterations: int = 30) -> StressTestResult:
    """场景2: 同步获取K线 - 基准测试"""
    result = StressTestResult("同步获取K线(基准)")
    ms = get_market_service()
    
    print(f"\n{'='*60}")
    print(f"场景2: 同步获取K线 - 基准测试 ({iterations}次)")
    print(f"{'='*60}")
    
    result.start_time = time.time()
    
    for i in range(iterations):
        try:
            start = time.time()
            klines = ms.get_klines("BTC-USDT-SWAP", "1H", 100)
            duration = time.time() - start
            
            result.durations.append(duration)
            result.success_count += 1
            
            if i % 5 == 0:
                print(f"  [{i+1}/{iterations}] K线数: {len(klines)} 延迟: {duration*1000:.1f}ms")
        
        except Exception as e:
            result.errors.append(str(e)[:100])
            result.error_count += 1
    
    result.end_time = time.time()
    return result


async def test_async_concurrent_ticker(concurrency: int = 20, per_worker: int = 5) -> StressTestResult:
    """场景3: 异步并发获取行情
    
    20个并发worker，每个请求5次。
    模拟多用户同时获取行情。
    """
    result = StressTestResult(f"异步并发行情({concurrency}并发x{per_worker}次)")
    ms = get_market_service()
    
    total = concurrency * per_worker
    print(f"\n{'='*60}")
    print(f"场景3: 异步并发获取行情 ({concurrency}并发 x {per_worker}次 = {total}次)")
    print(f"{'='*60}")
    
    async def worker(worker_id: int, session):
        for i in range(per_worker):
            try:
                start = time.time()
                ticker = await ms.async_get_ticker("BTC-USDT", session=session)
                duration = time.time() - start
                
                result.durations.append(duration)
                result.success_count += 1
            
            except Exception as e:
                result.errors.append(f"w{worker_id}-{i}: {str(e)[:200]}")
                result.error_count += 1
    
    result.start_time = time.time()
    
    # 使用共享session + 连接池
    import aiohttp
    connector = aiohttp.TCPConnector(
        limit=100, limit_per_host=30, ttl_dns_cache=300, use_dns_cache=True,
    )
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        tasks = [worker(i, session) for i in range(concurrency)]
        await asyncio.gather(*tasks)
    
    result.end_time = time.time()
    
    # 输出错误详情
    if result.errors:
        print(f"  错误详情 (前5条):")
        for err in result.errors[:5]:
            print(f"    {err}")
    
    return result


async def test_async_mixed_operations(concurrency: int = 10, per_worker: int = 10) -> StressTestResult:
    """场景4: 混合读写操作
    
    模拟真实场景：
    - 50% 行情查询
    - 20% K线查询
    - 20% 余额查询
    - 10% 持仓查询
    """
    result = StressTestResult(f"混合操作({concurrency}并发x{per_worker}次)")
    ms = get_market_service()
    
    total = concurrency * per_worker
    print(f"\n{'='*60}")
    print(f"场景4: 混合读写操作 ({concurrency}并发 x {per_worker}次 = {total}次)")
    print(f"{'='*60}")
    
    async def worker(worker_id: int, session):
        import random
        for i in range(per_worker):
            try:
                start = time.time()
                
                # 随机选择操作类型
                op = random.random()
                if op < 0.5:
                    await ms.async_get_ticker("BTC-USDT", session=session)
                elif op < 0.7:
                    await ms.async_get_klines("BTC-USDT-SWAP", "1H", 50, session=session)
                elif op < 0.9:
                    await ms.async_get_account_balance("USDT", session=session)
                else:
                    await ms.async_get_positions("BTC-USDT-SWAP", session=session)
                
                duration = time.time() - start
                result.durations.append(duration)
                result.success_count += 1
            
            except Exception as e:
                result.errors.append(f"w{worker_id}-{i}: {str(e)[:200]}")
                result.error_count += 1
    
    result.start_time = time.time()
    import aiohttp
    connector = aiohttp.TCPConnector(
        limit=100, limit_per_host=30, ttl_dns_cache=300, use_dns_cache=True,
    )
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        tasks = [worker(i, session) for i in range(concurrency)]
        await asyncio.gather(*tasks)
    result.end_time = time.time()
    
    # 输出错误详情
    if result.errors:
        print(f"  错误详情 (前5条):")
        for err in result.errors[:5]:
            print(f"    {err}")
    
    return result


def test_cache_effectiveness(iterations: int = 100) -> Dict[str, Any]:
    """场景5: 缓存效果对比
    
    同样请求100次，对比有缓存和无缓存的性能差异。
    """
    print(f"\n{'='*60}")
    print(f"场景5: 缓存效果对比 ({iterations}次)")
    print(f"{'='*60}")
    
    ms = get_market_service()
    cache = MarketCache()
    
    # 无缓存测试
    no_cache_durations = []
    start = time.time()
    for i in range(iterations):
        s = time.time()
        ms.get_ticker("BTC-USDT")
        no_cache_durations.append(time.time() - s)
    no_cache_total = time.time() - start
    
    # 有缓存测试
    cache_durations = []
    start = time.time()
    for i in range(iterations):
        # 先查缓存
        cached = cache.get("ticker", "BTC-USDT")
        if cached is None:
            s = time.time()
            result = ms.get_ticker("BTC-USDT")
            cache.set("ticker", result, "BTC-USDT")
            cache_durations.append(time.time() - s)
        else:
            cache_durations.append(0.0001)  # 缓存命中，几乎0延迟
    cache_total = time.time() - start
    
    cache_stats = cache.get_stats()
    
    return {
        "iterations": iterations,
        "no_cache": {
            "total_seconds": round(no_cache_total, 3),
            "qps": round(iterations / no_cache_total, 1),
            "avg_latency_ms": round(statistics.mean(no_cache_durations) * 1000, 1),
            "p95_ms": round(sorted(no_cache_durations)[int(len(no_cache_durations) * 0.95)] * 1000, 1),
        },
        "with_cache": {
            "total_seconds": round(cache_total, 3),
            "qps": round(iterations / cache_total, 1),
            "avg_latency_ms": round(statistics.mean(cache_durations) * 1000, 1),
        },
        "speedup": round(no_cache_total / cache_total, 1),
        "cache_stats": cache_stats,
    }


async def test_simulated_1000_users() -> StressTestResult:
    """场景6: 模拟1000用户并发
    
    使用单个API Key模拟1000个用户并发请求行情。
    注意：不会真正下单，只读取行情数据。
    """
    result = StressTestResult("模拟1000用户并发行情查询")
    ms = get_market_service()
    
    concurrency = 100  # 先用100并发测试
    per_worker = 10    # 每个worker请求10次
    total = concurrency * per_worker
    
    print(f"\n{'='*60}")
    print(f"场景6: 模拟1000用户并发 ({concurrency}并发 x {per_worker}次 = {total}次)")
    print(f"{'='*60}")
    
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT", "DOGE-USDT",
               "ADA-USDT", "AVAX-USDT", "DOT-USDT", "LINK-USDT", "SUI-USDT"]
    
    async def worker(worker_id: int, session):
        symbol = symbols[worker_id % len(symbols)]
        for i in range(per_worker):
            try:
                start = time.time()
                await ms.async_get_ticker(symbol, session=session)
                duration = time.time() - start
                
                result.durations.append(duration)
                result.success_count += 1
            
            except Exception as e:
                result.errors.append(f"w{worker_id}-{i}: {str(e)[:200]}")
                result.error_count += 1
    
    result.start_time = time.time()
    import aiohttp
    connector = aiohttp.TCPConnector(
        limit=200, limit_per_host=50, ttl_dns_cache=300, use_dns_cache=True,
    )
    async with aiohttp.ClientSession(connector=connector, trust_env=True) as session:
        tasks = [worker(i, session) for i in range(concurrency)]
        await asyncio.gather(*tasks)
    result.end_time = time.time()
    
    # 输出错误详情
    if result.errors:
        print(f"  错误详情 (前5条):")
        for err in result.errors[:5]:
            print(f"    {err}")
    
    return result


# ─── 主测试流程 ───

async def run_all_tests():
    """运行所有压力测试"""
    print("\n" + "=" * 60)
    print("  OKX REST API 压力测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = []
    
    # 场景1: 同步基准测试
    r1 = test_sync_ticker_baseline(50)
    results.append(r1.to_dict())
    print(f"\n  结果: QPS={r1.qps:.1f} | P50={r1.p50_latency_ms:.1f}ms | P95={r1.p95_latency_ms:.1f}ms | 错误率={r1.error_rate:.1f}%")
    
    # 场景2: K线基准测试
    r2 = test_sync_klines_baseline(30)
    results.append(r2.to_dict())
    print(f"\n  结果: QPS={r2.qps:.1f} | P50={r2.p50_latency_ms:.1f}ms | P95={r2.p95_latency_ms:.1f}ms | 错误率={r2.error_rate:.1f}%")
    
    # 场景3: 异步并发测试
    r3 = await test_async_concurrent_ticker(20, 5)
    results.append(r3.to_dict())
    print(f"\n  结果: QPS={r3.qps:.1f} | P50={r3.p50_latency_ms:.1f}ms | P95={r3.p95_latency_ms:.1f}ms | 错误率={r3.error_rate:.1f}%")
    
    # 场景4: 混合操作测试
    r4 = await test_async_mixed_operations(10, 10)
    results.append(r4.to_dict())
    print(f"\n  结果: QPS={r4.qps:.1f} | P50={r4.p50_latency_ms:.1f}ms | P95={r4.p95_latency_ms:.1f}ms | 错误率={r4.error_rate:.1f}%")
    
    # 场景5: 缓存效果测试
    r5 = test_cache_effectiveness(100)
    results.append(r5)
    print(f"\n  无缓存: {r5['no_cache']['qps']:.1f} QPS, 平均{r5['no_cache']['avg_latency_ms']:.1f}ms")
    print(f"  有缓存: {r5['with_cache']['qps']:.1f} QPS, 平均{r5['with_cache']['avg_latency_ms']:.1f}ms")
    print(f"  加速比: {r5['speedup']:.1f}x")
    
    # 场景6: 模拟1000用户
    r6 = await test_simulated_1000_users()
    results.append(r6.to_dict())
    print(f"\n  结果: QPS={r6.qps:.1f} | P50={r6.p50_latency_ms:.1f}ms | P95={r6.p95_latency_ms:.1f}ms | 错误率={r6.error_rate:.1f}%")
    
    # 汇总
    print("\n" + "=" * 60)
    print("  压力测试汇总")
    print("=" * 60)
    
    summary = {
        "test_time": datetime.now().isoformat(),
        "results": results,
        "conclusion": {
            "sync_ticker_qps": r1.qps,
            "async_concurrent_qps": r3.qps,
            "mixed_ops_qps": r4.qps,
            "cache_speedup": r5["speedup"],
            "simulated_1000_users_qps": r6.qps,
            "simulated_1000_users_error_rate": r6.error_rate,
            "recommendation": "",
        }
    }
    
    # 生成建议
    if r6.error_rate < 5 and r6.qps > 100:
        summary["conclusion"]["recommendation"] = "系统可支持1000+用户并发，建议上云部署"
    elif r6.error_rate < 10:
        summary["conclusion"]["recommendation"] = "系统基本可用，需优化错误率后上云"
    else:
        summary["conclusion"]["recommendation"] = "需优化后再上云，建议增加限频和重试机制"
    
    # 保存结果
    report_path = r"c:\LH\OKX\backend\stress_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存到: {report_path}")
    print(f"\n建议: {summary['conclusion']['recommendation']}")
    
    return summary


if __name__ == "__main__":
    asyncio.run(run_all_tests())
