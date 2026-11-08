#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Sherlock 中文图形界面 —— 本地 Web 外壳

只用 Python 标准库，不需要额外安装依赖。
浏览器打开 http://127.0.0.1:8766 即可使用，界面全中文。
"""
from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.0.0"

GUI_DIR = Path(__file__).resolve().parent
BASE = GUI_DIR.parent
PYTHON = BASE / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():  # 没建虚拟环境时，退回启动本程序的解释器
    PYTHON = Path(sys.executable)
DATA_JSON = BASE / "sherlock_project" / "resources" / "data.json"

HOST = "127.0.0.1"
PORT = int(os.environ.get("SHERLOCK_GUI_PORT", "8766"))

# 自动打开浏览器时依次尝试的可执行文件（显式调用，不依赖系统默认程序关联）
# 顺序：Chrome → Edge → Firefox；Edge 在个别机器上会启动即退出，所以放在 Chrome 后面
BROWSER_CANDIDATES = [
    os.environ.get("SHERLOCK_BROWSER", ""),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path(os.environ.get("LOCALAPPDATA") or "") / "Google" / "Chrome" / "Application" / "chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    str(Path(os.environ.get("LOCALAPPDATA") or "") / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
    r"C:\Program Files\Mozilla Firefox\firefox.exe",
    r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
]


LOG_PATH = GUI_DIR / "启动日志.txt"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# 最近一次收到「页面请求」的时间戳，用来判断浏览器是不是真的把界面加载了
UI_HITS = {"last": 0.0}


def _log(msg: str) -> str:
    """写一行到 gui\\启动日志.txt，方便排查；同时也返回这行给控制台。"""
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:  # noqa: BLE001
        pass
    return line


def copy_url(url: str) -> bool:
    """把地址复制到剪贴板，浏览器打不开时用户可以直接粘贴。"""
    try:
        subprocess.run(
            ["clip"], input=url.encode("ascii"), check=False, timeout=5,
            creationflags=CREATE_NO_WINDOW,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def _proc_count(name: str) -> int:
    """用 tasklist 数进程个数，用来判断浏览器到底有没有真的起来。"""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {name}", "/NH"],
            capture_output=True, timeout=10, creationflags=CREATE_NO_WINDOW,
        )
    except Exception:  # noqa: BLE001
        return -1
    text = out.stdout.decode("mbcs", "ignore")
    return sum(1 for ln in text.splitlines() if name.lower() in ln.lower())


def _try_launch(argv: list[str], proc_name: str, label: str, wait: float,
                verify: bool = True) -> tuple[bool, str, bool]:
    """启动一个命令，然后确认浏览器到底有没有真的把页面打开。

    verify=True 时用「服务器有没有收到页面请求」来判断——这是唯一可靠的证据：
    进程起来了不代表窗口出来了，窗口出来了也不代表页面加载了。
    返回 (是否成功, 说明行, 进程是否还活着)。
    """
    base_hit = UI_HITS["last"]
    before = _proc_count(proc_name)
    try:
        subprocess.Popen(argv, close_fds=True)
    except Exception as exc:  # noqa: BLE001
        return False, _log(f"[失败] {label}：无法启动（{exc}）"), False

    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(0.25)
        if verify and UI_HITS["last"] > base_hit:
            return True, _log(f"[成功] {label}：页面已被浏览器加载"), True
        if not verify:
            now = _proc_count(proc_name)
            if now > before and now > 0:
                return True, _log(f"[成功] {label}：进程已起来（{before} → {now}）"), True

    now = _proc_count(proc_name)
    alive = now > 0
    if verify:
        tail = f"（进程数 {before} → {now}）" if now >= 0 else ""
        return False, _log(f"[失败] {label}：{wait:.0f} 秒内没收到页面请求{tail}"), alive
    if before > 0 and alive:
        return True, _log(f"[可能成功] {label}：已有窗口在运行，已交给它打开"), True
    return False, _log(f"[失败] {label}：启动后进程又消失了（{before} → {now}）"), alive


def open_ui(url: str, verify: bool = True) -> tuple[bool, str]:
    """尽最大努力打开浏览器，返回 (是否成功, 用的什么方式)。

    verify=True 表示服务器就在本进程里，可以靠「有没有收到页面请求」验证；
    如果界面已经在别的进程里跑着（重复双击的情况），只能靠进程判断。
    """
    if os.environ.get("SHERLOCK_NO_BROWSER"):
        return False, "已跳过"

    seen: set[str] = set()
    browsers: list[tuple[str, str, str]] = []  # (exe, 进程名, 显示名)
    for exe in BROWSER_CANDIDATES:
        if not exe or exe in seen:
            continue
        seen.add(exe)
        try:
            if not Path(exe).is_file():
                continue
        except Exception:  # noqa: BLE001
            continue
        browsers.append((exe, Path(exe).name, Path(exe).stem))

    _log(f"===== 开始尝试打开 {url} =====")
    wait = 5.0 if verify else 4.0
    for exe, proc_name, stem in browsers:
        print(f"  正在尝试：{stem}", flush=True)
        ok, msg, alive = _try_launch([exe, url], proc_name, stem, wait=wait, verify=verify)
        print("  " + msg, flush=True)
        if ok:
            return True, stem
        # 普通方式失败但进程还活着 → 可能是配置/实例问题，换独立配置再试
        if alive and stem in ("msedge", "chrome"):
            label = f"{stem} 独立配置"
            print(f"  正在尝试：{label}", flush=True)
            profile = GUI_DIR / ".profile"
            ok, msg, _alive = _try_launch(
                [exe, f"--user-data-dir={profile}", url], proc_name, label,
                wait=wait, verify=verify,
            )
            print("  " + msg, flush=True)
            if ok:
                return True, label

    # 兜底：交给系统默认程序
    base_hit = UI_HITS["last"]
    try:
        os.startfile(url)  # noqa: S606
        if verify:
            deadline = time.time() + 6
            while time.time() < deadline:
                time.sleep(0.25)
                if UI_HITS["last"] > base_hit:
                    print("  " + _log("[成功] 系统默认程序：页面已加载"), flush=True)
                    return True, "系统默认程序"
            print("  " + _log("[失败] 系统默认程序：没收到页面请求"), flush=True)
        else:
            print("  " + _log("[兜底] 已交给系统默认程序打开"), flush=True)
            return True, "系统默认程序"
    except Exception as exc:  # noqa: BLE001
        print("  " + _log(f"[失败] 系统默认程序：{exc}"), flush=True)
    return False, _log("[失败] 所有方式都没能打开浏览器")

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RESULT_RE = re.compile(r"^\[([+\-])\]\s*(?:\[(\d+)ms\])?\s*(.+?):\s?(.*)$")

# 常用站点（按存在性过滤，缺失的自动忽略）
POPULAR_CANDIDATES = [
    "GitHub", "Reddit", "Twitter", "Instagram", "HackerNews", "Bluesky",
    "TikTok", "Telegram", "Facebook", "Pinterest", "Twitch", "Medium",
    "DeviantArt", "SoundCloud", "Spotify", "Patreon", "Discord", "YouTube",
    "VK", "Weibo", "Bilibili", "Zhihu", "Steam Community (User)", "9GAG",
    "1337x", "About.me", "Archive.org", "Codeberg", "GitLab", "BitBucket",
    "Mastodon", "Tumblr", "Snapchat", "Flickr", "Strava", "Duolingo",
    "Chess", "Kaggle", "HackerRank", "LeetCode", "Behance", "Dribbble",
    "ProductHunt", "PyPi", "Npm", "Docker Hub", "Keybase", "Linktree",
    "Threads", "Truth Social",
]

# 中文名 + 一句话说明（只覆盖常见站点，其余显示域名）
CN = {
    "GitHub": ("GitHub", "全球最大的代码托管平台"),
    "GitLab": ("GitLab", "代码托管与 DevOps 平台"),
    "BitBucket": ("Bitbucket", "代码托管平台"),
    "Codeberg": ("Codeberg", "开源代码托管平台"),
    "Reddit": ("Reddit", "美国大型综合论坛"),
    "Twitter": ("X（推特）", "原 Twitter，短消息社交平台"),
    "Instagram": ("Instagram", "图片社交平台"),
    "Facebook": ("Facebook", "社交平台"),
    "Threads": ("Threads", "Meta 的微博客平台"),
    "TikTok": ("TikTok（抖音国际版）", "短视频平台"),
    "YouTube": ("YouTube", "视频平台"),
    "Twitch": ("Twitch", "游戏直播平台"),
    "Telegram": ("Telegram", "即时通讯软件"),
    "Discord": ("Discord", "语音与社群聊天平台"),
    "Bluesky": ("Bluesky", "去中心化微博客平台"),
    "Mastodon": ("Mastodon", "去中心化社交网络（长毛象）"),
    "Tumblr": ("Tumblr", "轻博客平台"),
    "Pinterest": ("Pinterest", "图片收藏与分享"),
    "Flickr": ("Flickr", "照片分享社区"),
    "Snapchat": ("Snapchat", "阅后即焚社交应用"),
    "VK": ("VK", "俄罗斯最大社交网络"),
    "Weibo": ("微博", "新浪微博"),
    "Bilibili": ("哔哩哔哩", "国内视频弹幕网站"),
    "Zhihu": ("知乎", "国内问答社区"),
    "HackerNews": ("Hacker News", "技术创业社区（Y Combinator）"),
    "Medium": ("Medium", "博客写作平台"),
    "DeviantArt": ("DeviantArt", "艺术作品社区"),
    "Behance": ("Behance", "设计作品集平台"),
    "Dribbble": ("Dribbble", "设计师作品社区"),
    "SoundCloud": ("SoundCloud", "音乐分享平台"),
    "Spotify": ("Spotify", "音乐流媒体"),
    "Patreon": ("Patreon", "创作者订阅平台"),
    "Strava": ("Strava", "运动健身社交"),
    "Duolingo": ("Duolingo", "语言学习应用"),
    "Chess": ("Chess.com", "国际象棋平台"),
    "Kaggle": ("Kaggle", "数据科学竞赛平台"),
    "HackerRank": ("HackerRank", "编程练习与招聘"),
    "LeetCode": ("LeetCode", "算法刷题平台"),
    "ProductHunt": ("Product Hunt", "新产品发布社区"),
    "PyPi": ("PyPI", "Python 包仓库"),
    "Npm": ("npm", "Node.js 包仓库"),
    "Docker Hub": ("Docker Hub", "容器镜像仓库"),
    "Keybase": ("Keybase", "加密身份与聊天"),
    "Linktree": ("Linktree", "个人链接聚合页"),
    "About.me": ("About.me", "个人主页服务"),
    "Archive.org": ("Internet Archive", "互联网档案馆"),
    "9GAG": ("9GAG", "搞笑图片社区"),
    "1337x": ("1337x", "资源索引站"),
    "Truth Social": ("Truth Social", "美国社交平台"),
    "Steam Community (User)": ("Steam 用户", "Steam 玩家个人主页"),
    "Steam Community (Group)": ("Steam 群组", "Steam 游戏群组"),
    "GitHub": ("GitHub", "全球最大的代码托管平台"),
}


def load_catalog() -> dict:
    """读取 data.json，生成站点目录。"""
    raw = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    sites = []
    for name, info in raw.items():
        if name.startswith("$"):
            continue
        cn_name, desc = CN.get(name, ("", ""))
        domain = ""
        try:
            from urllib.parse import urlparse

            domain = urlparse(info.get("urlMain", "")).netloc
        except Exception:
            pass
        sites.append(
            {
                "name": name,
                "cn": cn_name,
                "desc": desc,
                "domain": domain,
                "nsfw": bool(info.get("isNSFW")),
            }
        )
    sites.sort(key=lambda s: s["name"].lower())
    by_name = {s["name"]: s for s in sites}
    popular = [n for n in POPULAR_CANDIDATES if n in by_name]
    default_sites = [n for n in popular if not by_name[n]["nsfw"]][:12]
    return {"sites": sites, "popular": popular, "defaults": default_sites}


CATALOG = load_catalog()

def _default_out() -> Path:
    """报告默认目录：优先桌面，桌面不存在（被 OneDrive 重定向或精简系统）时退回用户目录。"""
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        return desktop / "Sherlock报告"
    onedrive = os.environ.get("OneDrive") or ""
    if onedrive:
        cand = Path(onedrive) / "Desktop"
        if cand.is_dir():
            return cand / "Sherlock报告"
    return Path.home() / "Sherlock报告"


DEFAULT_OUT = _default_out()

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def build_command(payload: dict) -> tuple[list[str], Path]:
    """把前端参数翻译成 sherlock 命令行。"""
    usernames = payload.get("usernames") or []
    sites = payload.get("sites") or []
    timeout = int(payload.get("timeout") or 20)
    outdir = Path(payload.get("outdir") or DEFAULT_OUT)
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = [str(PYTHON), "-u", "-m", "sherlock_project", *usernames]
    cmd += ["--print-all", "--no-color", "--verbose", "--timeout", str(timeout)]

    all_sites = len(CATALOG["sites"])
    if sites and len(sites) < all_sites:
        for s in sites:
            cmd += ["--site", s]
    if payload.get("nsfw"):
        cmd.append("--nsfw")
    if payload.get("proxy"):
        cmd += ["--proxy", str(payload["proxy"])]
    if payload.get("txt"):
        cmd.append("--txt")
    if payload.get("csv"):
        cmd.append("--csv")
    if payload.get("xlsx"):
        cmd.append("--xlsx")
    if payload.get("txt") or payload.get("csv") or payload.get("xlsx"):
        cmd += ["-fo", str(outdir)]
    return cmd, outdir


def run_job(job_id: str, cmd: list[str], outdir: Path, timeout_hint: int) -> None:
    """在后台线程里执行 sherlock，把每一行解析成事件推给前端。"""
    job = JOBS[job_id]
    q: queue.Queue = job["queue"]
    started = time.time()
    job["started_at"] = started
    try:
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONPATH"] = str(BASE)
        proc = subprocess.Popen(
            cmd,
            cwd=str(outdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
        )
        job["proc"] = proc
        current_user = (job.get("usernames") or ["?"])[0]
        last_line_at = time.time()

        assert proc.stdout is not None
        for raw in proc.stdout:
            line = ANSI_RE.sub("", raw.rstrip("\n"))
            if not line.strip():
                continue
            last_line_at = time.time()
            m = re.match(r"^\[\*\] Checking username (.+?) on:", line)
            if m:
                current_user = m.group(1)
                q.put({"type": "user", "user": current_user})
                continue
            if "Search completed with" in line:
                continue
            rm = RESULT_RE.match(line)
            if rm and line.startswith(("[+]", "[-]")):
                mark, ms, site, rest = rm.groups()
                if mark == "+":
                    status, url, detail = "claimed", rest.strip(), ""
                else:
                    text = rest.strip()
                    url, detail = "", text
                    if text == "Not Found!":
                        status = "available"
                    elif text.startswith("Illegal Username"):
                        status = "illegal"
                    elif text.startswith("Blocked by bot detection"):
                        status = "waf"
                    else:
                        status = "unknown"
                q.put(
                    {
                        "type": "result",
                        "user": current_user,
                        "site": site.strip(),
                        "status": status,
                        "url": url,
                        "detail": detail,
                        "ms": int(ms) if ms else None,
                    }
                )
                continue
            if "checking for an update" in line:
                continue
            q.put({"type": "log", "text": line})

        proc.wait()
        elapsed = time.time() - started
        files = []
        for pattern in ("*.txt", "*.csv", "*.xlsx"):
            for f in outdir.glob(pattern):
                try:
                    if f.stat().st_mtime >= started - 2:
                        files.append({"name": f.name, "path": str(f), "size": f.stat().st_size})
                except OSError:
                    pass
        files.sort(key=lambda x: x["name"])
        q.put(
            {
                "type": "done",
                "code": proc.returncode,
                "elapsed": round(elapsed, 1),
                "files": files,
                "outdir": str(outdir),
            }
        )
    except Exception as exc:  # noqa: BLE001
        q.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
        q.put({"type": "done", "code": -1, "elapsed": round(time.time() - started, 1), "files": [], "outdir": str(outdir)})
    finally:
        with JOBS_LOCK:
            JOBS[job_id]["finished"] = True


class Handler(BaseHTTPRequestHandler):
    server_version = "SherlockGUI/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 安静一点，只记错误
        if args and str(args[1]).startswith(("4", "5")):
            sys.stderr.write("[gui] " + (fmt % args) + "\n")

    # ---------- 工具 ----------
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    # ---------- 路由 ----------
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            UI_HITS["last"] = time.time()
            html = (GUI_DIR / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(html)
        elif path == "/api/sites":
            self._json({**CATALOG, "default_out": str(DEFAULT_OUT)})
        elif path == "/api/events":
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            job_id = qs.split("id=")[1].split("&")[0] if "id=" in qs else ""
            self.stream_events(job_id)
        elif path == "/api/health":
            self._json({"ok": True, "python": str(PYTHON), "sites": len(CATALOG["sites"])})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            payload = self._body()
        except Exception:
            self._json({"error": "bad json"}, 400)
            return

        if path == "/api/run":
            usernames = [u.strip() for u in payload.get("usernames") or [] if u.strip()]
            if not usernames:
                self._json({"error": "请先填写用户名"}, 400)
                return
            cmd, outdir = build_command({**payload, "usernames": usernames})
            job_id = uuid.uuid4().hex[:12]
            with JOBS_LOCK:
                JOBS[job_id] = {
                    "queue": queue.Queue(),
                    "proc": None,
                    "usernames": usernames,
                    "cmd": cmd,
                    "outdir": outdir,
                    "finished": False,
                }
            threading.Thread(target=run_job, args=(job_id, cmd, outdir, 0), daemon=True).start()
            self._json({"id": job_id, "cmd": cmd, "outdir": str(outdir)})

        elif path == "/api/stop":
            job = JOBS.get(payload.get("id") or "")
            if job and job.get("proc"):
                try:
                    job["proc"].kill()
                except Exception:
                    pass
                self._json({"ok": True})
            else:
                self._json({"ok": False}, 404)

        elif path == "/api/open":
            target = Path(payload.get("path") or DEFAULT_OUT)
            try:
                if not target.exists():
                    target.mkdir(parents=True, exist_ok=True)
                os.startfile(str(target))  # noqa: S606
                self._json({"ok": True})
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, 500)

        else:
            self._json({"error": "not found"}, 404)

    # ---------- 服务器推送 ----------
    def stream_events(self, job_id: str):
        job = JOBS.get(job_id)
        if not job:
            self._json({"error": "任务不存在"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        q: queue.Queue = job["queue"]
        try:
            while True:
                try:
                    event = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                data = json.dumps(event, ensure_ascii=False)
                self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                self.wfile.flush()
                if event.get("type") in ("done", "error"):
                    break
        except (BrokenPipeError, ConnectionResetError):
            pass


def main():
    if not (BASE / "sherlock_project").is_dir():
        print("[错误] 没找到 sherlock_project 目录。")
        print(f"       请把 gui\\ 放在 sherlock 仓库根目录下（当前：{BASE}）")
        sys.exit(1)
    url = f"http://{HOST}:{PORT}/"

    # 已经在运行：直接打开浏览器，避免端口冲突
    import socket

    with socket.socket() as s:
        s.settimeout(0.6)
        if s.connect_ex((HOST, PORT)) == 0:
            print("界面已经在运行，正在打开浏览器…")
            ok, how = open_ui(url, verify=False)
            if ok:
                print(f"  已用 {how} 打开：{url}")
                time.sleep(1.5)
            else:
                print(f"  没能自动打开浏览器，请手动访问：{url}")
                copy_url(url)
                input("按回车键关闭窗口…")
            return

    print("=" * 52)
    print(f"  Sherlock 中文查询界面 v{VERSION}")
    print("=" * 52)
    print(f"  地址：{url}")
    print(f"  站点：{len(CATALOG['sites'])} 个")
    print("  关闭这个黑色窗口即退出程序")
    print("=" * 52)

    def _open_later():
        ok, how = open_ui(url)
        if ok:
            print(f"  已在 {how} 中打开界面")
            print("  （如果浏览器窗口没跳到最前面，看一下任务栏）")
        else:
            print("  [!] 没能自动打开浏览器")
            print(f"      请手动打开浏览器，在地址栏输入：{url}")
            if copy_url(url):
                print("      （地址已复制到剪贴板，可直接粘贴）")
        sys.stdout.flush()

    if not os.environ.get("SHERLOCK_NO_BROWSER"):
        threading.Timer(0.8, _open_later).start()
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
