"""加密服务 - API Key 加密存储

使用 Fernet 对称加密，密钥从机器特征派生。
文件中只存密文，启动时解密到内存。
"""
import base64
import hashlib
import os
from pathlib import Path

from cryptography.fernet import Fernet


# 密钥种子文件路径（首次启动自动生成）
_KEY_FILE = Path(__file__).resolve().parent.parent / "data" / ".enc_key"


def _get_or_create_key() -> bytes:
    """获取或创建加密密钥

    密钥策略：优先从文件读取；否则生成新密钥并保存。
    Fernet.generate_key() 返回 url-safe base64 编码的 32 字节密钥，
    长度固定为 44 字节。直接存储和使用，不要截取。
    """
    # 1. 尝试从文件读取
    if _KEY_FILE.exists():
        try:
            key = _KEY_FILE.read_bytes().strip()
            # Fernet key 是 base64 编码的 32 字节，长度为 44
            if len(key) == 44:
                return key
        except Exception:
            pass

    # 2. 生成新密钥并保存
    key = Fernet.generate_key()  # 44 字节 base64 编码
    try:
        _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _KEY_FILE.write_bytes(key)
        # Windows: 设置文件为隐藏 + 仅当前用户可读
        if os.name == "nt":
            try:
                import ctypes
                ctypes.windll.kernel32.SetFileAttributesW(str(_KEY_FILE), 0x02)
            except Exception:
                pass
    except Exception:
        pass

    return key


# 全局 Fernet 实例（模块加载时初始化一次）
_fernet = Fernet(_get_or_create_key())


def encrypt(plaintext: str) -> str:
    """加密明文，返回 base64 编码的密文"""
    if not plaintext:
        return ""
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str) -> str:
    """解密密文，返回明文"""
    if not ciphertext:
        return ""
    try:
        return _fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except Exception:
        # 解密失败（密钥更换等），返回空
        return ""


def is_encrypted(value: str) -> bool:
    """判断值是否是加密后的密文（Fernet 密文以 gAAAA 开头）"""
    return value.startswith("gAAAA") if value else False
