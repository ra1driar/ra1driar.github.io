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

## 写作工具

不想手写 front matter 就用这个：

```bash
python3 write.py
```

浏览器会自己打开 `http://127.0.0.1:8124/`：

- 左边是全部文章，点一下就能改
- 标题、日期、专栏下拉、网址、摘要、视频、草稿开关都是表单
- 正文用 Markdown，右侧实时预览，预览加载的是站点同一套 `style.css`
- **保存并构建**：写文件 + 重新生成 `docs/`
- **发布到线上**：保存 + 构建 + `git add/commit/push`，一步到位
- **删除**：删掉文件并重新构建

服务只监听 `127.0.0.1`，局域网里的别人访问不到。按 `Ctrl+C` 退出。

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

## 绑定自己的域名

1. 在注册商买一个域名
2. `site.ini` 里填 `domain = example.com`，跑 `python3 build.py`
3. 推送到 GitHub
4. 仓库 Settings → Pages → Custom domain 填 `example.com`，Save
5. 去 DNS 服务商加记录：

| 类型 | 名称 | 值 |
|---|---|---|
| A | `@` | `185.199.108.153`、`185.199.109.153`、`185.199.110.153`、`185.199.111.153` |
| AAAA | `@` | `2606:50c0:8000::153`、`2606:50c0:8001::153`、`2606:50c0:8002::153`、`2606:50c0:8003::153` |
| CNAME | `www` | `<用户名>.github.io` |

6. `dig example.com +short` 确认解析到上面四个 A 记录
7. 回到 Settings → Pages，等 Custom domain 检查通过，勾上 **Enforce HTTPS**

几个坑：

- **先在第 4 步填域名，再去配 DNS**。反过来会留下被人抢注子域名的窗口。
- `docs/CNAME` 是构建生成的，不要手写，下次构建会被覆盖。
- 域名放在 Cloudflare 的话，先把代理关掉（灰云 / DNS only），等 GitHub 签发证书后再考虑开橙云；开橙云时 SSL/TLS 模式必须选 **Full**，否则会无限重定向。
- 域名到期比服务器宕机常见得多，开自动续费。

买域名的渠道：

- **Cloudflare Registrar**：按成本价卖，没有加价，`.com` 大约 $10–11/年，域名必须用 Cloudflare DNS（免费）。
- **Porkbun / Namecheap**：首年促销多，续费略贵。
- **阿里云 / 腾讯云**：支付方便，`.cn` 需要实名；解析到 GitHub 不需要备案，因为服务器不在境内。

## 目录

| 路径 | 是什么 | 谁来改 |
|---|---|---|
| `posts/` | 文章原文，Markdown + front matter | 你，用编辑器 |
| `about.md` | 首页“为什么有这个东西”那段，纯 Markdown | 你 |
| `static/` | 样式表、图片、视频，构建时整体复制进 `docs/` | 你 |
| `site.ini` | 站点标题、描述、作者、URL | 你 |
| `columns.ini` | 专栏定义（随笔 / 读后感 / topic discuss） | 你 |
| `build.py` | 构建逻辑，不含任何内容数据 | 基本不用动 |
| `template.html` | 页面骨架 | 想改结构时动 |
| `docs/` | 构建产物，**不要手改**，改了会被下次构建覆盖 | 脚本 |

内容和代码是分开的：`build.py` 里没有任何一篇文章、一条配置。换渲染方式、换主题、甚至换静态生成器，`posts/` 里的东西都不用动。

## 文章格式

```markdown
---
title: 标题
date: 2026-11-08
summary: 列表页和 RSS 里显示的一句话，可省略（省略时自动取正文前 20 字）
column: 随笔               # 专栏，见下文
video: videos/demo.mp4     # 可选
poster: videos/demo.jpg    # 可选，视频封面
draft: true                # 可选，true 时不参与构建
---

正文从这儿开始。
```

文件名必须是 `YYYY-MM-DD-slug.md`，`slug` 决定网址。有专栏的文章放在 `/columns/<专栏 key>` 对应的目录下，比如写了 `column: 随笔` 就是 `docs/essay/<slug>.html`；没有专栏的才放在 `docs/posts/` 下。

## 专栏

专栏定义在 `columns.ini`，文件里的顺序就是顶部导航的顺序：

```ini
[essay]
name = 随笔
description = 想到什么写什么。
```

文章 front matter 里写 `column: 随笔`（写 `column: essay` 也行），构建时会：

- 在首页列表的日期后面显示专栏名
- 生成 `docs/columns/essay.html`，列出该专栏的全部文章
- 在 RSS 里加一个 `<category>`
- 顶部导航自动带上这个专栏

新增专栏只需要在 `columns.ini` 里加一段，`key` 决定网址，不用改代码。没有写 `column` 的文章不会出现在任何专栏页，只在首页。

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
