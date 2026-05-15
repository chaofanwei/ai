const http = require('http');
const { chromium } = require('playwright-core');
const {
  bindDialogLogger,
  fillApplyForm,
  loadRelease,
  usage,
} = require('./release_apply_common');

const CDP_URL = process.env.CDP_URL || 'http://127.0.0.1:9222';

function checkCdpEndpoint(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(`${url.replace(/\/$/, '')}/json/version`, (res) => {
      res.resume();
      if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
        resolve();
        return;
      }
      reject(new Error(`CDP endpoint responded with HTTP ${res.statusCode}`));
    });
    req.setTimeout(3000, () => {
      req.destroy(new Error('CDP endpoint check timed out'));
    });
    req.on('error', reject);
  });
}

async function main() {
  const releaseFile = process.argv[2];
  if (!releaseFile) usage('scripts/fill_release_apply_cdp.js');
  const release = loadRelease(releaseFile);

  try {
    await checkCdpEndpoint(CDP_URL);
  } catch (err) {
    throw new Error(
      `Cannot connect to Chrome CDP at ${CDP_URL}: ${err.message}\n` +
      'Start the Playwright MCP Chrome first, for example: ~/shells/start_ai-chrome.sh',
    );
  }

  const browser = await chromium.connectOverCDP(CDP_URL);
  const context = browser.contexts()[0] || await browser.newContext();
  const page = await context.newPage();
  bindDialogLogger(page);

  await fillApplyForm(page, release);
  process.exit(0);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
