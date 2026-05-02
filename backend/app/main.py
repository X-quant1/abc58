"""BTC 量化交易系统 - FastAPI 主入口"""
import os
import time
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.config import CORS_ORIGINS, BASE_DIR
from app.database import engine, Base, migrate_tables
from app.routers import dashboard, market, strategy, backtest, trade, settings, performance, monitor
from app.routers import ws as ws_router
from app.routers import notification as notification_router
from app.routers import auth as auth_router
from app.routers import admin as admin_router
from app.routers import activities as activities_router
from app.routers import robots as robots_router
from app.routers.ws import start_push_tasks, stop_push_tasks
from app.services.strategy import strategy_runner, STRATEGY_REGISTRY
from app.services.logger import sys_logger
from app.services.metrics import metrics
from app.auth import get_current_user
from app.database import SessionLocal
from app.models import StrategyTemplate


def _sync_strategy_templates():
    """启动时从 STRATEGY_REGISTRY 同步策略模板到数据库"""
    db = SessionLocal()
    try:
        for type_key, cls in STRATEGY_REGISTRY.items():
            existing = db.query(StrategyTemplate).filter(StrategyTemplate.type == type_key).first()
            if not existing:
                tpl = StrategyTemplate(
                    type=type_key,
                    name=cls.strategy_name,
                    desc=cls.strategy_desc,
                    published=True,
                    sort_order=list(STRATEGY_REGISTRY.keys()).index(type_key),
                )
                db.add(tpl)
        db.commit()
        count = db.query(StrategyTemplate).count()
        print(f"[OK] Strategy templates synced: {count} total")
    except Exception as e:
        print(f"[WARN] Strategy template sync failed: {e}")
        db.rollback()
    finally:
        db.close()


def _seed_hot_activities():
    """首次启动时创建默认热门活动数据"""
    from app.models import HotActivity
    db = SessionLocal()
    try:
        count = db.query(HotActivity).count()
        if count == 0:
            defaults = [
                HotActivity(sort_order=1, title="新用户注册送体验金", description="完成注册即送100U体验金，开启量化之旅",
                           status_text="进行中", badge_label="HOT", badge_type="hot",
                           icon_url="/images/jiangbei.webp"),
                HotActivity(sort_order=2, title="邀请好友双赢奖励", description="每邀请一位好友注册并绑定交易所，双方各得50U",
                           status_text="进行中", badge_label="NEW", badge_type="new",
                           icon_url="/images/fuli.webp"),
                HotActivity(sort_order=3, title="策略收益排行榜", description="每周收益排名前10的用户额外奖励策略额度",
                           status_text="即将开始", badge_label="", badge_type="none",
                           icon_url="/images/jiaocheng.webp"),
            ]
            for a in defaults:
                db.add(a)
            db.commit()
            print("[OK] Seeded 3 default hot activities")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时建表 + 恢复策略 + 启动 WS 推送"""
    # 确保 data 目录存在
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(exist_ok=True)

    # 建表
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables ready")

    # 自动迁移（为已有表添加缺失列）
    migrate_tables()

    # 同步策略模板（新增策略类型自动入库，已有模板保留管理员编辑内容）
    _sync_strategy_templates()

    # 种子热门活动默认数据
    _seed_hot_activities()

    # 种子默认量化机器人
    from app.routers.robots import seed_default_robots
    _seed_robots = lambda: seed_default_robots(SessionLocal())
    _seed_robots()

    # 确保 static 目录存在
    (BASE_DIR / "static" / "uploads" / "activities").mkdir(parents=True, exist_ok=True)

    # 启动时加载已保存的 API 配置到运行时
    from app.routers.settings import _load_config, _apply_config
    saved_config = _load_config()
    if saved_config.get("key"):
        _apply_config(saved_config)
        # 重置 OKX 客户端和缓存服务单例，让后续请求使用新配置
        from app.services.okx_client import reset_client
        reset_client()
        from app.services import cache as cache_module
        cache_module._cached_market_service = None
        from app.services import market_rest as market_module
        market_module._market_service = None
        print("[OK] API config loaded from file")

    # WebSocket 推送任务 - 暂时禁用（同步OKX调用阻塞线程池导致全系统卡顿）
    # TODO: 改用纯异步 aiohttp 调用后恢复
    # await start_push_tasks()
    print("[LIFESPAN] Startup complete")

    yield

    # await stop_push_tasks()
    print("[BYE] System shutdown")


app = FastAPI(
    title="BTC 量化交易系统",
    description="比特币量化交易 Web 系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 允许所有来源（WS 连接需要，前端通过 Vite 代理走同域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由 — auth 放最前面（不需要认证）
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(dashboard.router)
app.include_router(market.router)
app.include_router(strategy.router)
app.include_router(backtest.router)
app.include_router(trade.router)
app.include_router(settings.router)
app.include_router(performance.router)
app.include_router(monitor.router)
app.include_router(ws_router.router)
app.include_router(notification_router.router)
app.include_router(activities_router.router)
app.include_router(robots_router.router)

# 挂载静态文件服务（图片等）
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


# ─── API 认证中间件 ───
# 白名单：auth 路由 + health + WebSocket 升级请求 + 可选认证端点
AUTH_WHITELIST = {
    "/api/health",
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/send-code",
    "/api/auth/login-by-code",
    "/api/auth/reset-password",
    "/api/admin/strategies/templates/published",
    "/api/strategy/list",  # 可选认证（匿名用户只看已上架策略）
    "/api/dashboard/overview",  # 总览数据（公开市场数据）
    "/api/dashboard/platform_stats",  # 平台统计数据
    "/api/activities",                  # 热门活动（公开）
    "/api/robots/dashboard/summary",   # 机器人摘要（公开展示）
    "/api/metrics",        # Prometheus指标
    "/api/metrics/summary", # 监控摘要
    "/api/metrics/cache",   # 缓存统计
}


def _is_auth_whitelisted(path: str) -> bool:
    """检查路径是否在认证白名单中（支持前缀匹配）"""
    # 精确匹配
    if path in AUTH_WHITELIST:
        return True
    # 前缀匹配：/api/auth/* 和 /api/backtest/strategy/*/stats
    if path.startswith("/api/auth/"):
        return True
    if path.startswith("/api/backtest/strategy/") and path.endswith("/stats"):
        return True
    return False


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """性能监控中间件：记录每个请求的延迟和状态"""
    start = time.time()
    
    # 活跃连接计数
    metrics.increment_connections()
    
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000
        
        # 记录指标
        path = request.url.path
        method = request.method
        status = "success" if response.status_code < 400 else "error"
        
        metrics.record_request(
            endpoint=path,
            method=method,
            status=status,
            duration_ms=duration_ms,
        )
        
        # 添加性能头
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.1f}"
        return response
    
    except Exception as e:
        duration_ms = (time.time() - start) * 1000
        metrics.record_request(
            endpoint=request.url.path,
            method=request.method,
            status="error",
            duration_ms=duration_ms,
            error_code=type(e).__name__,
        )
        raise
    
    finally:
        metrics.decrement_connections()


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """HTTP 中间件：校验 JWT token，白名单路径跳过"""
    path = request.url.path

    # 白名单跳过
    if _is_auth_whitelisted(path):
        return await call_next(request)

    # WebSocket 跳过（WS 有自己的认证逻辑）
    if request.headers.get("upgrade", "").lower() == "websocket":
        return await call_next(request)

    # 非白名单请求需要带 token
    if path.startswith("/api/"):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "未登录，请先登录"})
        try:
            get_current_user(
                type("C", (), {"credentials": auth_header[7:]})()
            )
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    return await call_next(request)


# 健康检查
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ─── 监控指标端点 ───

@app.get("/api/metrics")
async def prometheus_metrics():
    """Prometheus 格式的监控指标"""
    return PlainTextResponse(
        content=metrics.get_prometheus_metrics(),
        media_type="text/plain",
    )


@app.get("/api/metrics/summary")
async def metrics_summary(minutes: int = 5):
    """监控指标摘要（JSON格式）
    
    Args:
        minutes: 最近N分钟的统计
    """
    return metrics.get_summary(minutes)


@app.get("/api/metrics/cache")
async def cache_stats():
    """缓存统计信息"""
    try:
        from app.services.cache import get_cached_market_service
        cached = get_cached_market_service()
        return cached.get_cache_stats()
    except Exception as e:
        return {"error": str(e), "entries": 0}


@app.post("/api/metrics/cache/clear")
async def cache_clear(current_user: dict = None):
    """清空缓存（需要认证）"""
    try:
        from app.services.cache import get_cached_market_service
        cached = get_cached_market_service()
        cached.clear_cache()
        return {"status": "ok", "message": "Cache cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ─── 全局异常处理 ───

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器 — 捕获所有未处理异常，返回统一格式"""
    # 记录到系统日志
    error_msg = f"{type(exc).__name__}: {str(exc)}"
    error_path = str(request.url)
    sys_logger.error("system", f"Unhandled exception: {error_msg}", {
        "path": error_path,
        "method": request.method,
        "traceback": traceback.format_exc()[:2000],
    })

    # 不暴露堆栈给前端
    return JSONResponse(
        status_code=500,
        content={
            "detail": "服务器内部错误，请稍后重试",
            "error": str(exc)[:200],
            "path": error_path,
        },
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """运行时错误 — 通常是 OKX CLI 调用失败"""
    sys_logger.error("system", f"Runtime error: {exc}", {"path": str(request.url)})

    return JSONResponse(
        status_code=502,
        content={
            "detail": "外部服务调用失败",
            "error": str(exc)[:300],
        },
    )
