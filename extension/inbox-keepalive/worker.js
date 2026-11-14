const HOST = "com.gernalix.eboks_keepalive";
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

function clickInboxInPage() {
  const norm = (value) =>
    (value || "").normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
  const exactLabels = new Set(["indbakke", "inbox", "posta in arrivo"]);
  const containsLabels = ["indbakke", "inbox", "posta in arrivo"];

  const candidates = [...document.querySelectorAll(
    'a, button, [role="button"], [role="link"], [role="menuitem"]'
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
    let score = 0;
    if (values.some((v) => exactLabels.has(v))) score = 100;
    else if (values.some((v) => containsLabels.some((label) => v.includes(label)))) score = 50;
    return {el, score, text, aria, title};
  }).filter((x) => x.score > 0).sort((a, b) => b.score - a.score);

  if (!scored.length) {
    const page = norm(document.body?.innerText || "");
    const loggedOut = /\bmitid\b|\blog ind\b|\blogin\b/.test(page);
    return {
      ok: false,
      clicked: false,
      reason: loggedOut ? "login_or_mitid_visible" : "inbox_not_found",
      url: location.href,
    };
  }

  const chosen = scored[0];
  chosen.el.click();
  return {
    ok: true,
    clicked: true,
    reason: "clicked",
    label: chosen.text || chosen.aria || chosen.title,
    url: location.href,
  };
}
