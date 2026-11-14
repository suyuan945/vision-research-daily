const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));
const tagsHTML = (tags = []) => '<div class="tag-list">'
  + tags.slice(0, 5).map(tag => '<span class="tag">' + escapeHTML(tag) + '</span>').join("")
  + '</div>';

const statuses = { unread: "待读", reading: "精读中", reproduce: "待复现", done: "已完成" };
const routes = ["today", "papers", "favorites", "archive"];
let digests = [];
let papers = [];
let byId = new Map();
let currentRoute;

function paperCard(paper, saved) {
  const state = saved[paper.id] || { starred: false, status: "unread" };
  const detail = "papers/" + encodeURIComponent(paper.id) + ".html";
  const published = paper.published ? " · 发表于 " + escapeHTML(paper.published.slice(0, 10)) : "";
  const summary = paper.abstract || "历史收录 · 摘要待补";
  const options = Object.entries(statuses).map(([value, label]) =>
    '<option value="' + value + '"' + (value === state.status ? ' selected' : '') + '>' + label + '</option>'
  ).join("");

  return '<article class="paper-card">'
    + '<div class="paper-top"><span class="paper-id">arXiv ' + escapeHTML(paper.id) + published + '</span>'
    + '<button type="button" class="bookmark-btn" data-save="' + escapeHTML(paper.id) + '" aria-label="收藏" aria-pressed="' + state.starred + '">'
    + (state.starred ? "★" : "☆") + '</button></div>'
    + '<h3><a href="' + detail + '">' + escapeHTML(paper.title) + '</a></h3>'
    + '<p class="paper-blurb">' + escapeHTML(summary) + '</p>'
    + tagsHTML(paper.tags)
    + '<div class="paper-foot"><span>收录 ' + escapeHTML(paper.first_seen) + '</span><div class="paper-links">'
    + '<button type="button" data-ai="' + escapeHTML(paper.id) + '">复制 AI 解读问题</button></div></div>'
    + '<div class="paper-state"><label>研究状态 <select data-status="' + escapeHTML(paper.id) + '">' + options + '</select></label></div></article>';
}

function renderCards(container, rows, emptyMessage) {
  const saved = ResearchStore.read().papers;
  $(container).innerHTML = rows.length ? rows.map(paper => paperCard(paper, saved)).join("")
    : '<p class="empty-state">' + emptyMessage + '</p>';
}

function route() {
  const hash = location.hash.slice(1);
  const next = routes.includes(hash) ? hash : "today";
  document.querySelectorAll(".hub-view").forEach(section => { section.hidden = section.id !== next; });
  document.querySelectorAll("[data-route]").forEach(link => {
    if (link.dataset.route === next) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  if (currentRoute && currentRoute !== next) {
    window.scrollTo(0, 0);
    $("#" + next + " h1").focus({ preventScroll: true });
  }
  currentRoute = next;
}

function renderToday() {
  const digest = digests[0];
  $("#count").textContent = digests.length;
  $("#paper-count").textContent = papers.length;
  $("#featured").innerHTML = digest
    ? '<div class="brief-meta"><time datetime="' + escapeHTML(digest.date) + '">' + escapeHTML(digest.date) + '</time>'
      + '<span>' + escapeHTML(digest.kind || "研究日报") + '</span></div>'
      + '<h2>' + escapeHTML(digest.title) + '</h2><p>' + escapeHTML(digest.summary) + '</p>'
      + tagsHTML(digest.tags)
      + '<a class="btn brief-cta" href="' + encodeURI(digest.url) + '">阅读完整日报 ↗</a>'
    : "暂无日报";
  $("#highlights").innerHTML = (digest?.highlights?.length ? digest.highlights : ["暂无本期要点"])
    .slice(0, 5).map(item => '<li>' + escapeHTML(item) + '</li>').join("");
  const latest = papers.filter(paper => paper.digests.includes(digest?.date)).slice(0, 6);
  renderCards("#today-papers", latest, "暂无本期论文。");
}

function matchesPaper(paper, query) {
  return [paper.id, paper.title, paper.abstract, ...(paper.tags || [])].join(" ").toLowerCase().includes(query);
}

function renderPapers() {
  const query = $("#paper-search").value.trim().toLowerCase();
  const topic = $("#paper-topic").value;
  const order = $("#paper-order").value;
  const rows = papers.filter(paper => (!topic || paper.tags?.includes(topic)) && matchesPaper(paper, query));
  if (order === "title") rows.sort((a, b) => a.title.localeCompare(b.title));
  if (order === "published") rows.sort((a, b) => (b.published || "").localeCompare(a.published || ""));
  $("#paper-results-count").textContent = rows.length + " / " + papers.length + " 篇论文";
  renderCards("#paper-results", rows, "没有找到符合条件的论文。");
}

function renderFavorites() {
  const saved = ResearchStore.read().papers;
  const entries = papers.filter(paper => saved[paper.id]?.starred);
  const query = $("#favorite-search").value.trim().toLowerCase();
  const status = $("#favorite-status").value;
  const rows = entries.filter(paper => (!status || saved[paper.id].status === status) && matchesPaper(paper, query));
  $("#saved-count").textContent = entries.length || "";
  $("#favorite-results-count").textContent = "已收藏 " + entries.length + " 篇 · 当前显示 " + rows.length + " 篇";
  renderCards("#favorite-results", rows, entries.length
    ? "没有符合筛选条件的收藏。" : "在日报或论文库中点击 ☆ 收藏论文。");
}

function renderArchive() {
  const query = $("#search").value.trim().toLowerCase();
  const topic = $("#topic").value;
  const rows = digests.filter(digest => {
    const text = [digest.date, digest.title, digest.summary, ...(digest.tags || []), ...(digest.highlights || [])];
    return (!topic || digest.tags?.includes(topic)) && text.join(" ").toLowerCase().includes(query);
  });
  $("#resultcount").textContent = "共 " + rows.length + " 期日报";
  $("#results").innerHTML = rows.length ? rows.map(digest =>
    '<article class="issue-card"><div class="issue-meta">' + escapeHTML(digest.date) + " · " + escapeHTML(digest.kind || "")
    + '</div><h3><a href="' + encodeURI(digest.url) + '">' + escapeHTML(digest.title) + '</a></h3><p>'
    + escapeHTML(digest.summary) + '</p>' + tagsHTML(digest.tags) + '</article>'
  ).join("") : '<p class="empty-state">没有符合条件的日报。</p>';
}

function refreshResearchState() {
  const saved = ResearchStore.read().papers;
  document.querySelectorAll("[data-save]").forEach(button => {
    const starred = saved[button.dataset.save]?.starred === true;
    button.setAttribute("aria-pressed", starred);
    button.textContent = starred ? "★" : "☆";
  });
  document.querySelectorAll("[data-status]").forEach(select => {
    select.value = saved[select.dataset.status]?.status || "unread";
  });
  const active = document.activeElement;
  const activeField = active.closest("#favorite-results") && (
    active.dataset.save ? "save" : active.dataset.status ? "status" : null
  );
  renderFavorites();
  if (activeField) {
    const replacement = $("#favorite-results [data-" + activeField + '="' + active.dataset[activeField] + '"]');
    (replacement || $("#favorite-search")).focus({ preventScroll: true });
  }
}

document.addEventListener("click", async event => {
  const save = event.target.closest("[data-save]");
  if (save) {
    const id = save.dataset.save;
    ResearchStore.set(id, { starred: !ResearchStore.get(id).starred });
    return;
  }
  const ai = event.target.closest("[data-ai]");
  if (!ai) return;
  const paper = byId.get(ai.dataset.ai);
  if (!paper) return;
  const copied = await ResearchStore.copyPrompt(paper);
  ai.textContent = copied ? "已复制" : "复制失败，重试";
  if (copied && !ai.nextElementSibling?.classList.contains("open-ai-link")) {
    const link = document.createElement("a");
    link.className = "open-ai-link";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.href = "https://chatgpt.com/";
    link.textContent = "打开 ChatGPT ↗";
    ai.after(link);
  }
});

document.addEventListener("change", event => {
  const select = event.target.closest("[data-status]");
  if (select) ResearchStore.set(select.dataset.status, { status: select.value });
});
window.addEventListener("research-state-change", refreshResearchState);
window.addEventListener("hashchange", route);
document.querySelectorAll(".hub-view h1").forEach(heading => { heading.tabIndex = -1; });
route();

function setTopics(selector, entries) {
  const tags = [...new Set(entries.flatMap(entry => entry.tags || []))].sort((a, b) => a.localeCompare(b, "zh"));
  $(selector).append(...tags.map(tag => new Option(tag)));
}

$("#paper-search").addEventListener("input", renderPapers);
$("#paper-topic").addEventListener("change", renderPapers);
$("#paper-order").addEventListener("change", renderPapers);
$("#favorite-search").addEventListener("input", renderFavorites);
$("#favorite-status").addEventListener("change", renderFavorites);
$("#search").addEventListener("input", renderArchive);
$("#topic").addEventListener("change", renderArchive);
$("#export-favorites").addEventListener("click", () => ResearchStore.exportData());
$("#import-favorites").addEventListener("click", () => $("#import-file").click());
$("#import-file").addEventListener("change", async event => {
  const message = $("#backup-message");
  try {
    const count = await ResearchStore.importData(event.target.files[0]);
    message.textContent = "已导入 " + count + " 条记录。";
  } catch (error) {
    message.textContent = "导入失败：" + error.message;
  } finally {
    event.target.value = "";
  }
});

async function loadIndexes() {
  try {
    const responses = await Promise.all(["index.json", "papers.json"].map(url => fetch(url, { cache: "no-store" })));
    if (responses.some(response => !response.ok)) throw Error("索引请求失败");
    const [issueData, paperData] = await Promise.all(responses.map(response => response.json()));
    if (!Array.isArray(issueData) || !Array.isArray(paperData)) throw Error("索引数据类型错误");
    digests = issueData.sort((a, b) => b.date.localeCompare(a.date));
    papers = paperData;
    byId = new Map(papers.map(paper => [paper.id, paper]));
    setTopics("#paper-topic", papers);
    setTopics("#topic", digests);
    renderToday();
    renderPapers();
    renderFavorites();
    renderArchive();
  } catch (error) {
    $("#load-error").hidden = false;
    $("#featured").textContent = "暂时无法读取最新一期。";
    console.error(error);
  }
}

loadIndexes();
