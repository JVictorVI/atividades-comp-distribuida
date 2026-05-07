$ErrorActionPreference = "Stop"

$UsersList = @(15, 50, 100)
$SpawnRate = 3
$RunTime = "2m"

$RootDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$ResultsDir = Join-Path $RootDir "results"
$LocustFile = Join-Path $RootDir "locust\locustfile.py"

New-Item -ItemType Directory -Force -Path $ResultsDir | Out-Null

$Urls = @(
    "https://www.tudogostoso.com.br", #197.995 
    "https://www.dictionary.com", #186.679
    "https://canaltech.com.br", #145.405
    "https://br.ign.com", #111.828
    "https://kotaku.com", #107.614
    "https://receitas.globo.com", #101.434 
    "https://g1.globo.com", #79.895
    "https://cnn.com", #58.036
    "https://huggingface.co", #32.932
    "https://www.todamateria.com.br" #14.543 
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

  throw "Python nao encontrado no PATH. Instale Python ou ajuste o PATH antes de consolidar os resultados."
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

  throw "Servico nao respondeu em $Uri apos $TimeoutSeconds segundos."
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
      throw "docker compose up falhou no cenario $ScenarioName."
    }

    Write-Host "Aguardando servico responder..."
    Wait-Service -Uri $HostUrl

    if ($Scenario.UsesCache) {
      Write-Host "Aquecendo cache antes das medicoes..."
      foreach ($Url in $Urls) {
        Invoke-WithRetry -Uri "$HostUrl/api/$Url"
      }
    }

    foreach ($Users in $UsersList) {
      Write-Host ""
      Write-Host "Executando: $ScenarioName com $Users usuarios"

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
