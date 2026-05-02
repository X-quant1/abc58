"""
OKX 下级用户 UID 爬虫
用法：
  1. 首次运行：python fetch_subordinates.py --login  # 手动登录保存 cookie
  2. 后续运行：python fetch_subordinates.py          # 用保存的 cookie 爬取
"""
import sys
import os
import json
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "backend"))

PLAYWRIGHT_AVAILABLE = True
try:
    from playwright.async_api import async_playwright
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

COOKIE_FILE = Path(__file__).parent / "backend" / "data" / "okx_cookies.json"
DB_PATH = Path(__file__).parent / "backend" / "data" / "btc_quant.db"


async def login_and_save_cookies():
    """手动登录 OKX 并保存 cookie"""
    if not PLAYWRIGHT_AVAILABLE:
        print("错误：未安装 playwright，请运行：pip install playwright && playwright install chromium")
        return False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 显示浏览器窗口
        context = await browser.new_context()
        page = await context.new_page()

        print("请在浏览器中登录 OKX...")
        print("登录完成后，手动导航到：https://www.okx.com/zh-hans/affiliates/recruit")
        print("确认能看到邀请记录后，回到此窗口按回车继续...")

        await page.goto("https://www.okx.com/zh-hans/affiliates/recruit")

        # 等待用户手动登录
        input("按回车继续保存 cookie...")

        cookies = await context.cookies()
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(COOKIE_FILE, "w") as f:
            json.dump(cookies, f)

        print(f"Cookie 已保存到: {COOKIE_FILE}")
        await browser.close()
        return True


async def fetch_subordinate_uids():
    """用保存的 cookie 爬取下级 UID"""
    if not PLAYWRIGHT_AVAILABLE:
        print("错误：未安装 playwright")
        return []

    if not COOKIE_FILE.exists():
        print("错误：未找到 cookie 文件，请先运行 --login 登录")
        return []

    with open(COOKIE_FILE) as f:
        cookies = json.load(f)

    uids = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            print("正在访问 OKX 邀请页面...")
            await page.goto("https://www.okx.com/zh-hans/affiliates/recruit", timeout=30000)
            await page.wait_for_load_state("networkidle", timeout=10000)

            # 等待邀请记录加载
            await asyncio.sleep(3)

            # 尝试找到所有包含 inviteeUid 的链接
            links = await page.query_selector_all('a[href*="inviteeUid="]')
            print(f"找到 {len(links)} 个下级链接")

            for link in links:
                href = await link.get_attribute("href")
                if href and "inviteeUid=" in href:
                    # 提取 UID
                    import re
                    match = re.search(r"inviteeUid=(\d+)", href)
                    if match:
                        uids.add(match.group(1))

            # 也尝试从消息页面获取
            await page.goto("https://www.okx.com/zh-hans/messages", timeout=30000)
            await asyncio.sleep(2)

            # 点击所有可能的邀请消息
            # 这里需要根据实际页面结构调整选择器

        except Exception as e:
            print(f"爬取失败: {e}")

        await browser.close()

    return list(uids)


def save_to_database(uids):
    """保存 UID 到数据库"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import SubordinateUID

    db = SessionLocal()
    try:
        new_count = 0
        for uid in uids:
            existing = db.query(SubordinateUID).filter(SubordinateUID.uid == uid).first()
            if not existing:
                db.add(SubordinateUID(uid=uid))
                new_count += 1
        db.commit()
        print(f"保存了 {new_count} 个新 UID，共 {len(uids)} 个")
    finally:
        db.close()


def update_users_subordinate_status():
    """更新用户的 is_subordinate 状态"""
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.models import User, SubordinateUID

    db = SessionLocal()
    try:
        # 获取所有下级 UID
        subordinate_uids = set(uid[0] for uid in db.query(SubordinateUID.uid).all())

        # 更新用户状态
        users = db.query(User).filter(User.okx_uid != None).all()
        updated = 0
        for user in users:
            is_sub = user.okx_uid in subordinate_uids
            if user.is_subordinate != is_sub:
                user.is_subordinate = is_sub
                updated += 1

        db.commit()
        print(f"更新了 {updated} 个用户的下级状态")
    finally:
        db.close()


async def main():
    parser = argparse.ArgumentParser(description="OKX 下级用户爬虫")
    parser.add_argument("--login", action="store_true", help="手动登录保存 cookie")
    args = parser.parse_args()

    if args.login:
        await login_and_save_cookies()
    else:
        uids = await fetch_subordinate_uids()
        if uids:
            print(f"获取到 {len(uids)} 个下级 UID:")
            for uid in uids[:10]:
                print(f"  {uid}")
            if len(uids) > 10:
                print(f"  ... 共 {len(uids)} 个")

            save_to_database(uids)
            update_users_subordinate_status()
        else:
            print("未获取到任何 UID，可能需要重新登录 (--login)")


if __name__ == "__main__":
    asyncio.run(main())
