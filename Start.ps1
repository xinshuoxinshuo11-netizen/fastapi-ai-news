# 启动本目录的前后端，模型密钥只从当前进程、用户或系统环境读取。
$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$logDir = Join-Path $projectDir 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
function Test-LocalPort([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $operation = $client.ConnectAsync('127.0.0.1', $Port)
        return ($operation.Wait(500) -and $client.Connected)
    } catch { return $false } finally { $client.Dispose() }
}
foreach ($variableName in @('DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY', 'QWEN_API_KEY')) {
    if (-not [Environment]::GetEnvironmentVariable($variableName, 'Process')) {
        $configuredValue = [Environment]::GetEnvironmentVariable($variableName, 'User')
        if (-not $configuredValue) { $configuredValue = [Environment]::GetEnvironmentVariable($variableName, 'Machine') }
        if ($configuredValue) { [Environment]::SetEnvironmentVariable($variableName, $configuredValue, 'Process') }
    }
}
$services = @(
    @{ Name = 'backend'; Port = 19000; Exe = (Join-Path $projectDir '.venv\Scripts\python.exe'); Args = @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '19000'); Dir = $projectDir },
    @{ Name = 'frontend'; Port = 5176; Exe = (Get-Command node.exe).Source; Args = @('node_modules/vite/bin/vite.js'); Dir = (Join-Path $projectDir 'frontend') }
)
foreach ($service in $services) {
    $pidFile = Join-Path $logDir "$($service.Name).pid"
    if (Test-LocalPort $service.Port) {
        $alreadyRunning = $false
        if (Test-Path -LiteralPath $pidFile) {
            try {
                $record = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
                $tracked = Get-Process -Id $record.ProcessId -ErrorAction Stop
                $alreadyRunning = ($tracked.StartTime.ToUniversalTime().Ticks.ToString() -eq $record.StartedAt -and $tracked.Path -eq $record.Executable)
            } catch { }
        }
        if ($alreadyRunning) { Write-Host "$($service.Name) 已在运行，跳过重复启动。"; continue }
        throw "端口 $($service.Port) 已被其他进程占用，请先确认占用来源。"
    }
    $process = Start-Process -FilePath $service.Exe -ArgumentList $service.Args -WorkingDirectory $service.Dir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir "$($service.Name).out.log") -RedirectStandardError (Join-Path $logDir "$($service.Name).err.log")
    @{ ProcessId = $process.Id; StartedAt = $process.StartTime.ToUniversalTime().Ticks.ToString(); Executable = $service.Exe } | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding UTF8
    $ready = $false
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        if (Test-LocalPort $service.Port) { $ready = $true; break }
        $process.Refresh()
        if ($process.HasExited) { break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $ready) { throw "$($service.Name) 启动失败，请查看 logs/$($service.Name).err.log。" }
    Write-Host "$($service.Name) 已就绪，进程 ID：$($process.Id)"
}
Write-Host '首页：http://127.0.0.1:5176  接口文档：http://127.0.0.1:19000/docs'
