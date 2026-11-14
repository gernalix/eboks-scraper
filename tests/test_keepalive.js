// Focused MV3 keepalive test: no browser profile or e-Boks access needed.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

(async function test() {
  const source = fs.readFileSync(__dirname + "/../extension/inbox-keepalive/worker.js", "utf8");
  const manifest = JSON.parse(fs.readFileSync(__dirname + "/../extension/inbox-keepalive/manifest.json"));
  assert(manifest.permissions.includes("alarms"));
  assert(!manifest.permissions.includes("nativeMessaging"));
  assert(!manifest.content_scripts);

  const listeners = {};
  const alarms = [];
  const executed = [];
  let clicked = 0;
  let selectionActive = false;
  let dialogOpen = false;
  let userEditing = false;
  const inbox = {
    innerText: "Posta in arrivo (55)",
    getAttribute() {return "";},
    getBoundingClientRect() {return {width: 100, height: 22};},
    click() {clicked++;},
    closest() {return this;},
    disabled: false,
  };
  const checkbox = {
    get checked() {return selectionActive;},
    getAttribute() {return null;},
  };
  const doc = {
    get activeElement() {
      return {matches() {return userEditing;}};
    },
    querySelector(selector) {
      if (selector.includes("dialog")) return dialogOpen ? {} : null;
      return null;
    },
    querySelectorAll(selector) {
      if (selector.includes("input[type=\"checkbox\"]")) return [checkbox];
      return [inbox];
    },
  };
  const context = {
    URL, console, document: doc,
    getComputedStyle() {return {display: "block", visibility: "visible"};},
    chrome: {
      runtime: {
        onInstalled: {addListener(fn) {listeners.installed = fn;}},
        onStartup: {addListener(fn) {listeners.startup = fn;}},
      },
      alarms: {
        async get() {return null;},
        async create(name, options) {alarms.push({name, options});},
        onAlarm: {addListener(fn) {listeners.alarm = fn;}},
      },
      action: {onClicked: {addListener(fn) {listeners.action = fn;}}},
      tabs: {
        async query() {return [
          {id: 1, url: "https://digitalpost.e-boks.dk/mailbox"},
          {id: 2, url: "https://digitalpost.e-boks.dk/login"},
          {id: 3, url: "https://www.e-boks.dk/privat/#/overview"},
          {id: 4, url: "https://mitid.dk/login"},
        ]},
      },
      scripting: {
        async executeScript({target, func}) {
          executed.push(target.tabId);
          return [{result: func()}];
        },
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(source, context);
  const tick = () => new Promise(resolve => setTimeout(resolve, 0));
  await tick();
  assert.equal(alarms.length, 1, "Must register exactly one alarm");
  assert.equal(alarms[0].options.periodInMinutes, 1);
  assert.equal(alarms[0].options.delayInMinutes, 1);
  assert.equal(typeof listeners.startup, "function");
  assert.equal(typeof listeners.installed, "function");
  assert.equal(typeof listeners.alarm, "function");
  assert.equal(typeof listeners.action, "function");
  listeners.alarm({name: "some-other-alarm"});
  await tick();
  assert.equal(executed.length, 0);
  listeners.alarm({name: "eboks-inbox-keepalive"});
  await tick();
  assert.deepEqual(executed, [1], "Only authenticated inbox should be injected");
  assert.equal(clicked, 1);

  for (const state of ["selectionActive", "dialogOpen", "userEditing"]) {
    if (state === "selectionActive") selectionActive = true;
    if (state === "dialogOpen") dialogOpen = true;
    if (state === "userEditing") userEditing = true;
    listeners.alarm({name: "eboks-inbox-keepalive"});
    await tick();
    assert.equal(clicked, 1, "Must not disrupt ongoing user interaction");
    selectionActive = dialogOpen = userEditing = false;
  }
  console.log("PASS: 1-minute alarm; authenticated inbox only; skips selections/dialogs/editing");
})().catch(error => {console.error(error); process.exitCode = 1;});
