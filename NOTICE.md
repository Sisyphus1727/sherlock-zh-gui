# NOTICE —— 归属、溯源与修改声明

本项目（`sherlock-zh-gui`）是第三方附加组件，为下列上游项目提供一个中文网页界面。

## 上游项目

| 项 | 内容 |
|---|---|
| 名称 | Sherlock |
| 仓库 | https://github.com/sherlock-project/sherlock |
| 版本 | v0.16.2 |
| commit | `c588d7c8b476df9f9c84912a05d1430fb8cdcdae` |
| 发布日期 | 2026-11-01 |
| 许可证 | MIT License，Copyright (c) 2019 Sherlock Project |
| 官网/文档 | https://sherlockproject.xyz/ |

上游的全部检测逻辑、站点清单（`sherlock_project/resources/data.json`，本项目基于的版本为 481 个站点）、命令行接口均归上游作者所有。

## 本项目的性质

- **叠加式外壳**，不是 fork：不复制上游源码，只在其仓库根目录新增 `gui/` 与若干 `.cmd`。
- 上游代码**零修改**。可用下面命令复核：在合并后的 sherlock 目录执行 `git status --porcelain`，输出应全部为 `??`（新增文件），不存在 `M`（被修改的既有文件）。
- 本项目不重新分发上游代码。使用者需自行从上游仓库克隆。

## 修改与新增清单（相对上游 v0.16.2）

新增（均为本项目原创）：

```
gui/server.py            本地 HTTP/SSE 服务
gui/index.html           中文单页界面
gui/.gitignore
启动图形界面.cmd          双击启动器
打开网页.cmd              直接调用浏览器打开界面
sherlock.cmd              命令行启动器（不改变工作目录）
install.ps1               安装脚本
requirements.txt          上游运行依赖
README.md / NOTICE.md / LICENSE / CHANGELOG.md
docs/使用教程.md
docs/排错.md
```

修改上游文件：**无**。

## 兼容性提示

上游升级后，若命令行输出格式（`[+] 站点: url`、`[-] 站点: Not Found!`、`Search completed with N results`）或 `data.json` 结构发生变化，界面侧的解析可能需要同步调整，见 `gui/server.py` 中的 `RESULT_RE` 与 `load_catalog()`。

## 商标与免责

"Sherlock" 名称与相关标识归上游项目所有。本项目使用该名称仅用于说明兼容对象，不代表任何官方关系、赞助或背书。本项目按 MIT 许可「按原样」提供，不附带任何担保；使用者需自行确保使用方式合法合规。

## 上游许可证原文（MIT）

```
MIT License

Copyright (c) 2019 Sherlock Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
