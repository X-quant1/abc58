from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    # 打开登录页面
    page.goto('https://new.zxlh.pro/pages/login.html')
    time.sleep(2)
    
    # 输入账号密码
    page.fill('input[type="text"]', '52bill')
    page.fill('input[type="password"]', '422926238')
    time.sleep(1)
    
    # 点击登录
    page.click('button:has-text("登录")')
    time.sleep(3)
    
    # 截图
    page.screenshot(path='login_result.png')
    print('登录完成，已截图')
    
    # 点击策略页面
    try:
        page.click('text=策略')
        time.sleep(2)
        page.screenshot(path='strategy_page.png')
        print('策略页面截图完成')
    except Exception as e:
        print(f'点击策略失败: {e}')
    
    browser.close()
