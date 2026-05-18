"""系统日志服务

提供统一的日志记录接口，将关键事件持久化到 system_logs 表。
策略引擎、交易服务、行情服务均可调用。
"""
import json
import threading
from datetime import datetime

from app.database import SessionLocal
from app.models import SystemLog


class SystemLogger:
    """系统日志记录器（线程安全）"""

    def __init__(self):
        self._lock = threading.Lock()

    def _write(self, level: str, module: str, message: str, detail: dict = None, strategy_id: int = None):
        """写入日志"""
        detail_str = json.dumps(detail, ensure_ascii=False) if detail else None
        db = SessionLocal()
        try:
            log = SystemLog(
                level=level,
                module=module,
                message=message[:500],
                detail=detail_str,
                strategy_id=strategy_id,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            # 日志写入失败不应影响业务
            print(f"[Logger] write failed: {e}")
        finally:
            db.close()

    def info(self, module: str, message: str, detail: dict = None, strategy_id: int = None):
        self._write("info", module, message, detail, strategy_id)

    def warn(self, module: str, message: str, detail: dict = None, strategy_id: int = None):
        self._write("warn", module, message, detail, strategy_id)

    def error(self, module: str, message: str, detail: dict = None, strategy_id: int = None):
        self._write("error", module, message, detail, strategy_id)


# 全局单例
sys_logger = SystemLogger()
