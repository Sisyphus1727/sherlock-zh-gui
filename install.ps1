# 把中文界面装入已克隆的 sherlock 仓库
#
# 示例：
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Target D:\tools\sherlock
#   powershell -ExecutionPolicy Bypass -File .\install.ps1 -Target D:\tools\sherlock -SetupVenv
#
# 只复制文件、不修改上游任何源码；重复执行是安全的（覆盖同名文件）。

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "sherlock 仓库根目录")]
    [string]$Target,

    [switch]$SetupVenv,

    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path -LiteralPath $Target -PathType Container)) {
    throw "目标目录不存在：$Target"
}
$Target = (Resolve-Path -LiteralPath $Target).Path

if (-not (Test-Path -LiteralPath (Join-Path $Target "sherlock_project") -PathType Container)) {
    throw "目标目录里没有 sherlock_project，看起来不是 sherlock 仓库根目录：$Target"
}

Write-Host "目标：$Target" -ForegroundColor Cyan

# 1) gui/
$guiSrc = Join-Path $here "gui"
$guiDst = Join-Path $Target "gui"
New-Item -ItemType Directory -Force -Path $guiDst | Out-Null
foreach ($name in @("server.py", "index.html", ".gitignore")) {
    $src = Join-Path $guiSrc $name
    if (Test-Path -LiteralPath $src -PathType Leaf) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $guiDst $name) -Force
        Write-Host "  已复制 gui\$name"
    }
}

# 2) 启动器
foreach ($name in @("启动图形界面.cmd", "打开网页.cmd", "sherlock.cmd")) {
    Copy-Item -LiteralPath (Join-Path $here $name) -Destination (Join-Path $Target $name) -Force
    Write-Host "  已复制 $name"
}

# 3) 可选：虚拟环境 + 依赖
if ($SetupVenv) {
    $venv = Join-Path $Target ".venv"
    $venvPy = Join-Path $venv "Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPy -PathType Leaf) {
        Write-Host "  已存在 .venv，跳过创建"
    }
    else {
        Write-Host "  创建虚拟环境：$venv"
        & $Python -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw "创建虚拟环境失败（请确认 $Python 可用）" }
    }

    Write-Host "  安装依赖…"
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r (Join-Path $here "requirements.txt")
    if ($LASTEXITCODE -ne 0) { throw "依赖安装失败，可尝试先注释 requirements.txt 里的 stem 后重试" }
}

Write-Host ""
Write-Host "完成。双击这个文件启动界面：" -ForegroundColor Green
Write-Host "  $(Join-Path $Target '启动图形界面.cmd')"
Write-Host "浏览器地址：http://127.0.0.1:8766/"
Write-Host ""
Write-Host "提示：个别机器上需要「以管理员身份运行」启动脚本，浏览器才允许被自动拉起。"
