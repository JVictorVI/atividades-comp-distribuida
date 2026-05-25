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

function Test-PositiveIntList {
    param([string]$Value)

    $items = @($Value -split "," | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($items.Count -eq 0) {
        throw "Informe ao menos uma carga em UserCounts. Exemplo: -UserCounts 50,250,500"
    }

    foreach ($item in $items) {
        $parsed = 0
        if (-not [int]::TryParse($item, [ref]$parsed) -or $parsed -le 0) {
            throw "Valor invalido em UserCounts: '$item'. Use apenas inteiros positivos separados por virgula."
        }
    }
}

function Invoke-DockerCompose {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    & docker compose @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao executar: docker compose $($Arguments -join ' ')"
    }
}

function Get-ContainerId {
    param([Parameter(Mandatory = $true)][string]$Service)

    $id = & docker compose ps -q $Service
    if ($LASTEXITCODE -ne 0 -or -not $id) {
        throw "Container do servico '$Service' nao encontrado."
    }

    return @($id)[0]
}

function Get-ContainerHealth {
    param([Parameter(Mandatory = $true)][string]$ContainerId)

    $status = & docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" $ContainerId
    if ($LASTEXITCODE -ne 0 -or -not $status) {
        return "unknown"
    }

    return (@($status)[0]).Trim()
}

function Wait-ServicesHealthy {
    param(
        [Parameter(Mandatory = $true)][string[]]$Services,
        [Parameter(Mandatory = $true)][int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)

    while ((Get-Date) -lt $deadline) {
        $pending = @()

        foreach ($service in $Services) {
            $containerId = Get-ContainerId -Service $service
            $status = Get-ContainerHealth -ContainerId $containerId

            if ($status -ne "healthy" -and $status -ne "running") {
                $pending += "$service=$status"
            }
        }

        if ($pending.Count -eq 0) {
            Write-Host "Servicos prontos: $($Services -join ', ')"
            return
        }

        Write-Host "Aguardando servicos: $($pending -join ', ')"
        Start-Sleep -Seconds 3
    }

    Invoke-DockerCompose -Arguments @("ps")
    throw "Tempo limite atingido aguardando os servicos ficarem saudaveis."
}

if ($SpawnRate -le 0) {
    throw "SpawnRate deve ser maior que zero."
}

Test-PositiveIntList -Value $UserCounts

$env:LOCUST_DURATION = $Duration
$env:LOCUST_SPAWN_RATE = [string]$SpawnRate
$env:LOCUST_USER_COUNTS = $UserCounts

Write-Host "Configuracao dos testes:"
Write-Host "  Duracao: $env:LOCUST_DURATION"
Write-Host "  Spawn rate: $env:LOCUST_SPAWN_RATE"
Write-Host "  Cargas: $env:LOCUST_USER_COUNTS"

try {
    & docker --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker nao encontrado."
    }

    if (-not $NoBuild) {
        Write-Host "Construindo imagem Docker..."
        Invoke-DockerCompose -Arguments @("build")
    }

    Write-Host "Subindo APIs..."
    Invoke-DockerCompose -Arguments @("up", "-d", "rest", "graphql", "soap", "grpc")
    Wait-ServicesHealthy -Services @("rest", "graphql", "soap", "grpc") -TimeoutSeconds $HealthTimeoutSeconds

    Write-Host "Executando cenarios Locust sem interface..."
    Invoke-DockerCompose -Arguments @("--profile", "scenarios", "run", "--rm", "locust-scenarios")

    Write-Host "Gerando graficos..."
    Invoke-DockerCompose -Arguments @("--profile", "charts", "run", "--rm", "charts")

    Write-Host "Fluxo concluido. Resultados em: $ProjectRoot\results"
    Write-Host "Graficos em: $ProjectRoot\results\charts"
}
finally {
    if ($KeepServices) {
        Write-Host "Containers mantidos ativos por causa de -KeepServices."
    }
    else {
        Write-Host "Encerrando containers..."
        & docker compose down --remove-orphans
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Nao foi possivel encerrar todos os containers automaticamente."
        }
    }
}
