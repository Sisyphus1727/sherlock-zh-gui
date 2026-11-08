# Sherlock 中文图形界面（sherlock-zh-gui）

给 [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) 套一层**全中文的本地网页界面**：双击一个脚本，浏览器里填用户名、勾网站、点开始，结果一行行实时出现，自动导出 TXT / CSV / Excel 报告。

面向不想记命令行参数的人——尤其是看不惯英文输出的用户。

- **不修改上游一行代码**：本项目只**新增**文件（一个 `gui/` 目录 + 几个 `.cmd` 启动器），上游仓库保持原样，可随时 `git pull` 升级。
- **零额外依赖**：`gui/server.py` 只用 Python 标准库；依赖只有上游 Sherlock 自己的那几个。
- **纯本地**：服务只监听 `127.0.0.1`，不联网上传任何东西，没有遥测。

> 本项目是第三方附加组件，**与上游 Sherlock 项目无隶属关系**，也未获其官方背书。上游许可见 [LICENSE](LICENSE) 与 [NOTICE.md](NOTICE.md)。

---

## 1. 溯源信息

| 项目 | 说明 |
|---|---|
| 上游项目 | [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) |
| 本项目基于的上游版本 | **v0.16.2** |
| 上游 commit | `c588d7c8b476df9f9c84912a05d1430fb8cdcdae`（2026-11-01，"update banner layout"） |
| 上游许可证 | MIT（Copyright © 2019 Sherlock Project） |
| 上游站点数 | 481（`sherlock_project/resources/data.json`，未计入 `$schema` 元键） |
| 本项目的改动 | **仅新增文件，未修改上游任何源码**（详见第 2 节） |
| 本项目许可证 | MIT |

**验证「上游零修改」**：把本项目文件放进你的 sherlock 克隆后，在克隆目录执行

```bash
git status --porcelain
```

输出应全部是 `??`（未跟踪的新文件），没有 ` M` / `M `（已修改的既有文件）。本项目所有产物都是新增文件，因此能干净地溯源到上游对应版本。

---

## 2. 修改说明（相对上游新增了什么）

新增文件清单：

| 文件 | 作用 |
|---|---|
| `gui/server.py` | 本地 Web 服务（Python 标准库 `http.server`），提供页面、站点目录、SSE 实时结果流、启动/停止查询、打开报告目录 |
| `gui/index.html` | 全中文单页界面（原生 JS + `EventSource`，无框架、无 CDN） |
| `启动图形界面.cmd` | 双击入口：设置 `PYTHONPATH` 后启动上面的服务，并自动打开浏览器 |
| `打开网页.cmd` | 不经 Python，直接用 Chrome / Edge 打开 `http://127.0.0.1:8766/` |
| `sherlock.cmd` | 命令行入口，等价于 `python -m sherlock_project`，但不切换工作目录（保证 `--txt/--csv/--xlsx` 输出在**你当前所在目录**） |
| `install.ps1` | 把以上文件装进已有的 sherlock 克隆（可选顺带建虚拟环境、装依赖） |
| `requirements.txt` | 上游 `pyproject.toml` 的运行依赖，带可用的版本区间 |
| `docs/使用教程.md` | 中文使用教程（图形界面 + 全部命令行参数 + 实战示例） |
| `docs/排错.md` | 常见问题：浏览器没弹出、端口占用、站点名写错、结果异常 |

**没有做的事**（避免误导）：没有 fork 上游、没有改上游代码、没有重新打包上游的发行版。你和上游的关系仍然是一次普通的 `git clone`，本项目只是叠加在上面的「外壳」。

---

## 3. 环境要求

- Windows 10 / 11
- Python **3.9+**（建议 3.10 ~ 3.12）
- Chrome / Edge / Firefox 任一（用于显示界面）
- 能访问目标站点（部分站点需要代理，可用界面里的「代理」选项）

> `gui/server.py` 本身是跨平台的，但启动器与自动打开浏览器逻辑按 Windows 编写，Linux / macOS 未做测试。

---

## 4. 安装

### 4.1 准备上游

```bash
git clone https://github.com/sherlock-project/sherlock.git
cd sherlock
```

（国内网络如果 `github.com` 拉不动，可换用你常用的镜像，把克隆出来的目录当成本项目的 `-Target`。）

### 4.2 装入中文界面

在本项目目录执行：

```powershell
# 只复制界面文件（推荐：依赖自己管理）
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Target D:\tools\sherlock

# 顺便建虚拟环境并装依赖
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Target D:\tools\sherlock -SetupVenv
```

`-SetupVenv` 会执行 `python -m venv .venv` + `pip install -r requirements.txt`。

### 4.3 或者手动复制（等价）

把下面这些**复制到 sherlock 克隆的根目录**：

```
gui\               →  <sherlock>\gui\
启动图形界面.cmd    →  <sherlock>\
打开网页.cmd        →  <sherlock>\
sherlock.cmd        →  <sherlock>\
```

然后装依赖：

```powershell
cd D:\tools\sherlock
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

> 没有 `.venv` 也能跑：`gui/server.py` 会自动退回当前解释器。但依赖必须已经装在这个解释器里。

---

## 5. 使用

**双击 `启动图形界面.cmd`**。会开一个黑色窗口（服务本体，别关）并自动打开浏览器 `http://127.0.0.1:8766/`。

界面四步：

1. **填用户名** —— 一个或多个，空格/逗号分隔。
2. **选网站** —— 默认 12 个主流平台（约 10 秒）；可切「全部站点」（481 个）或「自定义」勾选。
3. **点「开始查询」** —— 进度条、计时器、结果实时出现，可随时「停止」。
4. **看结果 / 拿报告** —— 每行有网站中文名、状态、主页链接、耗时；报告自动存到 **`桌面\Sherlock报告`**（TXT + CSV，可选 Excel）。

状态含义：

| 状态 | 含义 |
|---|---|
| 已注册 | 该站存在此用户名，链接即个人主页 |
| 未注册 | 该站没有此用户名 |
| 不支持此用户名 | 站点对用户名格式有限制（如不允许点号） |
| 被网站拦截 | 对方有反爬（Cloudflare 等），本次没查到 |
| 查询失败 | 超时或对方异常，**不代表账号不存在** |

**关闭黑窗口 = 退出程序**，页面随之失效。

命令行用法见 [docs/使用教程.md](docs/使用教程.md)（含全部参数、`{?}` 通配、多用户批量、导出格式细节）。

---

## 6. 环境变量

| 变量 | 作用 |
|---|---|
| `SHERLOCK_GUI_PORT` | 改监听端口（默认 `8766`） |
| `SHERLOCK_BROWSER` | 指定浏览器 exe 的完整路径，优先于内置候选列表 |
| `SHERLOCK_NO_BROWSER` | 设成任意值则不自动打开浏览器（适合脚本/远程环境） |

---

## 7. 已知现象与排错

完整版见 [docs/排错.md](docs/排错.md)。几个最常遇到的：

- **浏览器没自动弹出**：程序按 Chrome → Edge → Firefox 顺序尝试，并且只有**真的收到页面请求**才算成功（黑窗口与 `gui\启动日志.txt` 会逐条写结果）。全部失败时地址已复制到剪贴板，手动粘贴即可。个别机器上需要**以管理员身份运行**启动脚本，浏览器才允许被拉起。
- **Edge 启动即退出**：少数环境下 `msedge.exe` 起不来（进程 0→0），所以 Chrome 排在前面。
- **启动时一行 `A problem occurred while checking for an update: ...`**：上游在查 GitHub 最新版本，网络不通就会报。**无害**。
- **GitHub 站点查不到**：上游对 GitHub 的检测常被 403/限流，不是用错。
- **结果多到离谱**：不少站点对任意用户名都返回 200，属上游已知误报；用 `--site` 缩小范围并人工核对。

---

## 8. 隐私与合规

- 服务只监听 `127.0.0.1`，不对局域网/公网开放；界面无第三方统计、无外链字体与脚本。
- 查询结果是公开网页信息；请**仅用于合法用途**（自查、授权范围内的品牌/账号核查等），并遵守目标网站的服务条款与当地法律。
- 上游项目本身也声明仅用于教育与合法的信息核查，详见其仓库。

---

## 9. 许可证

MIT。本项目部分：Copyright © 2026 sherlock-zh-gui contributors；上游部分：Copyright © 2019 Sherlock Project。

完整文本见 [LICENSE](LICENSE)，归属与修改声明见 [NOTICE.md](NOTICE.md)。

## 10. 致谢

- [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) —— 全部检测能力来自上游，本项目只负责界面与包装。
- 上游站点清单的维护者们。
