#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地写作工具。用法：python3 write.py

只依赖标准库。会起一个小服务器，在浏览器里写 Markdown、实时预览、一键发布。
"""

import json
import os
import re
import subprocess
import sys
import webbrowser
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import build

ROOT = Path(__file__).resolve().parent
POSTS = ROOT / "posts"
EDITOR = ROOT / "editor.html"
HOST = "127.0.0.1"


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug


def read_post(path):
    meta, body = build.parse_front_matter(path.read_text(encoding="utf-8"))
    m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)$", path.stem)
    return {
        "file": path.stem,
        "slug": m.group(2) if m else path.stem,
        "date": meta.get("date") or (m.group(1) if m else ""),
        "title": meta.get("title", path.stem),
        "column": meta.get("column", ""),
        "summary": meta.get("summary", ""),
        "video": meta.get("video", ""),
        "draft": meta.get("draft", "").lower() in ("true", "yes", "1"),
        "body": body.lstrip("\n"),
    }


def list_posts():
    items = [read_post(p) for p in POSTS.glob("*.md")]
    items.sort(key=lambda x: (x["date"], x["slug"]), reverse=True)
    return items


def write_post(data):
    title = (data.get("title") or "").strip()
    day = (data.get("date") or "").strip() or date.today().isoformat()
    slug = (data.get("slug") or "").strip() or slugify(title) or "post"
    body = (data.get("body") or "").replace("\r\n", "\n").strip("\n")

    if not title:
        raise ValueError("标题不能为空")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        raise ValueError("日期格式应为 YYYY-MM-DD")
    if not re.match(r"^[a-z0-9][a-z0-9-]*$", slug):
        raise ValueError("网址只能用小写字母、数字和连字符")

    lines = ["---", "title: %s" % title, "date: %s" % day]
    if (data.get("column") or "").strip():
        lines.append("column: %s" % data["column"].strip())
    if (data.get("summary") or "").strip():
        lines.append("summary: %s" % data["summary"].strip())
    if (data.get("video") or "").strip():
        lines.append("video: %s" % data["video"].strip())
    if data.get("draft"):
        lines.append("draft: true")
    lines.append("---")
    lines.append("")

    stem = "%s-%s" % (day, slug)
    path = POSTS / (stem + ".md")
    path.write_text("\n".join(lines) + "\n" + body + "\n", encoding="utf-8")

    old = (data.get("file") or "").strip()
    if old and old != stem:
        old_path = POSTS / (old + ".md")
        if old_path.exists():
            old_path.unlink()

    return stem


def run_build():
    proc = subprocess.run([sys.executable, "build.py"], cwd=str(ROOT),
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def git_publish(title):
    def run(*args):
        return subprocess.run(["git", *args], cwd=str(ROOT),
                              capture_output=True, text=True)

    logs = []
    add = run("add", "-A")
    logs.append(add.stderr.strip())
    commit = run("commit", "-m", "post: %s" % title)
    logs.append((commit.stdout + commit.stderr).strip())
    push = run("push")
    logs.append((push.stdout + push.stderr).strip())
    ok = push.returncode == 0
    return ok, "\n".join(x for x in logs if x)


def preview_page(body):
    fragment = build.render_markdown(body or "")
    return ("<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
            "<base href=\"/\"><link rel=\"stylesheet\" href=\"/style.css\"></head>"
            "<body><main>%s</main></body></html>" % fragment)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj, ensure_ascii=False), "application/json")

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            self._send(200, EDITOR.read_text(encoding="utf-8"), "text/html")
        elif path == "/style.css":
            self._send(200, (ROOT / "static" / "style.css").read_bytes(), "text/css")
        elif path.startswith(("/images/", "/videos/")):
            target = (ROOT / "static" / path.lstrip("/")).resolve()
            if target.is_file() and str(target).startswith(str(ROOT / "static")):
                self._send(200, target.read_bytes(), "application/octet-stream")
            else:
                self._send(404, "not found", "text/plain")
        elif path == "/api/meta":
            self._json({
                "today": date.today().isoformat(),
                "now": datetime.now().strftime("%H%M"),
                "columns": [{"key": c["key"], "name": c["name"]} for c in build.COLUMNS],
            })
        elif path == "/api/posts":
            self._json(list_posts())
        elif path == "/api/post":
            stem = (query.get("file") or [""])[0]
            target = POSTS / (stem + ".md")
            if not target.exists():
                self._json({"error": "找不到这篇文章"}, 404)
                return
            self._json(read_post(target))
        else:
            self._send(404, "not found", "text/plain")

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            data = self._body()
        except json.JSONDecodeError:
            self._json({"error": "请求格式不对"}, 400)
            return

        try:
            if path == "/api/save":
                stem = write_post(data)
                ok, log = run_build()
                self._json({"file": stem, "ok": ok, "log": log})
            elif path == "/api/preview":
                self._send(200, preview_page(data.get("body", "")), "text/html")
            elif path == "/api/publish":
                stem = write_post(data)
                ok_build, log_build = run_build()
                if not ok_build:
                    self._json({"ok": False, "log": "构建失败：\n" + log_build})
                    return
                ok, log = git_publish(data.get("title", ""))
                self._json({"file": stem, "ok": ok, "log": log})
            elif path == "/api/delete":
                stem = (data.get("file") or "").strip()
                target = POSTS / (stem + ".md")
                if not target.exists():
                    self._json({"ok": False, "log": "文件不存在"}, 404)
                    return
                target.unlink()
                ok, log = run_build()
                self._json({"ok": ok, "log": log})
            else:
                self._send(404, "not found", "text/plain")
        except ValueError as exc:
            self._json({"error": str(exc)}, 400)
        except Exception as exc:  # noqa: BLE001
            self._json({"error": "出错了：%s" % exc}, 500)


def main():
    port = 8124
    for candidate in range(8124, 8135):
        try:
            server = ThreadingHTTPServer((HOST, candidate), Handler)
            port = candidate
            break
        except OSError:
            continue
    else:
        print("端口都被占用了")
        sys.exit(1)

    url = "http://%s:%d/" % (HOST, port)
    print("写作工具已启动：%s" % url)
    print("Ctrl+C 退出")
    if os.environ.get("NO_BROWSER") != "1":
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出")


if __name__ == "__main__":
    main()
