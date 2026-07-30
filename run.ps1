<#
.SYNOPSIS
  Start, stop and inspect the Argus container.

.DESCRIPTION
  Every component (Ollama, the Gemma model, the reasoning loop and the Flask
  dashboard) runs inside one resource-capped container, so the caps constrain
  inference itself rather than just the app code. The defaults below are the values
  the project was developed and measured against - see docker/resource_caps.md.

.EXAMPLE
  .\run.ps1                     # start (or restart) and open the dashboard
  .\run.ps1 status              # RAM / CPU / tokens-per-sec / recent observations
  .\run.ps1 logs                # follow container output
  .\run.ps1 stop                # remove the container
  .\run.ps1 build               # rebuild the image (slow: pulls the model)
  .\run.ps1 start -Clip demo\clips\other.mp4 -NoOpen
#>

[CmdletBinding()]
param(
    [ValidateSet("start", "stop", "restart", "status", "logs", "build")]
    [string]$Action = "start",

    # Clip to reason about, relative to the repo root.
    [string]$Clip = "demo\clips\porch_theft.mp4",

    # Seconds of footage skipped per sample. Tune to clip length: too large and the
    # subject crosses the scene between samples, so no motion is observable.
    [double]$ClipAdvance = 0.75,

    # Wall-clock floor between samples. Kept above measured inference time so the
    # device genuinely idles between samples rather than pegging the CPU.
    [double]$Interval = 5,

    # Longest frame edge sent to the model. Above ~2.6MP Gemma 4's vision encoder
    # exceeds the memory cap and the model process is OOM-killed.
    [int]$MaxFrameDim = 1024,

    [string]$Memory = "6g",
    [string]$MemorySwap = "12g",
    [int]$Cpus = 4,
    [int]$Port = 5000,
    [int]$OllamaPort = 11435,
    [string]$Image = "argus:clean",
    [string]$Name = "argus",

    [switch]$NoOpen
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Url = "http://localhost:$Port"

function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw "docker not found on PATH. Install Docker Desktop and reopen the terminal."
    }
    docker info 2>&1 | Out-Null
    if (-not $?) { throw "Docker is installed but not running. Start Docker Desktop first." }
}

function Test-Image {
    $found = docker images -q $Image
    if (-not $found) {
        throw "Image '$Image' not found. Build it first:  .\run.ps1 build"
    }
}

function Remove-Container {
    docker rm -f $Name 2>&1 | Out-Null
}

function Start-Argus {
    Test-Docker
    Test-Image

    $clipPath = Join-Path $Root $Clip
    if (-not (Test-Path $clipPath)) {
        throw "Clip not found: $clipPath`nPut a video in demo\clips\ or pass -Clip <path>."
    }
    # The container sees the repo's demo/ at /app/demo, so the host path has to be
    # translated rather than passed through.
    $clipInContainer = "/app/demo/" + ($Clip -replace '^demo[\\/]', '' -replace '\\', '/')

    Remove-Container
    Write-Host "Starting $Name ($Memory RAM, $Cpus CPUs) on $Clip ..." -ForegroundColor Cyan

    docker run -d --name $Name `
        --memory=$Memory --memory-swap=$MemorySwap --cpus=$Cpus `
        -p "${Port}:5000" -p "${OllamaPort}:11434" `
        -v "$Root\src:/app/src" `
        -v "$Root\demo:/app/demo" `
        -v "$Root\config:/app/config" `
        -v "$Root\scripts:/app/scripts" `
        -e SOURCE_KIND=file `
        -e FRAME_SOURCE="$clipInContainer" `
        -e CLIP_ADVANCE_SECONDS=$ClipAdvance `
        -e SAMPLE_INTERVAL_SECONDS=$Interval `
        -e MAX_FRAME_DIM=$MaxFrameDim `
        $Image | Out-Null
    if (-not $?) { throw "docker run failed." }

    # The model has to load into memory before the first request will succeed, so
    # poll the dashboard rather than reporting success the instant the container exists.
    Write-Host -NoNewline "Waiting for the dashboard"
    foreach ($i in 1..40) {
        Start-Sleep -Seconds 2
        try {
            Invoke-WebRequest "$Url/api/config" -UseBasicParsing -TimeoutSec 2 | Out-Null
            Write-Host ""
            Write-Host "Ready: $Url" -ForegroundColor Green
            Write-Host "First observation takes ~1-2 min (CPU-only multimodal inference)."
            if (-not $NoOpen) { Start-Process $Url }
            return
        } catch { Write-Host -NoNewline "." }
    }
    Write-Host ""
    Write-Warning "Dashboard did not respond in 80s. Check:  .\run.ps1 logs"
}

switch ($Action) {
    "start"   { Start-Argus }
    "restart" { Start-Argus }
    "stop"    { Test-Docker; Remove-Container; Write-Host "Stopped and removed '$Name'." }
    "status"  {
        $py = Join-Path $Root ".venv\Scripts\python.exe"
        if (-not (Test-Path $py)) { $py = "python" }
        & $py (Join-Path $Root "scripts\status.py")
    }
    "logs"    { Test-Docker; docker logs -f $Name }
    "build"   {
        Test-Docker
        Write-Host "Building $Image (pulls the Gemma model - expect 15+ min)..." -ForegroundColor Cyan
        docker build -t $Image -f (Join-Path $Root "docker\Dockerfile") $Root
        if (-not $?) { throw "docker build failed." }
        Write-Host "Built $Image." -ForegroundColor Green
    }
}
