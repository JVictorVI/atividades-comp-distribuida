[CmdletBinding()]
param(
    [string]$Duration = $(if ($env:LOCUST_DURATION) { $env:LOCUST_DURATION } else { "2m" }),
    [int]$SpawnRate = $(if ($env:LOCUST_SPAWN_RATE) { [int]$env:LOCUST_SPAWN_RATE } else { 10 }),
    [string]$UserCounts = $(if ($env:LOCUST_USER_COUNTS) { $env:LOCUST_USER_COUNTS } else { "50,250,500" }),
    [int]$HealthTimeoutSeconds = 120,
    [ValidateSet("all", "rest", "graphql", "soap", "grpc")]
    [string]$Api = "all",
    [switch]$NoBuild,
    [switch]$KeepServices,
    [switch]$StartOnly
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$AllApis = @("rest", "graphql", "soap", "grpc")
$ApiNames = if ($Api -eq "all") { $AllApis } else { @($Api) }
$ServiceByApi = @{
    rest = "rest-python"
    graphql = "graphql-python"
    soap = "soap-python"
    grpc = "grpc-python"
}
$EndpointByApi = @{
    rest = "http://localhost:3000"
    graphql = "http://localhost:3001/graphql"
    soap = "http://localhost:3002/soap"
    grpc = "localhost:50051"
}
$ApiServices = @($ApiNames | ForEach-Object { $ServiceByApi[$_] })
$ContainerResultsDir = if ($Api -eq "all") { "/app/results/python" } else { "/app/results/python/$Api" }
$ContainerChartsDir = "/app/results/charts"
$HostResultsDir = if ($Api -eq "all") { "$ProjectRoot\results\python" } else { "$ProjectRoot\results\python\$Api" }
$HostChartsDir = "$ProjectRoot\results\charts"

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
            Write-Host "Servicos Python prontos: $($Services -join ', ')"
            return
        }

        Write-Host "Aguardando servicos Python: $($pending -join ', ')"
        Start-Sleep -Seconds 3
    }

    Invoke-DockerCompose -Arguments @("ps")
    throw "Tempo limite atingido aguardando os servicos Python ficarem saudaveis."
}

function Stop-ApiServices {
    param([string[]]$Services)

    & docker compose stop @Services | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Nao foi possivel parar todos os containers Python automaticamente."
    }

    & docker compose rm -f @Services | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Nao foi possivel remover todos os containers Python automaticamente."
    }
}

function Show-ApiEndpoints {
    param([string[]]$Names)

    Write-Host "Endpoints Python disponiveis:"
    foreach ($name in $Names) {
        Write-Host "  $name -> $($EndpointByApi[$name])"
    }
}

if ($SpawnRate -le 0) {
    throw "SpawnRate deve ser maior que zero."
}

Test-PositiveIntList -Value $UserCounts

$env:LOCUST_DURATION = $Duration
$env:LOCUST_SPAWN_RATE = [string]$SpawnRate
$env:LOCUST_USER_COUNTS = $UserCounts

Write-Host "Configuracao dos testes Python:"
Write-Host "  API: $Api"
Write-Host "  Duracao: $env:LOCUST_DURATION"
Write-Host "  Spawn rate: $env:LOCUST_SPAWN_RATE"
Write-Host "  Cargas: $env:LOCUST_USER_COUNTS"

try {
    & docker --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker nao encontrado."
    }

    if (-not $NoBuild) {
        Write-Host "Construindo imagem Python..."
        Invoke-DockerCompose -Arguments @("build", "rest-python")
    }

    Write-Host "Subindo APIs Python..."
    Invoke-DockerCompose -Arguments (@("up", "-d") + $ApiServices)
    Wait-ServicesHealthy -Services $ApiServices -TimeoutSeconds $HealthTimeoutSeconds
    Show-ApiEndpoints -Names $ApiNames

    if ($StartOnly) {
        Write-Host "APIs Python iniciadas. Testes nao executados por causa de -StartOnly."
        return
    }

    Write-Host "Executando cenarios Locust contra Python..."
    $locustArgs = @(
        "--profile", "python-scenarios",
        "run", "--rm", "--no-deps",
        "-e", "LOCUST_RESULTS_DIR=$ContainerResultsDir"
    )
    if ($Api -ne "all") {
        $locustArgs += @("-e", "LOCUST_TECHNOLOGIES=$Api")
    }
    $locustArgs += "locust-python"
    Invoke-DockerCompose -Arguments $locustArgs

    Write-Host "Gerando graficos Python..."
    Invoke-DockerCompose -Arguments @(
        "--profile", "python-charts",
        "run", "--rm", "--no-deps",
        "-e", "LOCUST_RESULTS_DIR=$ContainerResultsDir",
        "-e", "LOCUST_CHARTS_DIR=$ContainerChartsDir",
        "charts-python"
    )

    Write-Host "Fluxo Python concluido. Resultados em: $HostResultsDir"
    Write-Host "Graficos em: $HostChartsDir"
}
finally {
    if ($KeepServices -or $StartOnly) {
        Write-Host "Containers Python mantidos ativos."
    }
    else {
        Write-Host "Encerrando containers Python..."
        Stop-ApiServices -Services $ApiServices
    }
}
