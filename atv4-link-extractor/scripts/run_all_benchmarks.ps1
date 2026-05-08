$ErrorActionPreference = "Stop"

$UsersList = @(100, 250, 500)
$SpawnRate = 10
$RunTime = "2m"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ResultsDir = Join-Path $RootDir "results"
$LocustFile = Join-Path $RootDir "locust\locustfile.py"

New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

$Urls = @(
    "https://www.foxnews.com", #911 links
    "https://cnn.com", #486 links
    "https://br.ign.com", #383 links 
    "https://www.estadao.com.br", #308 links
    "https://www12.senado.leg.br", #250 links
    "https://receitas.globo.com", #235 links 
    "https://www.tudogostoso.com.br", #208 links 
    "https://www.todamateria.com.br", #179 links 
    "https://canaltech.com.br", #155 links
    "https://kotaku.com" #136 links
)

$Scenarios = [ordered]@{
  python_nocache = @{ Dir = "step4"; Host = "http://localhost:5000"; UsesCache = $false; Services = @("api") }
  python_cache = @{ Dir = "step5"; Host = "http://localhost:5000"; UsesCache = $true; Services = @("api", "redis") }
  ruby_cache = @{ Dir = "step6"; Host = "http://localhost:4567"; UsesCache = $true; Services = @("api", "redis") }
  ruby_nocache = @{ Dir = "step6-nocache"; Host = "http://localhost:4567"; UsesCache = $false; Services = @("api") }
}

function Invoke-PythonScript {
  param([string]$Script)

  if (Get-Command python -ErrorAction SilentlyContinue) {
    python $Script
    return
  }

  if (Get-Command py -ErrorAction SilentlyContinue) {
    py $Script
    return
  }

  throw "Python não encontrado no PATH. Instale Python ou ajuste o PATH antes de consolidar os resultados."
}

function Stop-AllScenarioComposes {
  foreach ($ScenarioName in $Scenarios.Keys) {
    $ScenarioDir = Join-Path $RootDir $Scenarios[$ScenarioName].Dir
    Push-Location $ScenarioDir
    docker compose down --remove-orphans
    Pop-Location
  }
}

function Wait-Service {
  param(
    [string]$Uri,
    [int]$TimeoutSeconds = 90
  )

  $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  do {
    try {
      Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 5 | Out-Null
      return
    } catch {
      if ($_.Exception.Response) {
        return
      }

      Start-Sleep -Seconds 3
    }
  } while ((Get-Date) -lt $Deadline)

  throw "Serviço não respondeu em $Uri após $TimeoutSeconds segundos."
}

function Invoke-WithRetry {
  param(
    [string]$Uri,
    [int]$Attempts = 3
  )

  for ($Attempt = 1; $Attempt -le $Attempts; $Attempt++) {
    try {
      Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 60 | Out-Null
      return
    } catch {
      if ($Attempt -eq $Attempts) {
        throw
      }

      Start-Sleep -Seconds 5
    }
  }
}

foreach ($ScenarioName in $Scenarios.Keys) {
  $Scenario = $Scenarios[$ScenarioName]
  $StepDir = Join-Path $RootDir $Scenario.Dir
  $HostUrl = $Scenario.Host
  $Services = $Scenario.Services

  Write-Host ""
  Write-Host "===================================================="
  Write-Host "Cenario: $ScenarioName | Pasta: $($Scenario.Dir) | Host: $HostUrl"
  Write-Host "===================================================="

  Stop-AllScenarioComposes
  Push-Location $StepDir

  try {
    docker compose up -d --build @Services
    if ($LASTEXITCODE -ne 0) {
      throw "docker compose up falhou no cenário $ScenarioName."
    }

    Write-Host "Aguardando serviço responder..."
    Wait-Service -Uri $HostUrl

    if ($Scenario.UsesCache) {
      Write-Host "Aquecendo cache antes das medições..."
      foreach ($Url in $Urls) {
        Invoke-WithRetry -Uri "$HostUrl/api/$Url"
      }
    }

    foreach ($Users in $UsersList) {
      Write-Host ""
      Write-Host "Executando: $ScenarioName com $Users usuários"

      $OutputPrefix = Join-Path $ResultsDir "${ScenarioName}_${Users}"
      $env:LINK_COUNTS_CSV = "${OutputPrefix}_link_counts.csv"

      locust `
        -f $LocustFile `
        --headless `
        -u $Users `
        -r $SpawnRate `
        --run-time $RunTime `
        --host $HostUrl `
        --csv $OutputPrefix `
        --html "${OutputPrefix}.html"

      Remove-Item Env:\LINK_COUNTS_CSV -ErrorAction SilentlyContinue
      Start-Sleep -Seconds 5
    }
  } catch {
    Write-Host ""
    Write-Host "Falha no cenario $ScenarioName. Estado dos containers:"
    docker compose ps
    Write-Host ""
    Write-Host "Logs recentes da API:"
    docker compose logs --tail 80 api
    throw
  } finally {
    docker compose down --remove-orphans
    Pop-Location
  }
}

Push-Location $RootDir
Invoke-PythonScript "scripts\consolidate_results.py"
Invoke-PythonScript "scripts\generate_graphs.py"
Pop-Location

Write-Host ""
Write-Host "Finalizado."
Write-Host "Resultados CSV: results/"
Write-Host "Planilha consolidada: consolidated/resultados_consolidados.csv"
Write-Host "Graficos: graphs/"
