#!/usr/bin/env node
/**
 * md-2-pdf: Markdown → PDF converter
 *
 * Features:
 *   - Chinese font support (Noto Serif CJK / PingFang etc.)
 *   - Mermaid diagram rendering (sequenceDiagram / stateDiagram / flowchart ...)
 *   - GitHub-flavored markdown + syntax highlighting
 *   - Cross-platform: auto-detects system Chrome/Chromium (Linux & macOS)
 *
 * Usage:
 *   node convert.mjs <input.md> [output.pdf]
 *   If output.pdf is omitted, defaults to <input>.pdf next to the input.
 */
import fs from 'fs/promises';
import { existsSync } from 'fs';
import path from 'path';
import os from 'os';
import process from 'process';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import puppeteer from 'puppeteer';

function detectChromeExecutable() {
  if (process.env.CHROME_PATH && existsSync(process.env.CHROME_PATH)) {
    return process.env.CHROME_PATH;
  }
  const platform = os.platform();
  const candidates = platform === 'darwin'
    ? [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
      ]
    : [
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/snap/bin/chromium',
        '/opt/google/chrome/chrome',
      ];
  for (const p of candidates) {
    if (existsSync(p)) return p;
  }
  throw new Error(
    'Cannot find Chrome/Chromium. Set CHROME_PATH env var to override.\n' +
    `Tried: ${candidates.join(', ')}`,
  );
}

function buildMarkdownRenderer() {
  const mdit = new MarkdownIt({
    html: true,
    linkify: true,
    breaks: false,
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        try {
          return `<pre class="hljs"><code class="language-${lang}">${
            hljs.highlight(code, { language: lang, ignoreIllegals: true }).value
          }</code></pre>`;
        } catch (_) {}
      }
      return `<pre class="hljs"><code>${mdit.utils.escapeHtml(code)}</code></pre>`;
    },
  });

  const defaultFence = mdit.renderer.rules.fence;
  mdit.renderer.rules.fence = (tokens, idx, options, env, slf) => {
    const token = tokens[idx];
    const info = token.info ? token.info.trim() : '';
    if (info === 'mermaid') {
      const escaped = token.content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
      return `<div class="mermaid">${escaped}</div>\n`;
    }
    return defaultFence(tokens, idx, options, env, slf);
  };

  return mdit;
}

function buildHtmlTemplate(title, body) {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>${title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.10.0/styles/github.min.css">
<style>
  @page { size: A4; margin: 18mm 14mm; }
  body {
    font-family: "Noto Serif CJK SC", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 11pt;
    line-height: 1.7;
    color: #1f2328;
    max-width: 100%;
  }
  h1, h2, h3, h4, h5 {
    font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-weight: 600;
    line-height: 1.3;
    margin-top: 1.4em;
    margin-bottom: 0.6em;
    color: #1f2328;
    page-break-after: avoid;
  }
  h1 { font-size: 22pt; border-bottom: 2px solid #d0d7de; padding-bottom: 6px; }
  h2 { font-size: 17pt; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; }
  h3 { font-size: 14pt; }
  h4 { font-size: 12pt; }
  p { margin: 0.6em 0; }
  ul, ol { margin: 0.4em 0; padding-left: 1.6em; }
  li { margin: 0.15em 0; }
  code {
    font-family: "DejaVu Sans Mono", "Menlo", "Source Code Pro", Consolas, monospace;
    font-size: 0.88em;
    background: #f6f8fa;
    padding: 0.1em 0.35em;
    border-radius: 4px;
  }
  pre {
    background: #f6f8fa;
    padding: 12px 14px;
    border-radius: 6px;
    overflow: auto;
    font-size: 9.5pt;
    line-height: 1.5;
    page-break-inside: avoid;
  }
  pre code { background: transparent; padding: 0; font-size: inherit; }
  table { border-collapse: collapse; margin: 12px 0; width: 100%; page-break-inside: avoid; }
  th, td { border: 1px solid #d0d7de; padding: 6px 10px; font-size: 10pt; text-align: left; vertical-align: top; }
  th { background: #f6f8fa; font-weight: 600; }
  blockquote {
    border-left: 4px solid #d0d7de;
    margin: 0.8em 0;
    padding: 0.2em 0 0.2em 1em;
    color: #57606a;
    background: #f6f8fa;
    border-radius: 0 4px 4px 0;
  }
  a { color: #0969da; text-decoration: none; }
  hr { border: none; border-top: 1px solid #d0d7de; margin: 1.5em 0; }
  img { max-width: 100%; }
  .mermaid { text-align: center; margin: 18px 0; page-break-inside: avoid; }
</style>
</head>
<body>
${body}
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
  mermaid.initialize({
    startOnLoad: false,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: '"Noto Sans CJK SC", "PingFang SC", sans-serif',
  });
  (async () => {
    try {
      await mermaid.run({ querySelector: '.mermaid' });
    } catch (e) {
      console.error('mermaid error:', e);
    } finally {
      window.__mermaidReady__ = true;
    }
  })();
</script>
</body>
</html>`;
}

async function main() {
  const [, , inputArg, outputArg] = process.argv;
  if (!inputArg) {
    console.error('Usage: node convert.mjs <input.md> [output.pdf]');
    process.exit(1);
  }
  const inputPath = path.resolve(inputArg);
  if (!existsSync(inputPath)) {
    console.error(`Input file not found: ${inputPath}`);
    process.exit(1);
  }
  const outputPath = outputArg
    ? path.resolve(outputArg)
    : path.join(path.dirname(inputPath), path.basename(inputPath, path.extname(inputPath)) + '.pdf');

  const md = await fs.readFile(inputPath, 'utf-8');
  const mdit = buildMarkdownRenderer();
  const body = mdit.render(md);
  const title = path.basename(inputPath, path.extname(inputPath));
  const html = buildHtmlTemplate(title, body);

  const htmlPath = path.join(path.dirname(outputPath), `.tmp_md2pdf_${process.pid}.html`);
  await fs.writeFile(htmlPath, html, 'utf-8');

  const executablePath = detectChromeExecutable();
  console.log(`[md2pdf] using browser: ${executablePath}`);

  const browser = await puppeteer.launch({
    executablePath,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
    headless: 'new',
  });

  try {
    const page = await browser.newPage();
    await page.goto('file://' + htmlPath, { waitUntil: 'networkidle0', timeout: 60000 });
    await page.waitForFunction('window.__mermaidReady__ === true', { timeout: 30000 }).catch(() => {
      console.warn('[md2pdf] warning: mermaid render flag not set; continuing.');
    });
    await new Promise(r => setTimeout(r, 500));
    await page.pdf({
      path: outputPath,
      format: 'A4',
      printBackground: true,
      margin: { top: '18mm', right: '14mm', bottom: '18mm', left: '14mm' },
      displayHeaderFooter: false,
    });
  } finally {
    await browser.close();
    await fs.unlink(htmlPath).catch(() => {});
  }

  console.log(`[md2pdf] OK: ${outputPath}`);
}

main().catch(err => {
  console.error('[md2pdf] FAIL:', err.message);
  process.exit(1);
});
