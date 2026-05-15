const fs = require('fs');
const path = require('path');

const APPLY_URL = 'http://release-mgmt.qiyi.domain/release_manage/relApply/app/apply_add';

function usage(scriptName) {
  console.error(`Usage: node ${scriptName} <release-file>`);
  process.exit(1);
}

function extractIssues(noteText) {
  const issues = [];
  for (const line of noteText.split(/\r?\n/)) {
    const match = line.match(/^\d+\.\s+(.+?)：http:\/\/pms\.qiyi\.domain\/browse\/(VIDEODEV-\d+)/);
    if (match) {
      issues.push({ id: match[2], label: `[${match[2]}]${match[1]}` });
    }
  }
  return issues;
}

function loadRelease(releaseFile) {
  const releasePath = path.resolve(process.cwd(), releaseFile);
  const fileName = path.basename(releasePath);
  const noteText = fs.readFileSync(releasePath, 'utf8');
  const issues = extractIssues(noteText);
  if (!issues.length) {
    throw new Error(`No PMS IDs found in ${releaseFile}`);
  }

  return {
    fileName,
    noteText,
    issues,
    issueIds: issues.map((x) => x.id).join(','),
    issueKeys: issues.map((x) => x.label).join(','),
    mailTitle: `VRS上线申请(${fileName})`,
  };
}

async function waitForApplyPage(page) {
  if (page.url().includes('sso.qiyi.com')) {
    console.log('Waiting for SSO login. Complete login in the opened Chrome window.');
  }
  await page.waitForFunction(
    () => location.hostname.includes('release-mgmt.qiyi.domain') && location.href.includes('/apply_add'),
    { timeout: 10 * 60 * 1000 },
  );
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2500);
}

async function fillApplyForm(page, release) {
  await page.goto(APPLY_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await waitForApplyPage(page);

  await page.evaluate(({ issueIds, issueKeys, noteText, mailTitle }) => {
    window.chooseJira({ issueIds, issueKeys });

    if (window.CKEDITOR?.instances?.description) {
      window.CKEDITOR.instances.description.setData(noteText.replace(/\n/g, '<br>'));
    }
    const description = document.querySelector('#description');
    if (description) {
      description.value = noteText;
      description.dispatchEvent(new Event('input', { bubbles: true }));
      description.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const title = document.querySelector('#mailTitle');
    if (title) {
      title.value = mailTitle;
      title.dispatchEvent(new Event('input', { bubbles: true }));
      title.dispatchEvent(new Event('change', { bubbles: true }));
    }

    const checkbox = document.querySelector('#ifMailTitle');
    if (checkbox && !checkbox.checked) {
      checkbox.click();
    }
  }, release);

  await page.waitForTimeout(5000);
  const values = await page.evaluate(() => ({
    JiraKey: document.querySelector('#JiraKey')?.value || '',
    summary: document.querySelector('#summary')?.value || '',
    mailTitle: document.querySelector('#mailTitle')?.value || '',
    ifMailTitle: !!document.querySelector('#ifMailTitle')?.checked,
    descriptionText:
      window.CKEDITOR?.instances?.description?.editable?.().getText?.() ||
      document.querySelector('#description')?.value ||
      '',
  }));

  console.log(JSON.stringify({
    issueCount: release.issues.length,
    JiraKey: values.JiraKey,
    summaryLength: values.summary.length,
    mailTitle: values.mailTitle,
    ifMailTitle: values.ifMailTitle,
    descriptionLength: values.descriptionText.length,
  }, null, 2));

  await page.screenshot({ path: `/tmp/release_apply_${release.fileName}.png`, fullPage: true });
  console.log(`Filled apply form for ${release.fileName}. Review the browser manually; submit is not clicked.`);
}

function bindDialogLogger(page) {
  page.on('dialog', async (dialog) => {
    console.log(`Dialog: ${dialog.message()}`);
    await dialog.accept();
  });
}

module.exports = {
  APPLY_URL,
  bindDialogLogger,
  fillApplyForm,
  loadRelease,
  usage,
};
