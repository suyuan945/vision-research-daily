#!/usr/bin/env python3
import json,html,re
from pathlib import Path
from datetime import datetime
import mistune
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'site'
CONTENT=ROOT/'content'
(SITE/'issues').mkdir(parents=True,exist_ok=True)
md=mistune.create_markdown(plugins=['table','strikethrough','url'])
index=[]
header='<header class="site-header"><div class="header-inner"><a class="brand" href="../"><span class="brand-mark">◈</span><span>3D <em>VISION</em> DAILY</span></a><nav class="site-nav"><a href="../#latest">最新日报</a><a href="../#archive">历史归档</a></nav></div></header>'
for path in sorted(CONTENT.glob('*.json')):
    d=json.loads(path.read_text(encoding='utf-8'))
    date=d['date']
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):continue
    datetime.strptime(date,'%Y-%m-%d')
    title=html.escape(d['title'])
    subtitle=html.escape(d.get('summary',''))
    kind=html.escape(d.get('kind','技术日报'))
    tags=''.join('<span class="tag">'+html.escape(str(tag))+'</span>' for tag in d.get('tags',[]))
    body=md(d.get('markdown',''))
    body=re.sub(r'(<table>.*?</table>)',r'<div class="table-scroll">\1</div>',body,flags=re.S)
    page=f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{subtitle}"><title>{title} · 3D Vision Daily</title><link rel="stylesheet" href="../assets/style.css"></head>
<body>{header}<main class="article-shell"><a class="article-back" href="../#archive">← 返回历史归档</a><div class="article-header"><div class="article-kicker"><span>{date}</span><span> / </span><span>{kind}</span></div><h1>{title}</h1><p class="article-intro">{subtitle}</p><div class="tag-list">{tags}</div></div><article class="prose">{body}</article><div class="article-end"><a href="../#archive">← 查看更多历史日报</a></div></main><footer class="site-footer">3D VISION RESEARCH DAILY · RESEARCH FIRST, EVIDENCE FIRST.</footer></body></html>'''
    (SITE/'issues'/f'{date}.html').write_text(page,encoding='utf-8')
    index.append({k:d[k] for k in ('date','title','summary','kind','tags','highlights') if k in d}|{'url':f'issues/{date}.html'})
(SITE/'index.json').write_text(json.dumps(sorted(index,key=lambda d:d['date'],reverse=True),ensure_ascii=False,indent=2),encoding='utf-8')
print('Built',len(index),'issues')
