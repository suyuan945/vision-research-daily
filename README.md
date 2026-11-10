# 3D Vision Research Daily

中文论文日报网站：3DGS、4DGS、VGGT、SfM/SLAM、几何记忆和世界模型。

- 历史文章位于 `content/YYYY-MM-DD.json`；初始12期为前序聊天的**摘要索引**，不是全文，也未重新核实实验数据。
- `scripts/build.py` 生成静态网站，输出到 `site/`。
- `scripts/generate.py` 从 arXiv 元数据生成新增一期；需要单独计费的 `OPENAI_API_KEY`。
- `.github/workflows/daily.yml` 每天定时构建并发布 GitHub Pages。

## 本地预览

```bash
pip install -r requirements.txt
python scripts/build.py
cd site && python -m http.server 8000
```

## 部署

参见 [部署说明](docs/DEPLOY.md)。现有 ChatGPT 每日推送不会被修改，网页版为**独立生成**，两份文本并不保证一致。不要上传私人信息、企业数据或 API 密钥。
