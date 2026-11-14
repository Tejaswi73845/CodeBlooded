import { chromium } from "playwright-core";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const OUT = process.env.OUT_DIR ?? "screens";
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: EDGE, headless: true });
const context = await browser.newContext({ viewport: { width: 1440, height: 960 } });
const page = await context.newPage();

const errors = [];
page.on("console", (msg) => {
  if (msg.type() === "error") errors.push(msg.text());
});
page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));

const results = [];
const check = async (name, fn) => {
  try {
    await fn();
    results.push(["PASS", name]);
  } catch (error) {
    results.push(["FAIL", `${name} — ${error.message.split("\n")[0]}`]);
  }
};

await page.goto(BASE, { waitUntil: "networkidle" });
const email = page.locator('input[type="email"]');
if (await email.count()) {
  await email.fill("aarav.shah@kestrel.legal");
  await page.locator('input[type="password"]').fill("tracevault");
  await page.getByRole("button", { name: /^Sign in$/ }).click();
  await page.waitForSelector("aside", { timeout: 20000 });
}
await page.waitForTimeout(1200);

const routes = [
  ["Overview", "Default workspace"],
  ["Evidence Vault", "Evidence Vault"],
  ["Timeline", "Incident Timeline"],
  ["People & Connections", "People & Connections"],
  ["AI Assistant", "AI Assistant"],
  ["Reports", "Reports"],
  ["Audit Logs", "Audit Logs"],
  ["Settings", "Settings"],
];

for (const [label, heading] of routes) {
  await check(`route: ${label}`, async () => {
    await page.getByRole("button", { name: new RegExp(`^${label}`) }).first().click();
    await page.waitForTimeout(700);
    const text = await page.locator("main h1").first().innerText();
    if (!text.includes(heading)) throw new Error(`heading was "${text}"`);
  });
}

await check("vault: drawer opens", async () => {
  await page.getByRole("button", { name: /^Evidence Vault/ }).first().click();
  await page.waitForTimeout(600);
  await page.locator("tbody tr").first().click();
  await page.waitForTimeout(1200);
  await page.getByRole("dialog").waitFor({ state: "visible", timeout: 8000 });
  await page.screenshot({ path: `${OUT}/verify-drawer.png` });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(500);
});

await check("vault: upload dialog opens", async () => {
  const probe = `${OUT}/upload-probe.txt`;
  writeFileSync(probe, "intake probe — safe to discard\n");
  await page.getByRole("button", { name: /^Overview/ }).first().click();
  await page.waitForTimeout(400);
  await page.getByRole("button", { name: /^Evidence Vault/ }).first().click();
  await page.waitForTimeout(600);
  await page.locator('input[type="file"]').setInputFiles(probe);
  await page.getByText("Add evidence details").waitFor({ timeout: 8000 });
  await page.screenshot({ path: `${OUT}/verify-upload.png` });
  await page.getByRole("button", { name: /^Cancel$/ }).click();
  await page.waitForTimeout(400);
});

await check("search: command palette filters", async () => {
  await page.keyboard.press("Control+k");
  const input = page.getByLabel("Search evidence, people and events");
  await input.waitFor({ timeout: 5000 });
  await input.fill("meera");
  await page.waitForTimeout(600);
  const count = await page.locator("[data-index]").count();
  if (count === 0) throw new Error("no results for meera");
  await page.screenshot({ path: `${OUT}/verify-command.png` });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(400);
});

await check("notifications open", async () => {
  await page.getByRole("button", { name: /^Notifications/ }).click();
  await page.getByText("Mark all read").waitFor({ timeout: 5000 });
  await page.screenshot({ path: `${OUT}/verify-notifications.png` });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
});

await check("reports: document settings", async () => {
  await page.getByRole("button", { name: /^Reports/ }).first().click();
  await page.waitForTimeout(700);
  await page.getByRole("button", { name: /Document settings/ }).click();
  await page.getByText("Choose which sections appear").waitFor({ timeout: 5000 });
  await page.screenshot({ path: `${OUT}/verify-settings.png` });
  await page.getByRole("button", { name: /^Done$/ }).click();
  await page.waitForTimeout(300);
});

await check("timeline: edit event dialog", async () => {
  await page.getByRole("button", { name: /^Timeline/ }).first().click();
  await page.waitForTimeout(700);
  await page.getByRole("button", { name: /^Edit$/ }).first().click();
  await page.getByText("Edit timeline event").waitFor({ timeout: 5000 });
  await page.screenshot({ path: `${OUT}/verify-event-edit.png` });
  await page.getByRole("button", { name: /^Cancel$/ }).click();
  await page.waitForTimeout(300);
});

await check("workspace dropdown", async () => {
  await page.locator("aside button").filter({ hasText: "Default workspace" }).first().click();
  await page.getByText("New workspace").waitFor({ timeout: 5000 });
  await page.screenshot({ path: `${OUT}/verify-workspace-menu.png` });
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
});

await check("theme toggle round trip", async () => {
  await page.getByRole("button", { name: /Switch to dark mode/i }).click();
  await page.waitForTimeout(400);
  const dark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  if (!dark) throw new Error("dark class not applied");
  await page.getByRole("button", { name: /Switch to light mode/i }).click();
  await page.waitForTimeout(400);
  const light = await page.evaluate(() => !document.documentElement.classList.contains("dark"));
  if (!light) throw new Error("light class not restored");
});

await check("mobile: navigation sheet", async () => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(400);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.waitForTimeout(500);
  await page.getByRole("dialog").waitFor({ state: "visible", timeout: 5000 });
  await page.screenshot({ path: `${OUT}/verify-mobile-nav.png` });
  await page.getByRole("button", { name: /^Overview/ }).last().click();
  await page.waitForTimeout(500);
});

for (const [status, name] of results) console.log(`${status}  ${name}`);
if (errors.length) {
  console.log("\nConsole errors:");
  for (const error of errors) console.log(" -", error);
}
await browser.close();
process.exit(results.some(([status]) => status === "FAIL") || errors.length ? 1 : 0);
