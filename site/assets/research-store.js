/* Local-only, versioned research state. No secrets or private data sent to GitHub. */
(function(){
 const KEY="vision-research-v2";
 function empty(){return {version:2,papers:{}}}
 function sanitize(raw){
  const state=empty(); if(!raw||typeof raw!=="object")return state;
  const rows=raw.papers&&typeof raw.papers==="object"?raw.papers:{};
  for(const [id,item] of Object.entries(rows)){
   if(!/^\d{4}\.\d{4,5}$/.test(id)||!item||typeof item!=="object")continue;
   const status=["unread","reading","reproduce","done"].includes(item.status)?item.status:"unread";
   const starred=item.starred===true;
   const note=typeof item.note==="string"?item.note.slice(0,5000):"";
   if(starred||status!=="unread"||note)state.papers[id]={starred,status,note};
  }
  return state;
 }
 function read(){try{return sanitize(JSON.parse(localStorage.getItem(KEY)||"{}"))}catch{return empty()}}
 function save(v){localStorage.setItem(KEY,JSON.stringify(sanitize(v)));window.dispatchEvent(new Event("research-state-change"))}
 function get(id){return read().papers[id]||{starred:false,status:"unread",note:""}}
 function set(id,fields){if(!/^\d{4}\.\d{4,5}$/.test(id))return;const data=read();data.papers[id]={...get(id),...fields};save(data)}
 function exportData(){const file=new Blob([JSON.stringify({...read(),exported_at:new Date().toISOString()},null,2)],{type:"application/json"});const url=URL.createObjectURL(file);const a=document.createElement("a");a.href=url;a.download="vision-research-favorites.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 async function importData(file){if(!file||file.size>1024*1024)throw Error("备份文件不可超过1MB");const raw=JSON.parse(await file.text());if(raw.version!==2||!raw.papers||typeof raw.papers!=="object")throw Error("不是有效的V2收藏备份");const source=sanitize(raw);const target=read();target.papers={...target.papers,...source.papers};save(target);return Object.keys(source.papers).length}
 function aiPrompt(paper){
  return "请深入解读以下研究论文（不要仅凭标题猜测内容，如有必要先阅读论文原文）：\n"
  +"标题："+paper.title+"\narXiv："+paper.url+"\n"
  +"目前归档日期："+(paper.first_seen||"未知")+"\n技术标签："+(paper.tags||[]).join("、")+"\n\n"
  +"请按以下顺序分析：\n1. 任务定义、输入输出与方法整体架构；\n2. 核心创新和与相关工作的本质区别；\n3. 实验数据集、可证实的定量指标、失败案例；\n"
  +"4. 是否支持稀疏视角、密集时间、固定且同步的多相机视频，以及通用动态4DGS；\n"
  +"5. 代码、权重、数据开源状态，复现步骤、算力与显存评估；\n"
  +"6. 基于8张NVIDIA H20制定最小验证实验，明确预期风险。\n"
  +"请标明原文依据和技术推断，未知信息明确写未知，不要编造任何数字、仓库或结论。";
 }
 async function copyPrompt(paper){
  const value=aiPrompt(paper);
  try{await navigator.clipboard.writeText(value);return true}catch{
   const text=document.createElement("textarea");text.value=value;text.style.position="fixed";text.style.opacity="0";document.body.append(text);text.select();
   const success=document.execCommand("copy");text.remove();return success;
  }
 }
 window.ResearchStore={read,get,set,exportData,importData,copyPrompt,aiPrompt};
})();