const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const COOKIE_FILE = path.join(__dirname, 'backend', 'data', 'okx_cookies.json');

async function getSubordinateUIDs() {
  console.log('启动浏览器...');
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  });

  const page = await browser.newPage();

  // 加载已保存的 cookie
  if (fs.existsSync(COOKIE_FILE)) {
    const cookies = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf8'));
    await page.setCookie(...cookies);
    console.log('已加载保存的 cookie');
  }

  // 访问邀请页面（添加重试逻辑）
  console.log('访问 OKX 邀请页面...');
  let retryCount = 0;
  const maxRetries = 3;
  while (retryCount < maxRetries) {
    try {
      await page.goto('https://www.okx.com/zh-hans/affiliates/recruit', {
        waitUntil: 'domcontentloaded',
        timeout: 60000
      });
      break; // 成功则跳出循环
    } catch (e) {
      retryCount++;
      console.log(`导航失败 (尝试 ${retryCount}/${maxRetries}): ${e.message}`);
      if (retryCount >= maxRetries) throw e;
      await new Promise(r => setTimeout(r, 3000)); // 等待 3 秒后重试
    }
  }

  await new Promise(r => setTimeout(r, 5000));

  // 收集所有 UID
  const allUIDs = new Set();

  // 监听新页面/标签页
  browser.on('targetcreated', async (target) => {
    const newPage = await target.page();
    if (newPage) {
      const url = newPage.url();
      const match = url.match(/inviteeUid=(\d+)/);
      if (match) {
        console.log(`发现 UID: ${match[1]}`);
        allUIDs.add(match[1]);
      }
    }
  });

  // 监听页面跳转
  page.on('framenavigated', (frame) => {
    const url = frame.url();
    const match = url.match(/inviteeUid=(\d+)/);
    if (match) {
      console.log(`发现 UID: ${match[1]}`);
      allUIDs.add(match[1]);
    }
  });

  console.log('正在查找并点击"查看详情"按钮...');

  // 尝试多种选择器找到"查看详情"按钮
  const selectors = [
    'button:has-text("查看详情")',
    'a:has-text("查看详情")',
    '[class*="detail"]',
    '[class*="view"]',
    'button',
    'a'
  ];

  for (const selector of selectors) {
    try {
      const elements = await page.$$(selector);
      console.log(`找到 ${elements.length} 个元素: ${selector}`);

      for (let i = 0; i < Math.min(elements.length, 20); i++) {
        const el = elements[i];
        const text = await el.evaluate(e => e.innerText || e.textContent || '');
        const href = await el.evaluate(e => e.href || '');

        // 检查是否包含 inviteeUid
        if (href && href.includes('inviteeUid=')) {
          const match = href.match(/inviteeUid=(\d+)/);
          if (match) {
            console.log(`直接找到 UID: ${match[1]} (链接)`);
            allUIDs.add(match[1]);
          }
        }

        // 尝试点击"查看详情"按钮
        if (text.includes('查看详情') || text.includes('详情') || text.includes('查看')) {
          console.log(`点击: ${text}`);
          await el.click();
          await new Promise(r => setTimeout(r, 2000));

          // 检查当前页面 URL
          const currentUrl = page.url();
          const match = currentUrl.match(/inviteeUid=(\d+)/);
          if (match) {
            allUIDs.add(match[1]);
            console.log(`跳转后发现 UID: ${match[1]}`);
            await page.goBack();
            await new Promise(r => setTimeout(r, 1000));
          }
        }
      }
    } catch (e) {
      // 忽略错误继续
    }
  }

  // 最后再检查一遍所有链接
  const links = await page.$$eval('a', els => els.map(a => a.href));
  for (const link of links) {
    const match = link.match(/inviteeUid=(\d+)/);
    if (match) {
      allUIDs.add(match[1]);
    }
  }

  console.log(`\n共找到 ${allUIDs.size} 个下级 UID:`);
  [...allUIDs].forEach(uid => console.log(`  ${uid}`));

  await browser.close();

  // 保存到数据库
  if (allUIDs.size > 0) {
    const { execSync } = require('child_process');
    const py = 'C:\\Users\\Administrator\\.workbuddy\\binaries\\python\\envs\\btc-quant\\Scripts\\python.exe';
    const script = 'c:\\LH\\OKX\\save_uids.py';
    const uidStr = [...allUIDs].join(',');
    console.log('\n正在保存到数据库...');
    execSync(`"${py}" "${script}" "${uidStr}"`, { stdio: 'inherit' });
  }
}

getSubordinateUIDs().catch(console.error);
