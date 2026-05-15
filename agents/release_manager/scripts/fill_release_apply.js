const { chromium } = require('playwright-core');
const {
  bindDialogLogger,
  fillApplyForm,
  loadRelease,
  usage,
} = require('./release_apply_common');

const PROFILE_DIR = process.env.RELEASE_MGMT_PROFILE_DIR || '/tmp/release_mgmt_pw_profile';
const CHROME_PATH = process.env.CHROME_PATH || '/usr/bin/google-chrome';

async function main() {
  const releaseFile = process.argv[2];
  if (!releaseFile) usage('scripts/fill_release_apply.js');
  const release = loadRelease(releaseFile);

  const context = await chromium.launchPersistentContext(PROFILE_DIR, {
    executablePath: CHROME_PATH,
    headless: false,
    viewport: null,
    args: ['--start-maximized'],
  });
  const page = context.pages()[0] || await context.newPage();
  bindDialogLogger(page);
  await fillApplyForm(page, release);
  await new Promise(() => {});
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
