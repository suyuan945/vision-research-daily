# 3D Vision Research Hub — V2.0

研究方向：3DGS / 4DGS / VGGT / 视觉几何 / SfM-SLAM / 世界模型。

网站： https://suyuan945.github.io/vision-research-daily/

## 已实现

- 今日：最新日报与该期关联的独立论文
- 论文库：以 arXiv ID 去重的静态论文索引，支持标题、摘要、ID 和研究方向过滤
- 我的收藏：一键收藏、取消收藏，研究状态（待读、精读中、待复现、已完成）
- JSON 导入/导出：收藏默认只保存在当前浏览器 localStorage，不自动云同步；导入将按论文 ID 覆盖同 ID 状态
- AI 解读：复制带论文链接、研究偏好和复现实验清单的 ChatGPT 研究问题；再由使用者自行打开 ChatGPT 粘贴提问
- 历史日报：原有12期摘要和未来自动生成日报，保留旧链接 `issues/YYYY-MM-DD.html`

## 技术结构

```text
content/YYYY-MM-DD.json    每日来源内容（公开）
scripts/generate.py        arXiv API + DeepSeek AI 生成新日报、源论文元数据
scripts/build.py           静态编译：site/index.json、site/papers.json、论文详情HTML
site/assets/research-store.js  本地收藏状态schema，导入导出
site/assets/app.js         检索、收藏、页面路由、AI解读
.github/workflows/daily.yml   GitHub Pages 部署、日常采集
```

## 部署与密钥

GitHub Settings > Pages 选择 **GitHub Actions**。GitHub Actions Secrets 中设置 `DEEPSEEK_API_KEY`（不要写入源码）。

GitHub Actions 可以定时及手动执行；网站代码推送也会触发重新构建。已有 ChatGPT 每日推送独立保留，网页版不是原消息的逐字镜像。API 余额由 DeepSeek 平台管理。

## 收藏的隐私与局限

收藏数据保存在浏览器本地的 `vision-research-v2` 条目。清理网站数据、切换浏览器或设备后无法自动恢复，建议经常使用「导出收藏 JSON」备份并妥善保管。数据不存入公开 GitHub 仓库。当前没有云端同步、账号、笔记同步，也不会直接调用 ChatGPT 账户接口。

首次导入的历史论文可能只带有日报中的缩写标题和链接，不表示已核实发表日期、摘要或开源状态；新的论文将优先使用 arXiv 元数据。

## 本地构建

```bash
pip install -r requirements.txt
python scripts/build.py
cd site
python -m http.server 8000
```
