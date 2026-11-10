#!/usr/bin/env python3
"""Daily arXiv-source digest; no private ChatGPT messages involved."""
import os,json,re,urllib.request,urllib.parse,xml.etree.ElementTree as ET
from datetime import datetime,timedelta,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'content'
KEY=os.getenv('OPENAI_API_KEY')
if not KEY: print('No OPENAI_API_KEY; skipping new issue');raise SystemExit(0)
TZ=timezone(timedelta(hours=9)); day=datetime.now(TZ).date().isoformat()
if (OUT/f'{day}.json').exists(): print('Issue exists; skipping');raise SystemExit(0)
params=urllib.parse.urlencode({'search_query':'cat:cs.CV OR cat:cs.AI OR cat:cs.RO','start':0,'max_results':180,'sortBy':'submittedDate','sortOrder':'descending'})
req=urllib.request.Request('https://export.arxiv.org/api/query?'+params,headers={'User-Agent':'VisionResearchDaily/1.0'})
with urllib.request.urlopen(req,timeout=55) as r:root=ET.fromstring(r.read())
ns={'a':'http://www.w3.org/2005/Atom'}
papers=[]
for e in root.findall('a:entry',ns):
 link=e.findtext('a:id','',ns).replace('http://','https://')
 if not re.fullmatch(r'https://arxiv.org/abs/\d{4}\.\d+(?:v\d+)?',link):continue
 published=e.findtext('a:published','',ns)
 if datetime.fromisoformat(published.replace('Z','+00:00'))<datetime.now(timezone.utc)-timedelta(days=8):continue
 papers.append({'title':' '.join(e.findtext('a:title','',ns).split()),'summary':' '.join(e.findtext('a:summary','',ns).split())[:1200],'url':re.sub(r'v\d+$','',link),'published':published})
recent=set()
for f in sorted(OUT.glob('*.json'),reverse=True)[:8]:
 previous=json.loads(f.read_text(encoding='utf-8'))
 recent.update(re.findall(r'https://arxiv.org/abs/\d{4}\.\d+',previous.get('markdown','')))
papers=[p for p in papers if p['url'] not in recent]
if not papers:print('No new sources');raise SystemExit(0)
prompt='''请从所给官方arXiv记录筛选最近24小时最重要的3–6项与3DGS/4DGS/VGGT/几何基础模型/世界模型相关的新论文，必要时扩展到7天。不足3篇高价值项目时最多选2篇，明确说明新闻较少。中文详细技术解读、严格使用给定发布日期和arXiv链接，阐述机制、与旧方法差异、对稀疏同步多机位4DGS和生成外展的价值、复现状态（如记录中没有代码地址则写未核实）、实验指标只引用给定摘要中明确数字，不得编造代码仓库和数值。不要重复历史论文。只输出JSON对象：title,summary,tags(array),highlights(array),markdown(string)。材料：''' +json.dumps(papers,ensure_ascii=False)
payload={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'你是严谨的科研日报编辑；不可发明来源、指标、仓库。'},{'role':'user','content':prompt}]}
req=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=120) as r:response=json.load(r)
d=json.loads(response['choices'][0]['message']['content']);md=d['markdown']
links=set(re.findall(r'https://arxiv.org/abs/\d{4}\.\d+',md))
allowed={p['url'] for p in papers}
if not links or not links.issubset(allowed) or links&recent or len(md)<350:raise RuntimeError('Generated digest failed evidence/duplicate checks')
data={'date':day,'kind':'自动生成 · 独立网页版','title':d['title'],'summary':d['summary'],'tags':d['tags'],'highlights':d['highlights'],'markdown':md+'\n\n---\n\n*由模型根据arXiv元数据生成，复现状态及指标请以官方论文为准。*'}
OUT.mkdir(exist_ok=True);(OUT/f'{day}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Published content:',day)
