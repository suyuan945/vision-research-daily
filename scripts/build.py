#!/usr/bin/env python3
import json,html,re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]; SITE=ROOT/'site'; CONTENT=ROOT/'content'
(SITE/'issues').mkdir(parents=True,exist_ok=True)
index=[]
for f in sorted(CONTENT.glob('*.json')):
 d=json.loads(f.read_text(encoding='utf-8')); date=d['date']
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date): continue
 datetime.strptime(date,'%Y-%m-%d')
 title=html.escape(d['title']); tags=d.get('tags',[])
 import mistune
 body=mistune.create_markdown(plugins=['table','strikethrough','url'])(d['markdown'])
 content=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} · 3D Vision Daily</title><link rel="stylesheet" href="../assets/style.css"></head><body><header><a href="../">← 3D VISION DAILY</a></header><main class="article"><small>{date} · {html.escape(d.get('kind','技术日报'))}</small><h1>{title}</h1><p>{''.join('<span class="tag">'+html.escape(str(t))+'</span>' for t in tags)}</p>{body}<p><a href="../#archive">← 返回历史归档</a></p></main><footer>3D Vision Research Daily</footer></body></html>'''
 (SITE/'issues'/f'{date}.html').write_text(content,encoding='utf-8')
 index.append({k:d[k] for k in ('date','title','summary','kind','tags','highlights') if k in d}|{'url':f'issues/{date}.html'})
(SITE/'index.json').write_text(json.dumps(sorted(index,key=lambda x:x['date'],reverse=True),ensure_ascii=False,indent=2),encoding='utf-8')
print('Built',len(index),'issues')
