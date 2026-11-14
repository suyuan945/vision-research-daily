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
