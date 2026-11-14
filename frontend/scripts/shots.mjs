import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const OUT = process.env.OUT_DIR ?? "screens";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

const routes = [
  ["overview", "Overview"],
  ["vault", "Evidence Vault"],
  ["timeline", "Timeline"],
  ["people", "People & Connections"],
  ["assistant", "AI Assistant"],
  ["reports", "Reports"],
  ["audit", "Audit Logs"],
  ["settings", "Settings"],
];

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: EDGE, headless: true });

// Auth screen, unauthenticated.
{
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
  const page = await context.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/desktop-auth.png` });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/mobile-auth.png` });
  await context.close();
  console.log("shot auth");
}

const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, deviceScaleFactor: 1 });
const page = await context.newPage();
await page.goto(BASE, { waitUntil: "networkidle" });

const email = page.locator('input[type="email"]');
if (await email.count()) {
  await email.fill("aarav.shah@kestrel.legal");
  await page.locator('input[type="password"]').fill("tracevault");
  await page.getByRole("button", { name: /^Sign in$/ }).click();
  await page.waitForSelector("aside", { timeout: 20000 });
}
await page.waitForTimeout(1200);

for (const [id, label] of routes) {
  const nav = page.getByRole("button", { name: new RegExp(`^${label}`) }).first();
  if (await nav.count()) await nav.click();
  await page.waitForTimeout(id === "reports" ? 2500 : 1200);
  await page.screenshot({ path: `${OUT}/desktop-${id}.png` });
  console.log("shot", id);
}

// Evidence drawer.
await page.getByRole("button", { name: /^Evidence Vault/ }).first().click();
await page.waitForTimeout(800);
const row = page.locator("tbody tr").first();
if (await row.count()) {
  await row.click();
  await page.waitForTimeout(1400);
  await page.screenshot({ path: `${OUT}/desktop-drawer.png` });
  console.log("shot drawer");
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
}

// Command palette.
await page.keyboard.press("Control+k");
await page.waitForTimeout(600);
await page.screenshot({ path: `${OUT}/desktop-command.png` });
await page.keyboard.press("Escape");
console.log("shot command");

// Dark mode.
await page.getByRole("button", { name: /Switch to dark mode/i }).click();
await page.waitForTimeout(500);
await page.getByRole("button", { name: /^Overview$/ }).first().click();
await page.waitForTimeout(800);
await page.screenshot({ path: `${OUT}/desktop-overview-dark.png` });
await page.getByRole("button", { name: /^Timeline$/ }).first().click();
await page.waitForTimeout(900);
await page.screenshot({ path: `${OUT}/desktop-timeline-dark.png` });
console.log("shot dark");
await page.getByRole("button", { name: /Switch to light mode/i }).click();

// Mobile.
await page.setViewportSize({ width: 390, height: 844 });
for (const [id, label] of [
  ["overview", "Overview"],
  ["vault", "Evidence Vault"],
  ["timeline", "Timeline"],
  ["reports", "Reports"],
]) {
  const menu = page.getByRole("button", { name: "Open navigation" });
  if (await menu.count()) {
    await menu.click();
    await page.waitForTimeout(400);
  }
  const nav = page.getByRole("button", { name: new RegExp(`^${label}`) }).first();
  if (await nav.count()) await nav.click();
  await page.waitForTimeout(1000);
  await page.screenshot({ path: `${OUT}/mobile-${id}.png` });
  console.log("shot mobile", id);
}

await browser.close();
