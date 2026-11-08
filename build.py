#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 posts/*.md 构建成 docs/ 下的静态站点。

只依赖 Python 3 标准库，不需要 pip / npm / pandoc。
用法：python3 build.py
"""

import configparser
import html
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
STATIC = ROOT / "static"
OUT = ROOT / "docs"


def load_site_config():
    """站点信息放在 site.ini，不写死在代码里。"""
    parser = configparser.ConfigParser()
    parser.read(ROOT / "site.ini", encoding="utf-8")

    def get(key, default=""):
        return parser.get("site", key, fallback=default).strip()

    return {
        "title": get("title", "我的站点"),
        "description": get("description", ""),
        "author": get("author", ""),
        "url": get("url", ""),
    }


SITE = load_site_config()
SITE_TITLE = SITE["title"]
SITE_DESC = SITE["description"]
AUTHOR = SITE["author"]
SITE_URL = SITE["url"]  # 填上 GitHub Pages 地址后 RSS 里才是绝对链接

TEMPLATE = (ROOT / "template.html").read_text(encoding="utf-8")


# ---------- Markdown ----------

def _link(text, url):
    if url.lower().startswith(("javascript:", "data:")):
        return text
    return '<a href="%s">%s</a>' % (url, text)


def inline(text):
    """处理行内语法。传入的 text 必须已经过 html.escape。"""
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return "\x00%d\x00" % (len(codes) - 1)

    text = re.sub(r"`([^`]+)`", stash, text)
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)\s]+)\)",
        lambda m: '<img src="%s" alt="%s" loading="lazy">' % (m.group(2), m.group(1)),
        text,
    )
    text = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)",
                  lambda m: _link(m.group(1), m.group(2)), text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\w)__([^_]+)__(?!\w)", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", text)
    text = re.sub("\x00([0-9]+)\x00",
                  lambda m: "<code>%s</code>" % codes[int(m.group(1))], text)
    return text


LIST_RE = re.compile(r"^([-*+]|\d+\.)\s+(.*)$")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*)$")
HR_RE = re.compile(r"^(-{3,}|\*{3,}|_{3,})$")
TABLE_SEP_RE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?$")


def _is_block_start(s):
    return bool(
        HEAD_RE.match(s)
        or LIST_RE.match(s)
        or HR_RE.match(s)
        or s.startswith((">", "```", "<", "|"))
    )


def render_markdown(text):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = []
    i, n = 0, len(lines)

    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue

        # 围栏代码块
        if s.startswith("```"):
            lang = s[3:].strip()
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # 跳过结束围栏
            cls = ' class="language-%s"' % html.escape(lang) if lang else ""
            out.append("<pre><code%s>%s</code></pre>"
                       % (cls, html.escape("\n".join(buf))))

        # 原始 HTML 块，整段原样输出
        elif s.startswith("<"):
            buf = []
            while i < n and lines[i].strip() and lines[i].strip().startswith("<"):
                buf.append(lines[i])
                i += 1
            out.append("\n".join(buf))

        # 标题
        elif HEAD_RE.match(s):
            level = len(HEAD_RE.match(s).group(1))
            out.append("<h%d>%s</h%d>"
                       % (level, inline(html.escape(HEAD_RE.match(s).group(2).strip())), level))
            i += 1

        # 分隔线
        elif HR_RE.match(s):
            out.append("<hr>")
            i += 1

        # 引用
        elif s.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            out.append("<blockquote>%s</blockquote>"
                       % render_markdown("\n".join(buf)))

        # 表格
        elif ("|" in s
              and i + 1 < n
              and TABLE_SEP_RE.match(lines[i + 1].strip())):
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip() and "|" in lines[i]:
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            thead = "".join("<th>%s</th>" % inline(html.escape(c)) for c in header)
            tbody = "".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % inline(html.escape(c)) for c in r)
                for r in rows
            )
            out.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>"
                       % (thead, tbody))

        # 列表（一层，不支持嵌套）
        elif LIST_RE.match(s):
            ordered = LIST_RE.match(s).group(1).endswith(".")
            tag = "ol" if ordered else "ul"
            items = []
            while i < n:
                mm = LIST_RE.match(lines[i].strip())
                if not mm:
                    break
                items.append("<li>%s</li>" % inline(html.escape(mm.group(2))))
                i += 1
            out.append("<%s>%s</%s>" % (tag, "".join(items), tag))

        # 段落：单个换行保留为 <br>，方便中文排版
        else:
            buf = []
            while i < n:
                s2 = lines[i].strip()
                if not s2 or _is_block_start(s2):
                    break
                buf.append(html.escape(s2))
                i += 1
            para = inline("\n".join(buf)).replace("\n", "<br>")
            out.append("<p>%s</p>" % para)

    return "\n".join(out)


# ---------- 页面 ----------

def parse_front_matter(text):
    meta = {}
    if text.startswith("---"):
        lines = text.split("\n")
        if lines[0].strip() == "---":
            for idx in range(1, len(lines)):
                if lines[idx].strip() == "---":
                    for line in lines[1:idx]:
                        if ":" in line:
                            k, v = line.split(":", 1)
                            meta[k.strip()] = v.strip().strip('"').strip("'")
                    return meta, "\n".join(lines[idx + 1:])
    return meta, text


def page(body, page_title, description, root):
    return (TEMPLATE
            .replace("{{body}}", body)
            .replace("{{page_title}}", html.escape(page_title))
            .replace("{{description}}", html.escape(description))
            .replace("{{site_title}}", html.escape(SITE_TITLE))
            .replace("{{author}}", html.escape(AUTHOR))
            .replace("{{year}}", str(datetime.now().year))
            .replace("{{root}}", root))


def plain_text(fragment, limit=90):
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def load_posts():
    posts = []
    for path in sorted(POSTS.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        if meta.get("draft", "").lower() in ("true", "yes", "1"):
            continue

        stem = path.stem
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", stem)
        if m:
            date_str, slug = m.group(1), m.group(2)
        else:
            date_str, slug = meta.get("date", ""), stem

        date_str = meta.get("date") or date_str
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise SystemExit("文章日期格式不对（应为 YYYY-MM-DD）：%s" % path)

        rendered = render_markdown(body)
        posts.append({
            "path": path,
            "title": meta.get("title") or slug,
            "date": date,
            "date_str": date.strftime("%Y-%m-%d"),
            "summary": meta.get("summary") or plain_text(rendered),
            "slug": slug,
            "body": rendered,
            "video": meta.get("video", ""),
            "poster": meta.get("poster", ""),
        })

    posts.sort(key=lambda p: (p["date"], p["title"]), reverse=True)
    return posts


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    if STATIC.exists():
        shutil.copytree(STATIC, OUT, dirs_exist_ok=True)

    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    posts = load_posts()

    # 文章页
    (OUT / "posts").mkdir()
    for p in posts:
        parts = ["<h1>%s</h1>" % html.escape(p["title"]),
                 '<p class="meta"><time datetime="%s">%s</time></p>'
                 % (p["date_str"], p["date_str"])]
        if p["video"]:
            poster = ' poster="%s%s"' % ("../", p["poster"]) if p["poster"] else ""
            parts.append('<figure class="video"><video controls preload="metadata" '
                         'playsinline src="../%s"%s></video></figure>'
                         % (p["video"], poster))
        parts.append(p["body"])

        title = "%s · %s" % (p["title"], SITE_TITLE)
        page_html = page("\n".join(parts), title, p["summary"], "../")
        (OUT / "posts" / (p["slug"] + ".html")).write_text(page_html, encoding="utf-8")

    # 首页
    items = []
    for p in posts:
        items.append(
            '<li><time datetime="%s">%s</time>'
            '<a href="posts/%s.html">%s</a>'
            '<p class="summary">%s</p></li>'
            % (p["date_str"], p["date_str"], p["slug"],
               html.escape(p["title"]), html.escape(p["summary"]))
        )
    index_body = ('<h1>%s</h1>\n<p class="intro">%s</p>\n'
                  '<ul class="post-list">\n%s\n</ul>'
                  % (html.escape(SITE_TITLE), html.escape(SITE_DESC), "\n".join(items)))
    (OUT / "index.html").write_text(
        page(index_body, SITE_TITLE, SITE_DESC, ""), encoding="utf-8")

    # RSS
    base = SITE_URL.rstrip("/") + "/" if SITE_URL else ""
    entries = []
    for p in posts:
        link = base + "posts/" + p["slug"] + ".html" if base else "posts/" + p["slug"] + ".html"
        entries.append(
            "<item><title>%s</title><link>%s</link><guid>%s</guid>"
            "<pubDate>%s</pubDate><description>%s</description></item>"
            % (html.escape(p["title"]), html.escape(link), html.escape(link),
               p["date"].strftime("%a, %d %b %Y 00:00:00 +0800"),
               html.escape(p["summary"]))
        )
    feed = ('<?xml version="1.0" encoding="utf-8"?>\n<rss version="2.0"><channel>'
            "<title>%s</title><link>%s</link><description>%s</description>"
            "<language>zh-CN</language>%s</channel></rss>"
            % (html.escape(SITE_TITLE), html.escape(base or "index.html"),
               html.escape(SITE_DESC), "".join(entries)))
    (OUT / "feed.xml").write_text(feed, encoding="utf-8")

    print("构建完成：%d 篇文章 -> %s" % (len(posts), OUT))
    for p in posts:
        print("  posts/%s.html  %s  %s" % (p["slug"], p["date_str"], p["title"]))


if __name__ == "__main__":
    build()
