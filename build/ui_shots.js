/* UI 重构视觉验证截图：桌面 + 移动端 */
const { chromium } = require('playwright-core');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const BASE = 'http://127.0.0.1:5270';
const OUT = 'C:/Users/Amy/WorkBuddy/人事工作台/docs/ui_shots';

async function shot(page, name, path) {
  await page.goto(BASE + path, { waitUntil: 'networkidle' });
  await page.waitForTimeout(400);
  await page.screenshot({ path: OUT + '/' + name, fullPage: false });
  console.log('saved', name);
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME, headless: true });
  try {
    // 桌面
    const d = await browser.newContext({ viewport: { width: 1366, height: 800 }, deviceScaleFactor: 1 });
    const dp = await d.newPage();
    await shot(dp, 'desk-dashboard.png', '/');
    await shot(dp, 'desk-employees.png', '/employees');
    await shot(dp, 'desk-contract.png', '/contract');
    await shot(dp, 'desk-resume.png', '/resume');
    await shot(dp, 'desk-login.png', '/login');
    await d.close();

    // 移动端（抽屉收起态 + 展开态）
    const m = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1, isMobile: true });
    const mp = await m.newPage();
    await shot(mp, 'mob-dashboard-closed.png', '/');
    await mp.click('.menu-btn');
    await mp.waitForTimeout(450);
    await mp.screenshot({ path: OUT + '/mob-dashboard-drawer.png' });
    console.log('saved mob-dashboard-drawer.png');
    await m.close();
  } finally {
    await browser.close();
  }
})();
