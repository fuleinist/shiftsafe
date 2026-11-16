/**
 * Capture README screenshots from a running shiftsafe server.
 *
 * Usage:
 *   node scripts/screenshot.cjs "http://127.0.0.1:8123/?place=darwin&..." docs/screenshots
 *
 * Requires the workspace playwright install.
 */
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const url = process.argv[2] || "http://127.0.0.1:8123/";
const outDir = process.argv[3] || "docs/screenshots";
const errors = [];

function watch(page) {
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`[console] ${message.text()}`);
  });
  page.on("pageerror", (error) => errors.push(`[pageerror] ${String(error)}`));
  page.on("requestfailed", (request) =>
    errors.push(`[requestfailed] ${request.url()} ${request.failure()?.errorText ?? ""}`)
  );
}

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const launchOptions = { args: ["--disable-gpu", "--no-sandbox"] };
  let browser;
  try {
    browser = await chromium.launch(launchOptions);
  } catch (bundledError) {
    console.log(`Bundled Chromium unavailable, trying system Chrome.`);
    try {
      browser = await chromium.launch({ ...launchOptions, channel: "chrome" });
    } catch (chromeError) {
      console.log(`System Chrome unavailable, trying Edge.`);
      browser = await chromium.launch({ ...launchOptions, channel: "msedge" });
    }
  }
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  watch(page);

  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForSelector("#output:not([hidden])", { timeout: 20000 });
  await page.waitForSelector("#table tbody tr", { timeout: 20000 });
  await page.waitForTimeout(600);

  const rows = await page.locator("#table tbody tr").count();
  console.log(`Plan rendered with ${rows} hourly rows.`);

  await page.screenshot({ path: path.join(outDir, "plan-desktop.png"), fullPage: true });

  const card = page.locator("#crew-card");
  await card.screenshot({ path: path.join(outDir, "crew-card.png") });

  await browser.close();

  for (const file of fs.readdirSync(outDir).filter((name) => name.endsWith(".png"))) {
    const size = fs.statSync(path.join(outDir, file)).size;
    if (size > 500 * 1024) {
      console.log(`WARNING ${file} is ${Math.round(size / 1024)} KB, over 500 KB.`);
    }
    console.log(`${file}: ${Math.round(size / 1024)} KB`);
  }

  if (errors.length > 0) {
    console.error("CONSOLE_ERRORS");
    for (const error of errors) console.error(error);
    process.exit(1);
  }
  console.log("No console errors. No failed requests.");
})().catch((error) => {
  console.error(`FATAL: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
});