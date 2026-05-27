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

$ApiServices = @("rest-js", "graphql-js", "soap-js", "grpc-js")

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
            Write-Host "Servicos JavaScript prontos: $($Services -join ', ')"
            return
        }

        Write-Host "Aguardando servicos JavaScript: $($pending -join ', ')"
        Start-Sleep -Seconds 3
    }

    Invoke-DockerCompose -Arguments @("ps")
    throw "Tempo limite atingido aguardando os servicos JavaScript ficarem saudaveis."
}

function Stop-ApiServices {
    param([string[]]$Services)

    & docker compose stop @Services | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Nao foi possivel parar todos os containers JavaScript automaticamente."
    }

    & docker compose rm -f @Services | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Nao foi possivel remover todos os containers JavaScript automaticamente."
    }
}

if ($SpawnRate -le 0) {
    throw "SpawnRate deve ser maior que zero."
}

Test-PositiveIntList -Value $UserCounts

$env:LOCUST_DURATION = $Duration
$env:LOCUST_SPAWN_RATE = [string]$SpawnRate
$env:LOCUST_USER_COUNTS = $UserCounts

Write-Host "Configuracao dos testes JavaScript:"
Write-Host "  Duracao: $env:LOCUST_DURATION"
Write-Host "  Spawn rate: $env:LOCUST_SPAWN_RATE"
Write-Host "  Cargas: $env:LOCUST_USER_COUNTS"

try {
    & docker --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker nao encontrado."
    }

    if (-not $NoBuild) {
        Write-Host "Construindo imagens JavaScript e Locust..."
        Invoke-DockerCompose -Arguments @("build", "rest-js", "rest-python")
    }

    Write-Host "Subindo APIs JavaScript..."
    Invoke-DockerCompose -Arguments (@("up", "-d") + $ApiServices)
    Wait-ServicesHealthy -Services $ApiServices -TimeoutSeconds $HealthTimeoutSeconds

    Write-Host "Executando cenarios Locust contra JavaScript..."
    Invoke-DockerCompose -Arguments @("--profile", "js-scenarios", "run", "--rm", "locust-js")

    Write-Host "Gerando graficos JavaScript..."
    Invoke-DockerCompose -Arguments @("--profile", "js-charts", "run", "--rm", "charts-js")

    Write-Host "Fluxo JavaScript concluido. Resultados em: $ProjectRoot\results\javascript"
    Write-Host "Graficos em: $ProjectRoot\results\javascript\charts"
}
finally {
    if ($KeepServices) {
        Write-Host "Containers JavaScript mantidos ativos por causa de -KeepServices."
    }
    else {
        Write-Host "Encerrando containers JavaScript..."
        Stop-ApiServices -Services $ApiServices
    }
}
