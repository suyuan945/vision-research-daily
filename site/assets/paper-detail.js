document.addEventListener("DOMContentLoaded",async()=>{
 const root=document.querySelector(".paper-detail");
 if(!root||!window.ResearchStore)return;
 const id=root.dataset.paperId;
 const show=()=>{const s=ResearchStore.get(id);const button=root.querySelector(".save-paper");if(button){button.textContent=s.starred?"★ 已收藏":"☆ 收藏论文";button.setAttribute("aria-pressed",String(s.starred))}const select=root.querySelector(".paper-status");if(select)select.value=s.status};
 root.querySelector(".save-paper")?.addEventListener("click",()=>{const s=ResearchStore.get(id);ResearchStore.set(id,{starred:!s.starred});show()});
 root.querySelector(".paper-status")?.addEventListener("change",event=>ResearchStore.set(id,{status:event.target.value}));
 root.querySelector(".ai-paper")?.addEventListener("click",async event=>{
  const button=event.currentTarget;const paper={id,title:root.querySelector("h1")?.textContent||id,url:"https://arxiv.org/abs/"+id,tags:[...root.querySelectorAll(".tag")].map(t=>t.textContent),first_seen:root.querySelector(".article-intro")?.textContent};
  const ok=await ResearchStore.copyPrompt(paper);
  button.textContent=ok?"✓ 已复制，可粘贴至 ChatGPT":"复制失败，请检查浏览器权限";
  if(ok){const anchor=document.createElement("a");anchor.href="https://chatgpt.com/";anchor.target="_blank";anchor.rel="noopener noreferrer";anchor.className="outline-btn";anchor.textContent="打开 ChatGPT ↗";button.after(anchor)}
 });
 show();window.addEventListener("research-state-change",show);
});