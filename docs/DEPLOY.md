# 上线步骤

1. 确保仓库具备 GitHub Pages 发布资格。对于个人 Free 计划，通常需要把仓库设为 Public；私人仓库 Pages 权限依具体 GitHub 套餐而定。
2. Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。
3. 在 [DeepSeek API 平台](https://platform.deepseek.com/) 创建 API Key，确认账户有可用余额，然后前往 Settings → Secrets and variables → Actions → New repository secret：`DEEPSEEK_API_KEY`（不要粘贴到文件、Issue 或聊天中）。没有密钥时仅发布现有历史。
4. Actions → **Generate and publish research daily** → Run workflow；检查 build 和 deploy 两个 job。
5. 成功后打开 `https://suyuan945.github.io/vision-research-daily/`。

## 每日任务

GitHub Actions 计划在北京时间 07:10 触发，实际运行可能延迟。网页日报由 arXiv 和 DeepSeek 独立生成，DeepSeek API 单独计费。若没有新来源，网站保留最近一期。若生成失败，网站仍会部署现有归档，运行会标为失败。可展开 `Generate daily issue` 查看失败原因和 DeepSeek 结束状态。

## 数据安全

网站内容及论文链接均视为公开内容。避免上传私人研究笔记、保密数据或公司材料。

## GitHub 与公众号

- 在 `sources.json` 中调整 GitHub 研究方向和重点仓库。每日查找近七天新建项目，并读取重点仓库的公开 Releases。新仓库、首次收录与版本发布按各自日期展示。仓库和版本分别按 GitHub ID 去重。README 中出现的 arXiv 链接用于关联论文，关联仅代表仓库提及该论文。
- 公众号列表中填公开 RSS 地址即可参与每日采集。未找到稳定来源的账号填写 `null`，可以在 `wechat.articles` 加入已核实的公开原文链接、标题、日期和简短摘要。自动收录按相关方向筛选，只保存标题、日期、链接和标签。
- `site/github.json` 和 `site/articles.json` 由工作流维护。来源读取失败时保留历史记录，构建继续，工作流在部署后报告失败。可在 Actions 的采集步骤查看详情。
- 知识星球的成员内容可在本地 `.private/` 整理成个人简报。该目录不参与站点构建或发布。公开发布使用经确认可公开的原始来源。
