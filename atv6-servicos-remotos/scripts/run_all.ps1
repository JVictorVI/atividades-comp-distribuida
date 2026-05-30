[CmdletBinding()]
param(
    [string]$Duration = $(if ($env:LOCUST_DURATION) { $env:LOCUST_DURATION } else { "2m" }),
    [int]$SpawnRate = $(if ($env:LOCUST_SPAWN_RATE) { [int]$env:LOCUST_SPAWN_RATE } else { 10 }),
    [string]$UserCounts = $(if ($env:LOCUST_USER_COUNTS) { $env:LOCUST_USER_COUNTS } else { "50,250,500" }),
    [int]$HealthTimeoutSeconds = 120,
    [switch]$NoBuild,
    [switch]$KeepServices
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$RunPython = Join-Path $PSScriptRoot "run_python.ps1"
$RunJavaScript = Join-Path $PSScriptRoot "run_javascript.ps1"

try {
    & docker --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker nao encontrado."
    }

    if (-not $NoBuild) {
        Write-Host "Construindo imagens Python e JavaScript..."
        & docker compose build rest-python rest-js
        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao construir as imagens."
        }
    }

    Write-Host "Rodando bateria Python..."
    & $RunPython `
        -Duration $Duration `
        -SpawnRate $SpawnRate `
        -UserCounts $UserCounts `
        -HealthTimeoutSeconds $HealthTimeoutSeconds `
        -NoBuild `
        -KeepServices:$KeepServices
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao rodar a bateria Python."
    }

    Write-Host "Rodando bateria JavaScript..."
    & $RunJavaScript `
        -Duration $Duration `
        -SpawnRate $SpawnRate `
        -UserCounts $UserCounts `
        -HealthTimeoutSeconds $HealthTimeoutSeconds `
        -NoBuild `
        -KeepServices:$KeepServices
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao rodar a bateria JavaScript."
    }

    Write-Host "Gerando grafico comparativo Python x JavaScript..."
    & docker compose --profile combined-charts run --rm --no-deps `
        -e "LOCUST_RESULTS_DIR=" `
        -e "LOCUST_CHARTS_DIR=/app/results/charts" `
        charts-combined
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao gerar o grafico comparativo."
    }

    Write-Host "Fluxo completo concluido."
    Write-Host "Resultados Python: $ProjectRoot\results\python"
    Write-Host "Resultados JavaScript: $ProjectRoot\results\javascript"
    Write-Host "Graficos: $ProjectRoot\results\charts"
}
finally {
    if ($KeepServices) {
        Write-Host "Containers mantidos ativos por causa de -KeepServices."
    }
}
