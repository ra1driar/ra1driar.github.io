# 个人站点

Markdown 进，静态 HTML 出，GitHub Pages 托管。

**零第三方依赖**：只要 `python3`。没有 npm、没有 pip、没有 pandoc，没有需要定期升级的东西。

## 发布一篇

```bash
# 1. 新建 posts/YYYY-MM-DD-slug.md
# 2. 构建
python3 build.py
# 3. 提交并推送
git add -A && git commit -m "post: 标题" && git push
```

GitHub Pages 会在推送后一两分钟内更新。

## 本地预览

```bash
python3 build.py
python3 -m http.server 8123 --directory docs
# 浏览器打开 http://127.0.0.1:8123/
```

改了文章或样式之后重新跑一次 `build.py`，刷新页面就能看到。注意 `file://` 直接打开也能看，但用本地服务器更接近线上效果。

## 首次部署

仓库推到 GitHub 之后：

1. 仓库 Settings → Pages
2. Source 选 **Deploy from a branch**
3. 分支选 `main`，目录选 `/docs`，保存
4. 地址是 `https://<用户名>.github.io/<仓库名>/`

`docs/.nojekyll` 已经生成，防止 GitHub 用 Jekyll 处理构建产物。

> 注意：免费账号要发布 Pages，仓库必须是 **public**，也就是文章原文对所有人可见。不介意就这样。

## 目录

| 路径 | 是什么 | 谁来改 |
|---|---|---|
| `posts/` | 文章原文，Markdown + front matter | 你，用编辑器 |
| `static/` | 样式表、图片、视频，构建时整体复制进 `docs/` | 你 |
| `site.ini` | 站点标题、描述、作者、URL | 你 |
| `build.py` | 构建逻辑，不含任何内容数据 | 基本不用动 |
| `template.html` | 页面骨架 | 想改结构时动 |
| `docs/` | 构建产物，**不要手改**，改了会被下次构建覆盖 | 脚本 |

内容和代码是分开的：`build.py` 里没有任何一篇文章、一条配置。换渲染方式、换主题、甚至换静态生成器，`posts/` 里的东西都不用动。

## 文章格式

```markdown
---
title: 标题
date: 2026-11-08
summary: 列表页和 RSS 里显示的一句话，可省略（省略时自动取正文前 90 字）
video: videos/demo.mp4     # 可选
poster: videos/demo.jpg    # 可选，视频封面
draft: true                # 可选，true 时不参与构建
---

正文从这儿开始。
```

文件名必须是 `YYYY-MM-DD-slug.md`，`slug` 决定网址 `docs/posts/<slug>.html`。

## 加视频

把文件放进 `static/videos/`，front matter 写 `video: videos/demo.mp4`，构建时会自动插入 `<video controls preload="metadata">`，并带上 `poster`（如果有）。

想嵌 B 站 / YouTube 播放器，直接在正文里贴 `<iframe ...>`：以 `<` 开头的整行会作为原始 HTML 原样输出。

视频文件建议控制在 50MB 以内、总量 500MB 以内（GitHub 单文件硬上限 100MB，仓库软上限 1GB）。超了再换对象存储，那时把 front matter 里的路径改成完整 URL 即可。

## 支持的 Markdown

标题、段落（单个换行会保留为换行，适合中文排版）、粗体/斜体/删除线、行内代码、围栏代码块（带语言标注）、链接、尖括号自动链接、图片、无序/有序列表（按缩进嵌套）、引用、表格、分隔线、原始 HTML 块。

不支持：脚注、任务列表、行内 HTML 标签混排。需要的话再扩，渲染器就在 `build.py` 里。

## 改样子

只改 `static/style.css`。深色模式是 `prefers-color-scheme` 自动跟随系统，没有额外配置。

## 备份

仓库就是备份。`git clone` 到任何地方，`python3 build.py` 就能重新生成整站。

## 隐私

所有页面都带 `<meta name="robots" content="noindex, nofollow">`，`docs/robots.txt` 也禁止抓取。搜索引擎不会收录，但知道链接的人仍能访问，适合给固定的一小圈人看。
