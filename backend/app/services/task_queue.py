"""任务队列 - 异步执行策略信号

当前实现：Python 内置队列 + 后台线程
后期扩展：替换为 Redis + Celery（只需改此文件）
"""
import queue
import threading
from typing import Callable, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Task:
    """任务对象"""
    
    def __init__(self, task_type: str, payload: dict, callback: Optional[Callable] = None):
        self.task_type = task_type  # open_long, open_short, close_position, etc.
        self.payload = payload      # 任务数据
        self.callback = callback    # 回调函数
        self.created_at = datetime.utcnow()
        self.retry_count = 0
        self.max_retries = 3


class TaskQueue:
    """任务队列（单例模式）
    
    当前使用 Python 内置队列，后期可无缝替换为 Redis 队列
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._queue = queue.Queue()
        self._workers = []
        self._running = False
        self._handlers = {}  # 任务类型 -> 处理函数
        
        # 统计
        self._stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
        }
    
    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理函数"""
        self._handlers[task_type] = handler
        logger.info(f"[TaskQueue] Registered handler for: {task_type}")
    
    def enqueue(self, task: Task) -> bool:
        """入队"""
        try:
            self._queue.put(task)
            self._stats["total_tasks"] += 1
            logger.debug(f"[TaskQueue] Enqueued task: {task.task_type}")
            return True
        except Exception as e:
            logger.error(f"[TaskQueue] Failed to enqueue: {e}")
            return False
    
    def _process_task(self, task: Task):
        """处理单个任务"""
        handler = self._handlers.get(task.task_type)
        if not handler:
            logger.error(f"[TaskQueue] No handler for task type: {task.task_type}")
            self._stats["failed_tasks"] += 1
            return
        
        try:
            result = handler(task.payload)
            self._stats["completed_tasks"] += 1
            logger.info(f"[TaskQueue] Task completed: {task.task_type}")
            
            # 执行回调
            if task.callback:
                try:
                    task.callback(result)
                except Exception as e:
                    logger.error(f"[TaskQueue] Callback error: {e}")
                    
        except Exception as e:
            logger.error(f"[TaskQueue] Task failed: {task.task_type}, error: {e}")
            self._stats["failed_tasks"] += 1
            
            # 重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(f"[TaskQueue] Retrying task ({task.retry_count}/{task.max_retries})")
                self._queue.put(task)
    
    def _worker_loop(self):
        """工作线程循环"""
        while self._running:
            try:
                task = self._queue.get(timeout=1.0)
                self._process_task(task)
                self._queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[TaskQueue] Worker error: {e}")
    
    def start(self, worker_count: int = 4):
        """启动工作线程"""
        if self._running:
            return
        
        self._running = True
        for i in range(worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"TaskWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"[TaskQueue] Started {worker_count} workers")
    
    def stop(self):
        """停止工作线程"""
        self._running = False
        self._workers.clear()
        logger.info("[TaskQueue] Stopped")
    
    def get_stats(self) -> dict:
        """获取队列统计"""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "workers": len(self._workers),
            "running": self._running,
        }
    
    def is_empty(self) -> bool:
        """队列是否为空"""
        return self._queue.empty()


# 全局单例
task_queue = TaskQueue()


# ─────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────

def enqueue_trade(task_type: str, payload: dict, callback: Callable = None) -> bool:
    """快捷入队交易任务"""
    task = Task(task_type, payload, callback)
    return task_queue.enqueue(task)


def get_queue_stats() -> dict:
    """获取队列统计"""
    return task_queue.get_stats()
