const $ = selector => document.querySelector(selector);
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, char => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[char]));
const tagsHTML = (tags = []) => '<div class="tag-list">'
  + tags.slice(0, 5).map(tag => '<span class="tag">' + escapeHTML(tag) + '</span>').join("")
  + '</div>';

const statuses = { unread: "待读", reading: "精读中", reproduce: "待复现", done: "已完成" };
const routes = ["today", "papers", "opensource", "articles", "favorites", "archive"];
const eventLabels = { new: "新仓库", release: "版本发布", discovered: "首次收录" };
let digests = [];
let papers = [];
let byId = new Map();
let githubFeed = [];
let articles = [];
let githubUnavailable = false;
let articlesUnavailable = false;
let currentRoute;
let paperChecks = [];
let paperDay;
let calendarMonth;
let paperGroupLimit = 8;
const issueByDate = new Map();
const checkByDate = new Map();

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
  const [hash, params] = location.hash.slice(1).split("?");
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
  if (next === "papers" && paperDay) {
    const day = new URLSearchParams(params).get("date");
    if (day && validPaperDate(day) && day !== paperDay) {
      selectPaperDay(day, false);
    }
  }
}

function renderToday() {
  const digest = digests[0];
  const date = $("#edition-date");
  date.textContent = digest?.date || "";
  date.dateTime = digest?.date || "";
  $("#featured").innerHTML = digest
    ? '<div class="brief-meta">最新一期</div>'
      + '<h2>' + escapeHTML(digest.title) + '</h2><p>' + escapeHTML(digest.summary) + '</p>'
      + '<div class="brief-footer">' + tagsHTML(digest.tags)
      + '<a class="section-link" href="' + encodeURI(digest.url) + '">阅读完整日报 ↗</a></div>'
    : "暂无日报";
  const latest = digest?.paper_ids?.length ? digest.paper_ids.map(id => byId.get(id)).filter(Boolean)
    : papers.filter(paper => paper.digests.includes(digest?.date));
  renderCards("#today-papers", latest.slice(0, 6), "暂无本期论文。");
}

function matchesPaper(paper, query) {
  return [paper.id, paper.title, paper.abstract, ...(paper.tags || []), ...(paper.aliases || [])]
    .join(" ").toLowerCase().includes(query);
}

function validPaperDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value > chinaDate(Date.now())) return false;
  const parsed = new Date(value + "T00:00:00Z");
  return !Number.isNaN(parsed.valueOf()) && parsed.toISOString().slice(0, 10) === value
    && value >= (digests.at(-1)?.date || value);
}

function paperDateLabel(day) {
  const [year, month, date] = day.split("-").map(Number);
  return year + "年" + month + "月" + date + "日";
}

function paperDayRows(day) {
  const preferred = issueByDate.get(day)?.paper_ids || [];
  const matched = papers.filter(paper => paper.digests.includes(day));
  if (!preferred.length) return matched;
  const order = new Map(preferred.map((id, index) => [id, index]));
  return matched.sort((a, b) => (order.get(a.id) ?? Infinity) - (order.get(b.id) ?? Infinity) || 0);
}

function selectPaperDay(day, updateUrl = true) {
  paperDay = day;
  calendarMonth = day.slice(0, 7);
  $('input[name="paper-scope"][value="day"]').checked = true;
  if (updateUrl) history.replaceState(null, "", "#papers?date=" + day);
  renderPaperCalendar();
  renderPapers();
}

function monthShift(offset) {
  const [year, month] = calendarMonth.split("-").map(Number);
  calendarMonth = new Date(Date.UTC(year, month - 1 + offset, 1)).toISOString().slice(0, 7);
  renderPaperCalendar();
}

function renderPaperCalendar() {
  if (!calendarMonth) return;
  const [year, month] = calendarMonth.split("-").map(Number);
  const offset = (new Date(Date.UTC(year, month - 1, 1)).getUTCDay() + 6) % 7;
  const days = new Date(Date.UTC(year, month, 0)).getUTCDate();
  const today = chinaDate(Date.now());
  $("#paper-month").textContent = year + "年" + month + "月";
  $("#paper-next-month").disabled = calendarMonth >= today.slice(0, 7);
  const oldest = (digests.at(-1)?.date || today).slice(0, 7);
  $("#paper-prev-month").disabled = calendarMonth <= oldest;
  $("#paper-calendar-days").innerHTML = '<span aria-hidden="true"></span>'.repeat(offset)
    + Array.from({ length: days }, (_, index) => {
      const number = index + 1;
      const date = calendarMonth + "-" + String(number).padStart(2, "0");
      const state = issueByDate.has(date) ? "issue" : checkByDate.get(date)?.status || "";
      const label = ({ issue: "有日报", no_new: "已检查，无新收录", failed: "采集失败" })[state] || "无归档";
      return '<button type="button" data-paper-day="' + date + '" data-state="' + state
        + '" aria-label="' + paperDateLabel(date) + "，" + label + '" aria-pressed="' + (date === paperDay) + '"'
        + (date === today ? ' aria-current="date"' : '') + (date > today ? ' disabled' : '') + '>'
        + number + '</button>';
    }).join("");
}

function archivePaperRow(paper, saved, showReceived) {
  const state = saved[paper.id] || { starred: false, status: "unread" };
  const detail = "papers/" + encodeURIComponent(paper.id) + ".html";
  const published = paper.published ? "arXiv 提交 " + escapeHTML(paper.published.slice(0, 10)) + " UTC" : "提交日期待核实";
  return '<article class="archive-paper">'
    + '<div class="archive-paper-meta"><span>' + published + '</span>'
    + (showReceived ? '<span>首次收录 ' + escapeHTML(paper.first_seen) + '</span>' : '') + '</div>'
    + '<h3><a href="' + detail + '">' + escapeHTML(paper.title) + '</a></h3>'
    + (paper.abstract ? '<p class="paper-blurb">' + escapeHTML(paper.abstract) + '</p>' : '')
    + '<div class="archive-paper-foot">' + tagsHTML(paper.tags.slice(0, 3))
    + '<div class="paper-links"><a href="https://arxiv.org/abs/' + encodeURIComponent(paper.id) + '">arXiv ↗</a>'
    + '<button type="button" data-ai="' + escapeHTML(paper.id) + '">复制 AI 解读问题</button></div></div>'
    + '<button type="button" class="bookmark-btn" data-save="' + escapeHTML(paper.id)
    + '" aria-label="收藏" aria-pressed="' + state.starred + '">' + (state.starred ? "★" : "☆") + '</button>'
    + (state.status === "unread" ? "" : '<span class="archive-paper-reading" data-reading="'
      + escapeHTML(paper.id) + '">' + statuses[state.status] + '</span>') + '</article>';
}

function paperDateGroup(day, rows, { issue, message, showReceived, title, caption } = {}) {
  const saved = ResearchStore.read().papers;
  return '<section class="paper-date-group"><header class="paper-day-header">'
    + '<div><h2>' + escapeHTML(title || paperDateLabel(day)) + '</h2><p>'
    + escapeHTML(caption || rows.length + " 篇论文") + '</p></div>'
    + (issue ? '<a class="section-link" href="' + encodeURI(issue.url) + '">阅读当期日报 ↗</a>' : '')
    + '</header>' + (rows.length ? rows.map(paper => archivePaperRow(paper, saved, showReceived)).join("")
      : '<p class="paper-day-empty">' + escapeHTML(message) + '</p>') + '</section>';
}

function renderPapers() {
  if (!paperDay) return;
  const scope = $('input[name="paper-scope"]:checked').value;
  const query = $("#paper-search").value.trim().toLowerCase();
  const topic = $("#paper-topic").value;
  const order = $("#paper-order").value;
  const filter = paper => (!topic || paper.tags.includes(topic)) && matchesPaper(paper, query);
  $("#paper-order").hidden = scope === "day";
  $("#paper-more").hidden = true;
  if (scope === "day") {
    const issue = issueByDate.get(paperDay);
    const all = paperDayRows(paperDay);
    const rows = all.filter(filter);
    const check = checkByDate.get(paperDay);
    const today = chinaDate(Date.now());
    const empty = all.length ? "这一天没有匹配的论文。"
      : issue ? "这期日报没有可单独收录的论文，可以查看原日报。"
        : check?.status === "no_new" ? "当天已检查，没有新论文入库。"
          : check?.status === "failed" ? "当天采集失败，尚无日报。"
            : paperDay === today ? "今天的采集尚未记录，最近一期仍可查阅。" : "这一天没有归档记录。";
    $("#paper-results-count").textContent = paperDateLabel(paperDay) + "，" + rows.length + " 篇论文";
    $("#paper-results").innerHTML = paperDateGroup(paperDay, rows, {
      issue, message: empty, showReceived: false,
      caption: issue && (query || topic) ? rows.length + " / " + all.length + " 篇论文" : undefined,
    });
    return;
  }
  const rows = papers.filter(filter);
  $("#paper-results-count").textContent = "找到 " + rows.length + " 篇论文";
  const groups = new Map();
  for (const paper of rows) {
    const date = order === "published" ? paper.published?.slice(0, 10) || "" : paper.first_seen;
    if (!groups.has(date)) groups.set(date, []);
    groups.get(date).push(paper);
  }
  const keys = [...groups.keys()].sort().reverse();
  $("#paper-more").hidden = keys.length <= paperGroupLimit;
  $("#paper-results").innerHTML = keys.length ? keys.slice(0, paperGroupLimit).map(day =>
    paperDateGroup(day, groups.get(day), {
      title: day ? undefined : "提交日期待核实",
      caption: groups.get(day).length + " 篇论文" + (day && order === "published" ? " · UTC" : ""),
      issue: order === "recent" ? issueByDate.get(day) : undefined,
      showReceived: order === "published",
    })
  ).join("") : '<p class="paper-day-empty">没有找到符合条件的论文。</p>';
}

function initializePapers() {
  digests.forEach(issue => issueByDate.set(issue.date, issue));
  paperChecks.forEach(check => checkByDate.set(check.date, check));
  const today = chinaDate(Date.now());
  const latest = digests[0]?.date;
  const first = digests.at(-1)?.date;
  $("#paper-coverage").textContent = first
    ? papers.length + " 篇论文 · " + digests.length + " 期日报 · " + first + " 至 " + latest
    : papers.length + " 篇论文";
  const check = checkByDate.get(today);
  const health = issueByDate.has(today) ? "今天已归档"
    : ({ no_new: "今日已检查 · 无新收录", failed: "今日采集失败" })[check?.status]
      || "等待今日采集";
  const time = check?.checked_at ? " · 北京时间 " + new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(new Date(check.checked_at)) : "";
  $("#paper-health").dataset.state = issueByDate.has(today) ? "published" : check?.status || "pending";
  $("#paper-health").textContent = health + time;
  const requested = new URLSearchParams(location.hash.split("?")[1]).get("date");
  const date = requested && validPaperDate(requested) ? requested : today;
  selectPaperDay(date, false);
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
  const reproduce = entries.filter(paper => saved[paper.id].status === "reproduce").slice(0, 4);
  $("#reproduce-section").hidden = !reproduce.length;
  $("#reproduce-papers").innerHTML = reproduce.map(paper =>
    compactItem("arXiv " + paper.id, paper.title, "papers/" + encodeURIComponent(paper.id) + ".html")
  ).join("");
}

function compactItem(meta, title, href) {
  return '<article class="compact-item"><p>' + escapeHTML(meta) + '</p>'
    + '<h3><a href="' + escapeHTML(href) + '">' + escapeHTML(title) + '</a></h3></article>';
}

function chinaDate(value) {
  const parts = new Intl.DateTimeFormat("en", {
    timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(value));
  const date = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return date.year + "-" + date.month + "-" + date.day;
}

function gitEventCard(event) {
  const repo = event.repo;
  const license = repo.license && repo.license !== "NOASSERTION" ? repo.license
    : repo.license_name && repo.license_name !== "Other" ? repo.license_name : "许可证待核实";
  const sources = repo.paper_ids.filter(id => byId.has(id)).slice(0, 4).map(id =>
    '<a href="papers/' + encodeURIComponent(id) + '.html">相关论文 ' + escapeHTML(id) + ' ↗</a>'
  );
  if (event.kind === "release") sources.unshift('<a href="' + escapeHTML(repo.url) + '">项目仓库 ↗</a>');
  const assets = event.weights?.length
    ? '<p class="feed-meta">疑似权重附件 · ' + escapeHTML(event.weights.join("、")) + '</p>' : "";
  return '<article class="feed-entry">'
    + '<p class="feed-meta"><strong>' + eventLabels[event.kind] + '</strong> · ' + chinaDate(event.date)
    + (event.prerelease ? " · 预发行" : "") + '</p>'
    + '<h3><a href="' + escapeHTML(event.url) + '">' + escapeHTML(repo.name)
    + (event.version ? ' <span class="version">' + escapeHTML(event.version) + '</span>' : '') + ' ↗</a></h3>'
    + (event.title !== repo.name && event.title !== event.version ? '<p>' + escapeHTML(event.title) + '</p>' : '')
    + (repo.description ? '<p>' + escapeHTML(repo.description) + '</p>' : '')
    + tagsHTML(repo.topics)
    + '<p class="feed-meta">' + escapeHTML(license) + ' · 仓库创建 ' + chinaDate(repo.created_at)
    + ' · 首次收录 ' + escapeHTML(event.first_seen) + '</p>'
    + assets + (sources.length ? '<div class="feed-links">' + sources.join("") + '</div>' : '')
    + '</article>';
}

function renderGithub() {
  const query = $("#github-search").value.trim().toLowerCase();
  const topic = $("#github-topic").value;
  const kind = $("#github-kind").value;
  const rows = githubFeed.filter(event => {
    const searchable = [event.repo.name, event.repo.description, event.title, event.version, ...event.repo.topics];
    return (!topic || event.repo.topics.includes(topic)) && (!kind || event.kind === kind)
      && searchable.join(" ").toLowerCase().includes(query);
  });
  $("#github-count").textContent = githubUnavailable ? "" : rows.length + " 条动态";
  $("#github-results").innerHTML = rows.length ? rows.map(gitEventCard).join("")
    : '<p class="empty-state">' + (githubUnavailable ? "暂时无法读取 GitHub 动态。" : "没有符合条件的 GitHub 动态。") + '</p>';
}

function renderArticles() {
  const query = $("#article-search").value.trim().toLowerCase();
  const account = $("#article-account").value;
  const rows = articles.filter(article => (!account || article.account === account)
    && [article.title, article.account, article.summary, ...(article.tags || [])].join(" ").toLowerCase().includes(query));
  $("#article-count").textContent = articlesUnavailable ? "" : rows.length + " 篇文章";
  $("#article-results").innerHTML = rows.length ? rows.map(article =>
    '<article class="feed-entry"><p class="feed-meta">' + escapeHTML(article.account) + ' · ' + escapeHTML(article.date) + '</p>'
    + '<h3><a href="' + escapeHTML(article.url) + '">' + escapeHTML(article.title) + ' ↗</a></h3>'
    + (article.summary ? '<p>' + escapeHTML(article.summary) + '</p>' : '') + tagsHTML(article.tags)
    + '</article>'
  ).join("") : '<p class="empty-state">' + (articlesUnavailable ? "暂时无法读取文章。"
    : articles.length ? "没有符合条件的文章。" : "尚未收录公众号文章。") + '</p>';
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
    + escapeHTML(digest.summary) + '</p>' + tagsHTML(digest.tags)
    + '<a class="issue-papers-link section-link" href="#papers?date=' + escapeHTML(digest.date) + '">查看本期论文 ↗</a></article>'
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

function applyPaperFilters() {
  paperGroupLimit = 8;
  renderPapers();
}

$("#paper-search").addEventListener("input", () => {
  if ($("#paper-search").value.trim() && $('input[name="paper-scope"][value="day"]').checked) {
    $('input[name="paper-scope"][value="all"]').checked = true;
    history.replaceState(null, "", "#papers");
  }
  applyPaperFilters();
});
$("#paper-topic").addEventListener("change", applyPaperFilters);
$("#paper-order").addEventListener("change", applyPaperFilters);
document.querySelectorAll('input[name="paper-scope"]').forEach(input => input.addEventListener("change", () => {
  history.replaceState(null, "", input.value === "day" ? "#papers?date=" + paperDay : "#papers");
  applyPaperFilters();
}));
$("#paper-prev-month").addEventListener("click", () => monthShift(-1));
$("#paper-next-month").addEventListener("click", () => monthShift(1));
$("#paper-today").addEventListener("click", () => selectPaperDay(chinaDate(Date.now())));
$("#paper-latest").addEventListener("click", () => selectPaperDay(digests[0]?.date || chinaDate(Date.now())));
$("#paper-calendar-days").addEventListener("click", event => {
  const button = event.target.closest("[data-paper-day]");
  if (!button) return;
  selectPaperDay(button.dataset.paperDay);
  $("#paper-calendar-days [aria-pressed=true]").focus();
});
$("#paper-more").addEventListener("click", () => {
  paperGroupLimit += 8;
  renderPapers();
});
$("#github-search").addEventListener("input", renderGithub);
$("#github-topic").addEventListener("change", renderGithub);
$("#github-kind").addEventListener("change", renderGithub);
$("#article-search").addEventListener("input", renderArticles);
$("#article-account").addEventListener("change", renderArticles);
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
    const [issueData, paperData, checks] = await Promise.all([
      ...responses.map(response => response.json()),
      readIndex("paper-checks.json").catch(() => []),
    ]);
    if (!Array.isArray(issueData) || !Array.isArray(paperData)) throw Error("索引数据类型错误");
    digests = issueData.sort((a, b) => b.date.localeCompare(a.date));
    papers = paperData;
    paperChecks = Array.isArray(checks) ? checks : [];
    byId = new Map(papers.map(paper => [paper.id, paper]));
    setTopics("#paper-topic", papers);
    setTopics("#topic", digests);
    renderToday();
    initializePapers();
    renderFavorites();
    renderArchive();
  } catch (error) {
    $("#load-error").hidden = false;
    $("#featured").textContent = "暂时无法读取最新一期。";
    console.error(error);
  }
}

async function readIndex(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw Error("索引请求失败");
  return response.json();
}

async function loadGithub(indexes) {
  try {
    const archive = await readIndex("github.json");
    const repos = new Map(archive.repositories.map(repo => [repo.id, repo]));
    githubFeed = archive.events.filter(event => repos.has(event.repository_id) && eventLabels[event.kind])
      .map(event => ({ ...event, repo: repos.get(event.repository_id) }));
    setTopics("#github-topic", archive.repositories.map(repo => ({ tags: repo.topics })));
    const latest = githubFeed.filter(event => event.kind !== "discovered").slice(0, 4);
    const rows = latest.length ? latest : githubFeed.slice(0, 4);
    $("#latest-github").innerHTML = rows.length ? rows.map(event => compactItem(
      eventLabels[event.kind] + " · " + chinaDate(event.date),
      event.repo.name + (event.version ? " · " + event.version : ""),
      event.url
    )).join("") : '<p class="muted">暂时没有收录的动态。</p>';
    const checked = archive.checked_at ? " · 最近检查 " + chinaDate(archive.checked_at) : "";
    $("#github-status").textContent = (({ ok: "采集正常", partial: "部分来源读取失败，保留历史记录",
      failed: "本次采集失败，保留历史记录" })[archive.status] || "等待首次采集") + checked;
  } catch {
    githubUnavailable = true;
    $("#github-status").textContent = "暂时无法读取采集状态。";
    $("#latest-github").textContent = "暂时无法读取 GitHub 动态。";
  }
  await indexes;
  renderGithub();
}

async function loadArticles() {
  try {
    const archive = await readIndex("articles.json");
    articles = archive.articles;
    const accounts = Object.keys(archive.sources).sort((a, b) => a.localeCompare(b, "zh"));
    const sourceLabels = { ok: "自动追踪", failed: "读取失败", stale: "订阅源近期未更新", pending: "等待验证", manual: "链接收录" };
    $("#article-sources").innerHTML = accounts.map(account => {
      const source = archive.sources[account];
      return '<li><strong>' + escapeHTML(account) + '</strong> · ' + sourceLabels[source.state]
        + (source.newest ? ' · 来源最新 ' + escapeHTML(source.newest) : '') + '</li>';
    }).join("");
    $("#article-account").append(...accounts.map(account => new Option(account)));
    $("#reading-section").hidden = !articles.length;
    $("#latest-articles").innerHTML = articles.slice(0, 4).map(article =>
      compactItem(article.account + " · " + article.date, article.title, article.url)
    ).join("");
  } catch {
    articlesUnavailable = true;
  }
  renderArticles();
}

loadGithub(loadIndexes());
loadArticles();
