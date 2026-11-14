// Keepalive only within an already authenticated e-Boks inbox.
// No persistent page scripts, cookies, private APIs, or MitID interaction.
const ALARM = "eboks-inbox-keepalive";
const URL_PATTERNS = [
  "https://e-boks.dk/*",
  "https://*.e-boks.dk/*",
  "https://eboks.dk/*",
  "https://*.eboks.dk/*",
  "https://e-boks.com/*",
  "https://*.e-boks.com/*",
  "https://eboks.com/*",
  "https://*.eboks.com/*",
];

function isInboxUrl(url) {
  try {
    const parsed = new URL(url);
    if (parsed.protocol !== "https:") return false;
    const host = parsed.hostname;
    if (host === "digitalpost.e-boks.dk") {
      return parsed.pathname === "/mailbox" || parsed.pathname.startsWith("/mailbox/");
    }
    if (["www.e-boks.dk", "e-boks.dk", "private.e-boks.com"].includes(host)) {
      return parsed.hash.startsWith("#/mailbox");
    }
    return false;
  } catch (_) {
    return false;
  }
}

function clickInboxInPage() {
  const norm = (value) =>
    (value || "").normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
  const exactLabels = new Set(["indbakke", "inbox", "posta in arrivo"]);
  const containsLabels = ["indbakke", "inbox", "posta in arrivo"];

  // A scheduled refresh must never disrupt a selected batch or an export dialog.
  if (document.querySelector('[role="dialog"], dialog[open]')) {
    return {ok: false, clicked: false, reason: "dialog_open"};
  }
  if ([...document.querySelectorAll('input[type="checkbox"], [role="checkbox"]')].some(
    (el) => el.checked === true || el.getAttribute("aria-checked") === "true"
  )) {
    return {ok: false, clicked: false, reason: "selection_active"};
  }
  if (document.activeElement?.matches?.(
    'input:not([type="checkbox"]), textarea, select, [contenteditable="true"]'
  )) {
    return {ok: false, clicked: false, reason: "user_editing"};
  }
  const candidates = [...document.querySelectorAll(
    'a, button, [role="button"], [role="link"], [role="menuitem"], li, span, div'
  )].filter((el) => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" &&
      rect.width > 0 && rect.height > 0 &&
      !el.disabled && el.getAttribute("aria-disabled") !== "true";
  });

  const scored = candidates.map((el) => {
    const text = norm(el.innerText || el.textContent);
    const aria = norm(el.getAttribute("aria-label"));
    const title = norm(el.getAttribute("title"));
    const values = [text, aria, title].filter(Boolean);
    const exact = values.some((v) => exactLabels.has(v));
    const partial = values.some((v) => v.length <= 48 &&
      containsLabels.some((label) => v.startsWith(label)));
    const score = exact ? 100 : partial ? 50 : 0;
    return {el, score};
  }).filter((x) => x.score > 0).sort((a, b) => b.score - a.score);

  if (!scored.length) {
    return {ok: false, clicked: false, reason: "inbox_not_found"};
  }
  const chosen = scored[0].el;
  (chosen.closest?.('a, button, [role="button"], [role="link"], [role="menuitem"]') || chosen).click();
  return {ok: true, clicked: true, reason: "clicked"};
}

async function runKeepalive() {
  // Never target login, MitID or other browser pages.
  const tabs = await chrome.tabs.query({url: URL_PATTERNS});
  const inboxTabs = tabs.filter((tab) => tab.id != null && isInboxUrl(tab.url));
  for (const tab of inboxTabs) {
    try {
      const results = await chrome.scripting.executeScript({
        target: {tabId: tab.id},
        func: clickInboxInPage,
      });
      console.info("e-Boks keepalive", results[0]?.result?.reason || "no_result");
    } catch (error) {
      console.warn("e-Boks keepalive skipped:", error.message);
    }
  }
}

async function ensureAlarm() {
  const existing = await chrome.alarms.get(ALARM);
  if (!existing) {
    await chrome.alarms.create(ALARM, {delayInMinutes: 1, periodInMinutes: 1});
  }
}

chrome.runtime.onInstalled.addListener(() => { void ensureAlarm(); });
chrome.runtime.onStartup.addListener(() => { void ensureAlarm(); });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === ALARM) void runKeepalive();
});
chrome.action.onClicked.addListener(() => { void runKeepalive(); });
// Also repair missing alarms when a previously-installed service worker wakes up.
void ensureAlarm();
