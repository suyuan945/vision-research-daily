const $=s=>document.querySelector(s);
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const cardTags=tags=>'<div class="tag-list">'+(tags||[]).slice(0,5).map(t=>'<span class="tag">'+escapeHTML(t)+'</span>').join('')+'</div>';
(async()=>{
 let docs=[];
 try{const response=await fetch('index.json',{cache:'no-store'});if(!response.ok)throw Error('Cannot load index');docs=await response.json();if(!Array.isArray(docs))throw Error('Invalid data')}
 catch(e){$('#featured').textContent='暂时无法读取文章';$('#results').textContent='归档索引加载失败，请稍后刷新';return;}
 docs.sort((a,b)=>b.date.localeCompare(a.date));$('#count').textContent=String(docs.length);$('#latest-date').textContent=docs[0]?.date||'—';
 const topics=[...new Set(docs.flatMap(d=>d.tags||[]))].sort((a,b)=>a.localeCompare(b,'zh'));
 $('#topic').innerHTML='<option value="">所有研究方向</option>'+topics.map(t=>'<option value="'+escapeHTML(t)+'">'+escapeHTML(t)+'</option>').join('');
 if(docs.length){const d=docs[0];$('#featured').innerHTML='<small>'+escapeHTML(d.date)+' · '+escapeHTML(d.kind||'技术日报')+'</small><h3>'+escapeHTML(d.title)+'</h3><p>'+escapeHTML(d.summary)+'</p>'+cardTags(d.tags)+'<p style="margin:25px 0 0"><a class="btn" href="'+encodeURI(d.url)+'">阅读本期完整内容 <span aria-hidden="true">↗</span></a></p>'}
 else $('#featured').textContent='尚无文章。';
 const render=()=>{
  const q=$('#search').value.trim().toLocaleLowerCase(),topic=$('#topic').value;
  const list=docs.filter(d=>(!topic||(d.tags||[]).includes(topic))&&(!q||[d.date,d.title,d.summary,...(d.tags||[]),...(d.highlights||[])].join(' ').toLocaleLowerCase().includes(q)));
  $('#resultcount').textContent='共 '+list.length+' 期日报'+(q||topic?' · 已筛选':'');
  $('#results').innerHTML=list.length?list.map(d=>'<article class="issue-card"><div class="issue-meta">'+escapeHTML(d.date)+' <span aria-hidden="true">·</span> '+escapeHTML(d.kind||'技术日报')+'</div><h3>'+escapeHTML(d.title)+'</h3><p>'+escapeHTML(d.summary)+'</p>'+cardTags(d.tags)+'<a class="read-link" href="'+encodeURI(d.url)+'">阅读全文 ↗</a></article>').join(''):'<div class="empty-state">没有匹配的日报，试试其他关键词或研究方向。</div>';
 };
 $('#search').addEventListener('input',render);$('#topic').addEventListener('change',render);render();
})();