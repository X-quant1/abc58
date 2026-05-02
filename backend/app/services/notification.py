"""通知服务 - 邮件/数据库/Webhook 多渠道

通知触发场景：
- 策略开仓/平仓 (category=trade)
- 策略异常/错误 (category=strategy)
- 系统异常 (category=system)
- 自定义告警 (category=alert)
"""
import json
import smtplib
import threading
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

from app.database import SessionLocal
from app.models import Notification
from app.services.logger import sys_logger


# ─── 通知配置（从 settings 路由同步过来）───
class NotifyConfig:
    """运行时通知配置"""
    smtp_host = ""
    smtp_port = 465
    smtp_user = ""
    smtp_password = ""
    smtp_to = ""          # 收件人（多个用逗号分隔）
    smtp_ssl = True
    email_enabled = False
    # 通知开关：哪些场景发邮件
    notify_trade = True       # 开仓/平仓
    notify_error = True       # 策略错误
    notify_system = True      # 系统异常

    def reload_from_file(self):
        """从配置文件重新加载（防御性：内存为空时自动补载）"""
        try:
            config_path = Path(__file__).resolve().parent.parent / "data" / "notify_config.json"
            if not config_path.exists():
                return
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            from app.services.crypto import is_encrypted, decrypt
            pwd = data.get("smtp_password", "")
            if pwd and is_encrypted(pwd):
                data["smtp_password"] = decrypt(pwd)
            self.smtp_host = data.get("smtp_host", "")
            self.smtp_port = int(data.get("smtp_port", 465))
            self.smtp_user = data.get("smtp_user", "")
            self.smtp_password = data.get("smtp_password", "")
            self.smtp_to = data.get("smtp_to", "")
            self.smtp_ssl = data.get("smtp_ssl", True)
            self.email_enabled = data.get("email_enabled", False)
            self.notify_trade = data.get("notify_trade", True)
            self.notify_error = data.get("notify_error", True)
            self.notify_system = data.get("notify_system", True)
        except Exception as e:
            print(f"[NotifyConfig] reload failed: {e}")


notify_config = NotifyConfig()


class NotificationService:
    """通知服务（多渠道）

    渠道：
    - db: 数据库存储（通知历史）
    - email: SMTP 邮件（开仓/平仓/异常告警）
    - webhook: 自定义 Webhook（预留）
    """

    # 通知级别
    LEVEL_INFO = "info"
    LEVEL_WARN = "warn"
    LEVEL_ERROR = "error"

    def __init__(self):
        self._lock = threading.Lock()

    def notify(self, title: str, message: str, level: str = "info",
               category: str = "system", channels: list = None,
               extra: dict = None, strategy_id: int = None):
        """统一通知入口

        Args:
            title: 通知标题
            message: 通知内容
            level: info/warn/error
            category: trade/strategy/system/alert
            channels: 通知渠道列表，如 ["email", "db"]；None=全部已启用渠道
            extra: 附加数据
            strategy_id: 关联策略ID
        """
        # 1. 系统日志
        log_level = {
            self.LEVEL_INFO: "info",
            self.LEVEL_WARN: "warn",
            self.LEVEL_ERROR: "error",
        }.get(level, "info")
        sys_logger.log(log_level, category, message, extra)

        # 2. 数据库存储（始终记录）
        if channels is None or "db" in channels:
            self._save_to_db(title, message, level, category, extra, strategy_id)

        # 3. 邮件通知
        if channels is None or "email" in channels:
            self._maybe_send_email(title, message, level, category, extra)

    # ─── 数据库存储 ───

    def _save_to_db(self, title: str, message: str, level: str,
                    category: str, extra: dict, strategy_id: int):
        """持久化到数据库"""
        detail_str = json.dumps(extra, ensure_ascii=False) if extra else None
        db = SessionLocal()
        try:
            notif = Notification(
                level=level,
                category=category,
                title=title[:200],
                message=message[:2000],
                detail=detail_str,
                channels="email" if notify_config.email_enabled else "db",
                strategy_id=strategy_id,
            )
            db.add(notif)
            db.commit()
            # 通过 WebSocket 推送通知
            self._ws_broadcast(notif)
        except Exception as e:
            print(f"[Notification] db save failed: {e}")
        finally:
            db.close()

    def _ws_broadcast(self, notif: Notification):
        """WebSocket 广播通知到前端"""
        try:
            from app.services.ws_manager import ws_manager
            ws_manager.broadcast("notification", {
                "id": notif.id,
                "level": notif.level,
                "category": notif.category,
                "title": notif.title,
                "message": notif.message,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
            })
        except Exception:
            pass  # WS 不可用不影响

    # ─── 邮件发送 ───

    def _maybe_send_email(self, title: str, message: str, level: str,
                          category: str, extra: dict):
        """检查是否需要发邮件"""
        cfg = notify_config
        if not cfg.email_enabled:
            return
        if not cfg.smtp_host or not cfg.smtp_user or not cfg.smtp_to:
            return
        # 按场景过滤
        if category == "trade" and not cfg.notify_trade:
            return
        if category == "strategy" and not cfg.notify_error:
            return
        if category == "system" and not cfg.notify_system:
            return

        # 异步发送（不阻塞策略线程）
        thread = threading.Thread(
            target=self._send_email,
            args=(title, message, level, category, extra),
            daemon=True,
        )
        thread.start()

    def _send_email(self, title: str, message: str, level: str,
                    category: str, extra: dict):
        """实际发送邮件"""
        cfg = notify_config
        try:
            # 构建邮件
            level_emoji = {"info": "📊", "warn": "⚠️", "error": "🚨"}.get(level, "📋")
            cat_label = {
                "trade": "交易通知",
                "strategy": "策略告警",
                "system": "系统通知",
                "alert": "自定义告警",
            }.get(category, category)

            html_body = f"""
            <div style="font-family: 'Microsoft YaHei', sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f7931a, #e8800a); padding: 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="color: #fff; margin: 0;">{level_emoji} BTC Quant {cat_label}</h2>
                </div>
                <div style="background: #fff; padding: 24px; border: 1px solid #eee; border-top: none; border-radius: 0 0 8px 8px;">
                    <h3 style="color: #1d2129; margin-top: 0;">{title}</h3>
                    <p style="color: #4e5969; line-height: 1.6;">{message}</p>
                    {'<pre style="background: #f7f8fa; padding: 12px; border-radius: 6px; font-size: 12px; overflow-x: auto;">' + json.dumps(extra, ensure_ascii=False, indent=2) + '</pre>' if extra else ''}
                    <hr style="border: none; border-top: 1px solid #f0f2f5; margin: 16px 0;">
                    <p style="color: #c9cdd4; font-size: 12px; margin-bottom: 0;">
                        BTC Quant 量化交易系统 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[BTC Quant] {level_emoji} {title}"
            msg["From"] = cfg.smtp_user
            msg["To"] = cfg.smtp_to
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            # 发送
            if cfg.smtp_ssl:
                server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10)

            server.login(cfg.smtp_user, cfg.smtp_password)
            server.sendmail(cfg.smtp_user, cfg.smtp_to.split(","), msg.as_string())
            server.quit()

            sys_logger.info("notification", f"Email sent: {title}")
        except Exception as e:
            sys_logger.error("notification", f"Email send failed: {e}")

    # ─── 查询通知历史 ───

    def get_notifications(self, limit: int = 50, offset: int = 0,
                          category: str = None, unread_only: bool = False):
        """查询通知历史"""
        db = SessionLocal()
        try:
            q = db.query(Notification)
            if category:
                q = q.filter(Notification.category == category)
            if unread_only:
                q = q.filter(Notification.read == False)
            total = q.count()
            items = q.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()
            return {
                "total": total,
                "unread": db.query(Notification).filter(Notification.read == False).count(),
                "items": [
                    {
                        "id": n.id,
                        "level": n.level,
                        "category": n.category,
                        "title": n.title,
                        "message": n.message,
                        "detail": n.detail,
                        "channels": n.channels,
                        "read": n.read,
                        "strategy_id": n.strategy_id,
                        "created_at": n.created_at.isoformat() if n.created_at else None,
                    }
                    for n in items
                ],
            }
        finally:
            db.close()

    def mark_read(self, notification_id: int = None, mark_all: bool = False):
        """标记已读"""
        db = SessionLocal()
        try:
            if mark_all:
                db.query(Notification).filter(Notification.read == False).update({"read": True})
            elif notification_id:
                n = db.query(Notification).filter(Notification.id == notification_id).first()
                if n:
                    n.read = True
            db.commit()
            return {"success": True}
        finally:
            db.close()

    def get_unread_count(self):
        """获取未读数"""
        db = SessionLocal()
        try:
            return db.query(Notification).filter(Notification.read == False).count()
        finally:
            db.close()

    def test_email(self) -> dict:
        """测试邮件发送"""
        cfg = notify_config
        if not cfg.smtp_host or not cfg.smtp_user or not cfg.smtp_to:
            return {"success": False, "message": "请先配置 SMTP"}
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "[BTC Quant] 🧪 测试邮件"
            msg["From"] = cfg.smtp_user
            msg["To"] = cfg.smtp_to
            html = """
            <div style="font-family: sans-serif; padding: 20px;">
                <h2>✅ 邮件配置测试成功</h2>
                <p>BTC Quant 量化交易系统邮件通知已正常工作。</p>
                <p style="color: #999;">如果你收到这封邮件，说明 SMTP 配置正确。</p>
            </div>
            """
            msg.attach(MIMEText(html, "html", "utf-8"))

            if cfg.smtp_ssl:
                server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10)
            server.login(cfg.smtp_user, cfg.smtp_password)
            server.sendmail(cfg.smtp_user, cfg.smtp_to.split(","), msg.as_string())
            server.quit()
            return {"success": True, "message": "测试邮件已发送"}
        except Exception as e:
            return {"success": False, "message": f"发送失败: {e}"}


def send_verification_email(email: str, code: str, purpose: str) -> dict:
    """发送验证码邮件（注册/登录/重置密码）

    Args:
        email: 收件人邮箱
        code: 6位验证码
        purpose: login/register/reset

    Returns:
        {"success": True/False, "message": "..."}
    """
    cfg = notify_config
    # 防御性加载：内存配置为空时从文件重新读取
    if not cfg.smtp_host or not cfg.smtp_user:
        cfg.reload_from_file()
    if not cfg.smtp_host or not cfg.smtp_user:
        return {"success": False, "message": "邮件服务未配置，请在管理后台设置SMTP"}

    purpose_label = {"login": "登录验证", "register": "注册验证", "reset": "重置密码"}.get(purpose, "验证码")
    purpose_icon = {"login": "🔐", "register": "✉️", "reset": "🔑"}.get(purpose, "📋")

    html_body = f"""
    <div style="font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; max-width: 520px; margin: 0 auto; background: #f9fafb; border-radius: 12px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #f7931a, #e8800a); padding: 28px 24px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 22px;">BTC Quant</h1>
            <p style="color: rgba(255,255,255,0.85); margin: 6px 0 0; font-size: 13px;">{purpose_icon} {purpose_label}</p>
        </div>
        <div style="padding: 32px 24px; background: #fff;">
            <p style="color: #4e5969; font-size: 14px; line-height: 1.7; margin: 0 0 20px;">
                您正在进行 <strong style="color: #1d2129;">{purpose_label}</strong> 操作，请在 5 分钟内输入以下验证码：
            </p>
            <div style="background: #f7f8fa; border-radius: 10px; padding: 18px; text-align: center; margin: 0 0 24px; border: 1px dashed #e5e6eb;">
                <span style="font-size: 36px; font-weight: 700; letter-spacing: 10px; color: #f7931a; font-family: 'Courier New', monospace;">{code}</span>
            </div>
            <p style="color: #c9cdd4; font-size: 12px; margin: 0;">
                如果这不是您本人的操作，请忽略此邮件。验证码 5 分钟后失效。
            </p>
        </div>
        <div style="padding: 16px 24px; text-align: center; border-top: 1px solid #f0f2f5;">
            <p style="color: #c9cdd4; font-size: 11px; margin: 0;">
                BTC Quant 量化交易系统 &copy; 2026
            </p>
        </div>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[BTC Quant] {purpose_icon} 您的验证码: {code}"
        msg["From"] = cfg.smtp_user
        msg["To"] = email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if cfg.smtp_ssl:
            server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10)
            server.starttls()

        server.login(cfg.smtp_user, cfg.smtp_password)
        server.sendmail(cfg.smtp_user, [email], msg.as_string())
        server.quit()

        sys_logger.info("notification", f"Verification email sent: {email} purpose={purpose}")
        return {"success": True, "message": "验证码已发送"}
    except Exception as e:
        sys_logger.error("notification", f"Verification email failed: {e}")
        return {"success": False, "message": f"邮件发送失败: {e}"}


# 单例
notification_service = NotificationService()
