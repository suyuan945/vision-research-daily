# 上线步骤

1. 确保仓库具备 GitHub Pages 发布资格。对于个人 Free 计划，通常需要把仓库设为 Public；私人仓库 Pages 权限依具体 GitHub 套餐而定。
2. Settings → Pages → Build and deployment → Source 选 **GitHub Actions**。
3. Settings → Secrets and variables → Actions → New repository secret：`OPENAI_API_KEY`（不要粘贴到文件、Issue 或聊天中）。没有密钥时仅发布现有历史。
4. Actions → **Generate and publish research daily** → Run workflow；检查 build 和 deploy 两个 job。
5. 成功后打开 `https://suyuan945.github.io/vision-research-daily/`。

## 每日任务

GitHub Actions 在东京时间约08:10触发（可能延迟）；OpenAI API 与 ChatGPT 订阅分开计费。ChatGPT 自动推送保留原样，网站从 arXiv 生成独立文章，不会自动复制聊天内容。若当天没有有价值的新增论文，生成器可跳过发布。

## 数据安全

网站内容及论文链接均视为公开内容。避免上传私人研究笔记、保密数据或公司材料。
