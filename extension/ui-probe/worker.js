chrome.action.onClicked.addListener(async (tab) => {
  if (!tab.id || !/^https:\/\/(?:[^/]+\.)?e-boks\.(?:dk|com)\//.test(tab.url || '')) return;
  const injected = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: () => {
      const visible = (el) => {
        const s = getComputedStyle(el), r = el.getBoundingClientRect();
        return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
      };
      const description = (el) => ({
        tag: el.tagName.toLowerCase(), role: el.getAttribute('role') || '',
        type: el.getAttribute('type') || '', aria: el.getAttribute('aria-label') || '',
        title: el.getAttribute('title') || '',
        text: (el.matches('button,a,[role="button"],[role="menuitem"],[role="option"]') ? (el.innerText || '').trim().slice(0, 160) : ''),
        disabled: Boolean(el.disabled || el.getAttribute('aria-disabled') === 'true'),
        checked: el.matches('input[type="checkbox"],[role="checkbox"]') ? (el.matches('input') ? el.checked : el.getAttribute('aria-checked')) : undefined
      });
      const words = /download|save|local|copy|select|all|export|gem|hent|vælg|markér|pdf|zip/i;
      const controls = [...document.querySelectorAll('button,a,input,select,[role="button"],[role="checkbox"],[role="menuitem"],[role="option"]')]
        .filter(visible).map(description).filter((x) => words.test(`${x.aria} ${x.title} ${x.text}`));
      const boxes = [...document.querySelectorAll('input[type="checkbox"],[role="checkbox"]')].filter(visible).map(description);
      document.getElementById('__eboks_ondemand_probe__')?.remove();
      const panel = document.createElement('pre');
      panel.id = '__eboks_ondemand_probe__';
      const report = {checkbox_count: boxes.length, checkboxes: boxes, export_controls: controls};
      panel.textContent = JSON.stringify(report, null, 2);
      Object.assign(panel.style, {position:'fixed',right:'8px',bottom:'8px',zIndex:'2147483647',maxWidth:'45vw',maxHeight:'45vh',overflow:'auto',padding:'8px',margin:'0',background:'#111',color:'#0f0',font:'11px monospace',whiteSpace:'pre-wrap',border:'1px solid #0f0'});
      document.documentElement.append(panel);
      return report;
    }
  });
  await chrome.runtime.sendNativeMessage('com.gernalix.eboks_ui_probe', injected[0]?.result || {});
});
