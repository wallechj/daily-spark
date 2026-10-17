// Daily Spark — 每日灵感小站
const $ = (id) => document.getElementById(id);

// ---------- 主题 ----------
const themeBtn = $("themeBtn");
function applyTheme(t) {
  document.documentElement.dataset.theme = t;
  themeBtn.textContent = t === "dark" ? "☀️" : "🌙";
  localStorage.setItem("ds-theme", t);
}
applyTheme(localStorage.getItem("ds-theme") || "light");
themeBtn.onclick = () =>
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");

// ---------- 日期 ----------
$("todayDate").textContent = new Date().toLocaleDateString("zh-CN", {
  year: "numeric", month: "long", day: "numeric", weekday: "long",
});

// ---------- 每日一句 ----------
let quotes = [];
let quoteIdx = 0;
async function loadQuotes() {
  try {
    const res = await fetch("data/quotes.json");
    quotes = await res.json();
  } catch (e) {
    quotes = [{ zh: "把今天过好，就是对未来最好的准备。", en: "Living today well is the best preparation for tomorrow." }];
  }
  // 按日期固定轮换：同一天看到同一句
  const dayNum = Math.floor(Date.now() / 86400000);
  quoteIdx = dayNum % quotes.length;
  renderQuote();
  $("quoteCount").textContent = seenQuotes().size;
}
function renderQuote() {
  const q = quotes[quoteIdx % quotes.length];
  $("quoteZh").textContent = q.zh;
  $("quoteEn").textContent = q.en;
  const seen = seenQuotes();
  seen.add(quoteIdx % quotes.length);
  localStorage.setItem("ds-seen", JSON.stringify([...seen]));
  $("quoteCount").textContent = seen.size;
}
function seenQuotes() {
  try { return new Set(JSON.parse(localStorage.getItem("ds-seen") || "[]")); }
  catch { return new Set(); }
}
$("newQuoteBtn").onclick = () => {
  quoteIdx = (quoteIdx + 1) % quotes.length;
  renderQuote();
};
loadQuotes();

// ---------- 番茄钟 ----------
const FOCUS_LEN = 25 * 60;
let remain = FOCUS_LEN, timerId = null;
function fmt(s) {
  return String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
}
function todayKey() { return "ds-focus-" + new Date().toISOString().slice(0, 10); }
function getDone() { return parseInt(localStorage.getItem(todayKey()) || "0", 10); }
function refreshDone() {
  $("doneCount").textContent = getDone();
  let total = 0;
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k && k.startsWith("ds-focus-")) total += parseInt(localStorage.getItem(k) || "0", 10);
  }
  $("focusTotal").textContent = total;
}
$("timerToggle").onclick = () => {
  if (timerId) {
    clearInterval(timerId); timerId = null;
    $("timerToggle").textContent = "继续专注";
    return;
  }
  $("timerToggle").textContent = "暂停";
  timerId = setInterval(() => {
    remain--;
    $("timerDisplay").textContent = fmt(remain);
    if (remain <= 0) {
      clearInterval(timerId); timerId = null;
      remain = FOCUS_LEN;
      $("timerDisplay").textContent = fmt(remain);
      $("timerToggle").textContent = "开始专注";
      localStorage.setItem(todayKey(), String(getDone() + 1));
      refreshDone();
      alert("🎉 完成一个番茄！休息一下吧～");
    }
  }, 1000);
};
$("timerReset").onclick = () => {
  clearInterval(timerId); timerId = null;
  remain = FOCUS_LEN;
  $("timerDisplay").textContent = fmt(remain);
  $("timerToggle").textContent = "开始专注";
};
refreshDone();

// ---------- 小确幸 ----------
function joyKey() { return "ds-joy-" + new Date().toISOString().slice(0, 10); }
function getJoys() {
  try { return JSON.parse(localStorage.getItem(joyKey()) || "[]"); }
  catch { return []; }
}
function renderJoys() {
  const list = $("joyList");
  list.innerHTML = "";
  getJoys().forEach((text, i) => {
    const li = document.createElement("li");
    li.innerHTML = "<span></span>";
    li.querySelector("span").textContent = text;
    const del = document.createElement("button");
    del.textContent = "✕";
    del.onclick = () => {
      const arr = getJoys(); arr.splice(i, 1);
      localStorage.setItem(joyKey(), JSON.stringify(arr));
      renderJoys(); refreshJoyTotal();
    };
    li.appendChild(del);
    list.appendChild(li);
  });
}
function refreshJoyTotal() {
  let total = 0;
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    if (k && k.startsWith("ds-joy-")) {
      try { total += JSON.parse(localStorage.getItem(k) || "[]").length; } catch {}
    }
  }
  $("joyTotal").textContent = total;
}
$("joyForm").onsubmit = (e) => {
  e.preventDefault();
  const v = $("joyInput").value.trim();
  if (!v) return;
  const arr = getJoys(); arr.push(v);
  localStorage.setItem(joyKey(), JSON.stringify(arr));
  $("joyInput").value = "";
  renderJoys(); refreshJoyTotal();
};
renderJoys(); refreshJoyTotal();
