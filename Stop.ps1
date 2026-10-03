# 只停止启动记录对应的进程树；核对创建时间，防止 PID 被其他程序复用。
$ErrorActionPreference = 'Stop'
foreach ($serviceName in @('backend', 'frontend')) {
    $pidFile = Join-Path $PSScriptRoot "logs\$serviceName.pid"
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $record = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
    $process = Get-Process -Id $record.ProcessId -ErrorAction SilentlyContinue
    if (-not $process) {
        Remove-Item -LiteralPath $pidFile
        Write-Host "$serviceName 原进程已退出。"
        continue
    }
    if ($process.StartTime.ToUniversalTime().Ticks.ToString() -ne $record.StartedAt -or $process.Path -ne $record.Executable) {
        throw "$serviceName 的 PID 已被其他程序复用，未执行停止。"
    }
    # Windows 虚拟环境的 Python 启动器会创建子进程，因此停止已验证的整个进程树。
    & taskkill.exe /PID $record.ProcessId /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$serviceName 停止失败。" }
    Remove-Item -LiteralPath $pidFile
    Write-Host "$serviceName 已停止。"
}
