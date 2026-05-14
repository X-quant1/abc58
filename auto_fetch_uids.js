const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const COOKIE_FILE = path.join(__dirname, 'backend', 'data', 'okx_cookies.json');

async function getCookies() {
  console.log('启动浏览器...');
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  });

  const page = await browser.newPage();

  // 检查是否已有 cookie
  if (fs.existsSync(COOKIE_FILE)) {
    const cookies = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
    await page.setCookie(...cookies);
    console.log('已加载保存的 cookie');
  }

  // 访问邀请页面
  console.log('访问 OKX 邀请页面...');
  await page.goto('https://www.okx.com/zh-hans/affiliates/recruit', {
    waitUntil: 'networkidle2',
    timeout: 60000
  });

  // 等待页面加载
  await new Promise(r => setTimeout(r, 5000));

  // 检查是否需要登录
  const currentUrl = page.url();
  if (currentUrl.includes('login') || currentUrl.includes('signin')) {
    console.log('\n请在新打开的浏览器窗口中登录 OKX...');
    console.log('登录完成后，脚本会自动继续...\n');

    // 等待 URL 变化（登录成功后会跳转）
    await page.waitForFunction(() => {
      return !window.location.href.includes('login') && !window.location.href.includes('signin');
    }, { timeout: 300000 }); // 5分钟超时

    console.log('检测到登录成功！');
  }

  // 保存 cookie
  const cookies = await page.cookies();
  fs.mkdirSync(path.dirname(COOKIE_FILE), { recursive: true });
  fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
  console.log(`Cookie 已保存到: ${COOKIE_FILE}`);

  // 查找所有包含 inviteeUid 的链接
  console.log('正在查找下级 UID...');
  const links = await page.$$eval('a[href*="inviteeUid="]', els => els.map(a => a.href));
  const uids = [...new Set(links.map(url => {
    const match = url.match(/inviteeUid=(\d+)/);
    return match ? match[1] : null;
  }).filter(Boolean))];

  console.log(`找到 ${uids.length} 个下级 UID:`);
  uids.forEach(uid => console.log(`  ${uid}`));

  await browser.close();

  // 保存到数据库
  if (uids.length > 0) {
    const { execSync } = require('child_process');
    const py = 'C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\envs\\btc-quant\\Scripts\\python.exe';
    const script = 'c:\\LH\\OKX\\save_uids.py';
    const uidStr = uids.join(',');
    console.log('正在保存到数据库...');
    execSync(`"${py}" "${script}" "${uidStr}"`, { stdio: 'inherit' });
  }
}

getCookies().catch(console.error);
