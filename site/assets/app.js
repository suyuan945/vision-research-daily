const $=q=>document.querySelector(q);
const escapeHTML=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const tagsHTML=v=>'<div class="tag-list">'+(v||[]).slice(0,5).map(t=>'<span class="tag">'+escapeHTML(t)+'</span>').join("")+"</div>";
let digests=[],papers=[],byId=new Map();
function paperCard(p){
 const state=ResearchStore.get(p.id),star=state.starred,detail="papers/"+encodeURIComponent(p.id)+".html";
 const blurb=p.abstract||"历史日报中收录的论文，尚未导入完整摘要。点击标题查看 arXiv 链接和收录日期。";
 return '<article class="paper-card"><div class="paper-top"><span class="paper-id">arXiv '+escapeHTML(p.id)+'</span><button type="button" class="bookmark-btn" data-save="'+escapeHTML(p.id)+'" aria-label="'+(star?"取消收藏":"收藏")+'" aria-pressed="'+star+'">'+(star?"★":"☆")+'</button></div>'
 +'<h3><a href="'+detail+'">'+escapeHTML(p.title)+'</a></h3><p class="paper-blurb">'+escapeHTML(blurb)+'</p>'
 +tagsHTML(p.tags)+'<div class="paper-foot"><span>收录 '+escapeHTML(p.first_seen)+'</span>'
 +'<div class="paper-links"><a href="'+detail+'">详情 ↗</a><button type="button" data-ai="'+escapeHTML(p.id)+'">✦ AI解读</button></div></div>'
 +'<div class="paper-state"><label>研究状态 <select data-status="'+escapeHTML(p.id)+'"><option value="unread"'+(state.status==="unread"?" selected":"")+'>待读</option><option value="reading"'+(state.status==="reading"?" selected":"")+'>精读中</option><option value="reproduce"'+(state.status==="reproduce"?" selected":"")+'>待复现</option><option value="done"'+(state.status==="done"?" selected":"")+'>已完成</option></select></label></div></article>';
}
function route(){
 const name=location.hash.slice(1),valid=["today","papers","favorites","archive"];
 const current=valid.includes(name)?name:"today";
 document.querySelectorAll(".hub-view").forEach(section=>{section.hidden=section.id!==current});
 document.querySelectorAll("[data-route]").forEach(a=>a.classList.toggle("active",a.dataset.route===current));
 if(current==="favorites")renderFavorites();
 if(current==="papers")renderPapers();
 if(current==="archive")renderArchive();
}
function renderToday(){
 const d=digests[0];$("#count").textContent=digests.length;$("#paper-count").textContent=papers.length;
 $("#latest-date").textContent=d?.date||"—";
 $("#featured").innerHTML=d?'<small>'+escapeHTML(d.date)+" · "+escapeHTML(d.kind||"研究日报")+'</small><h3>'+escapeHTML(d.title)+'</h3><p>'+escapeHTML(d.summary)+'</p>'+tagsHTML(d.tags)+'<p style="margin:24px 0 0"><a class="btn" href="'+encodeURI(d.url)+'">阅读今日完整日报 ↗</a></p>':"暂无日报";
 const todays=papers.filter(p=>p.digests.includes(d?.date)).slice(0,6);
 $("#today-papers").innerHTML=todays.length?todays.map(paperCard).join(""):'<p class="empty-state">本期尚未解析出独立的 arXiv 论文链接。可阅读完整日报。</p>';
}
function renderPapers(){
 const q=$("#paper-search").value.trim().toLowerCase(),topic=$("#paper-topic").value,order=$("#paper-order").value;
 let rows=papers.filter(p=>(!topic||(p.tags||[]).includes(topic))&&(!q||[p.id,p.title,p.abstract,...(p.tags||[])].join(" ").toLowerCase().includes(q)));
 if(order==="title")rows.sort((a,b)=>a.title.localeCompare(b.title));
 $("#paper-results-count").textContent="找到 "+rows.length+" 篇论文 · 按 arXiv ID 去重";
 $("#paper-results").innerHTML=rows.length?rows.map(paperCard).join(""):'<p class="empty-state">没有找到符合条件的论文。</p>';
}
function renderFavorites(){
 const entries=papers.filter(p=>ResearchStore.get(p.id).starred);
 const q=$("#favorite-search").value.trim().toLowerCase(),status=$("#favorite-status").value;
 const rows=entries.filter(p=>(!status||ResearchStore.get(p.id).status===status)&&(!q||[p.title,p.id,p.abstract,...(p.tags||[])].join(" ").toLowerCase().includes(q)));
 $("#saved-count").textContent=entries.length?"("+entries.length+")":"";
 $("#favorite-results-count").textContent="已收藏 "+entries.length+" 篇 · 当前显示 "+rows.length+" 篇";
 $("#favorite-results").innerHTML=rows.length?rows.map(paperCard).join(""):'<div class="empty-state">暂时没有匹配的收藏。从“今日”或“论文库”点击 ☆ 收藏喜欢的论文。</div>';
}
function renderArchive(){
 const q=$("#search").value.trim().toLowerCase(),tag=$("#topic").value;
 const rows=digests.filter(d=>(!tag||(d.tags||[]).includes(tag))&&(!q||[d.date,d.title,d.summary,...(d.tags||[]),...(d.highlights||[])].join(" ").toLowerCase().includes(q)));
 $("#resultcount").textContent="共 "+rows.length+" 期日报";
 $("#results").innerHTML=rows.length?rows.map(d=>'<article class="issue-card"><div class="issue-meta">'+escapeHTML(d.date)+" · "+escapeHTML(d.kind||"")+'</div><h3>'+escapeHTML(d.title)+'</h3><p>'+escapeHTML(d.summary)+'</p>'+tagsHTML(d.tags)+'<a class="read-link" href="'+encodeURI(d.url)+'">阅读全文 ↗</a></article>').join(""):'<div class="empty-state">没有符合条件的日报。</div>';
}
document.addEventListener("click",async event=>{
 const save=event.target.closest("[data-save]");
 if(save){const id=save.dataset.save,s=ResearchStore.get(id);ResearchStore.set(id,{starred:!s.starred});return}
 const ai=event.target.closest("[data-ai]");
 if(ai){const p=byId.get(ai.dataset.ai);if(!p)return;const ok=await ResearchStore.copyPrompt(p);ai.textContent=ok?"✓ 已复制":"复制失败";if(ok){let node=ai.nextElementSibling;if(!node||!node.classList.contains("open-ai-link")){const link=document.createElement("a");link.className="open-ai-link";link.target="_blank";link.rel="noopener noreferrer";link.href="https://chatgpt.com/";link.textContent="打开ChatGPT ↗";ai.after(link)}}return}
});
document.addEventListener("change",event=>{const select=event.target.closest("[data-status]");if(select)ResearchStore.set(select.dataset.status,{status:select.value})});
window.addEventListener("research-state-change",()=>{renderToday();renderPapers();renderFavorites()});
(async()=>{
 try{
  const [a,b]=await Promise.all([fetch("index.json",{cache:"no-store"}),fetch("papers.json",{cache:"no-store"})]);
  if(!a.ok||!b.ok)throw Error("索引请求失败");
  digests=await a.json();papers=await b.json();if(!Array.isArray(digests)||!Array.isArray(papers))throw Error("数据类型错误");
  digests.sort((x,y)=>y.date.localeCompare(x.date));byId=new Map(papers.map(p=>[p.id,p]));
  const topics=[...new Set(papers.flatMap(p=>p.tags||[]))].sort((a,b)=>a.localeCompare(b,"zh"));
  $("#paper-topic").innerHTML='<option value="">全部方向</option>'+topics.map(t=>'<option>'+escapeHTML(t)+'</option>').join("");
  const digestTopics=[...new Set(digests.flatMap(d=>d.tags||[]))].sort((a,b)=>a.localeCompare(b,"zh"));
  $("#topic").innerHTML='<option value="">所有方向</option>'+digestTopics.map(t=>'<option>'+escapeHTML(t)+'</option>').join("");
  renderToday();renderPapers();renderFavorites();renderArchive();
 }catch(error){$("#featured").textContent="数据加载失败，请刷新页面或查看 GitHub Actions 构建记录。";console.error(error)}
 ["paper-search","paper-topic","paper-order"].forEach(id=>$("#"+id).addEventListener(id==="paper-search"?"input":"change",renderPapers));
 ["favorite-search","favorite-status"].forEach(id=>$("#"+id).addEventListener(id==="favorite-search"?"input":"change",renderFavorites));
 ["search","topic"].forEach(id=>$("#"+id).addEventListener(id==="search"?"input":"change",renderArchive));
 $("#export-favorites").addEventListener("click",()=>ResearchStore.exportData());
 $("#import-file").addEventListener("change",async e=>{
  const msg=$("#backup-message");
  try{const n=await ResearchStore.importData(e.target.files[0]);msg.textContent="已导入 "+n+" 条记录（相同论文将采用导入文件中的状态）";renderFavorites()}
  catch(error){msg.textContent="导入失败："+error.message}finally{e.target.value=""}
 });
 window.addEventListener("hashchange",route);route();
})();
