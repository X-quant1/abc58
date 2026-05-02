const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const COOKIE_FILE = path.join(__dirname, 'backend', 'data', 'okx_cookies.json');

async function login() {
  console.log('启动浏览器...');
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  });

  const page = await browser.newPage();
  await page.goto('https://www.okx.com/zh-hans/affiliates/recruit', { waitUntil: 'networkidle2' });

  console.log('\n请在浏览器中登录 OKX...');
  console.log('登录完成后，按回车继续...\n');

  await new Promise(resolve => {
    process.stdin.once('data', resolve);
  });

  const cookies = await page.cookies();
  fs.mkdirSync(path.dirname(COOKIE_FILE), { recursive: true });
  fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
  console.log(`Cookie 已保存到: ${COOKIE_FILE}`);

  await browser.close();
}

async function fetchUIDs() {
  if (!fs.existsSync(COOKIE_FILE)) {
    console.log('错误：未找到 cookie 文件，请先运行 --login');
    return [];
  }

  console.log('启动浏览器（无头模式）...');
  const browser = await puppeteer.launch({
    headless: true,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  });
  const page = await browser.newPage();

  const cookies = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
  await page.setCookie(...cookies);

  console.log('访问 OKX 邀请页面...');
  await page.goto('https://www.okx.com/zh-hans/affiliates/recruit', { waitUntil: 'networkidle2', timeout: 30000 });
  await new Promise(r => setTimeout(r, 3000));

  // 查找所有包含 inviteeUid 的链接
  const links = await page.$$eval('a[href*="inviteeUid="]', els => els.map(a => a.href));
  const uids = [...new Set(links.map(url => {
    const match = url.match(/inviteeUid=(\d+)/);
    return match ? match[1] : null;
  }).filter(Boolean))];

  console.log(`找到 ${uids.length} 个下级 UID`);
  uids.forEach(uid => console.log(`  ${uid}`));

  await browser.close();
  return uids;
}

async function saveToDatabase(uids) {
  const { execSync } = require('child_process');
  const py = 'C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\envs\\btc-quant\\Scripts\\python.exe';
  const script = 'c:\\LH\\OKX\\save_uids.py';
  const uidStr = uids.join(',');
  execSync(`"${py}" "${script}" "${uidStr}"`, { stdio: 'inherit' });
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--login')) {
    await login();
  } else {
    const uids = await fetchUIDs();
    if (uids.length > 0) {
      await saveToDatabase(uids);
    }
  }
}

main().catch(console.error);
