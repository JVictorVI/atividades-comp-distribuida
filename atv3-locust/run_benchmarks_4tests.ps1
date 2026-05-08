# Cargas escolhidas para esta maquina de teste, mantendo a taxa de erros em ate 10%.
$usersList = @(25, 75, 155)

# Quantidade de instancias WordPress usadas para avaliar escalabilidade horizontal.
$instancesList = @(1, 2, 3)

# Cada entrada aponta para um arquivo Locust com um perfil de acesso diferente.
$tests = @(
    @{ name = "light"; file = "locust_light.py" },
    @{ name = "medium"; file = "locust_medium.py" },
    @{ name = "heavy"; file = "locust_heavy.py" },
    @{ name = "hybrid"; file = "locust_hybrid.py" }
)

$runTime = "2m"
$spawnRate = 3
$resultsDir = "results"

# Garante que a pasta de saida exista antes de o Locust gravar os CSVs.
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null

foreach ($instances in $instancesList) {

    Write-Host "====================================="
    Write-Host "Instancias: $instances"
    Write-Host "====================================="

    # Troca a configuracao do Nginx para balancear apenas as instancias deste teste.
    Copy-Item ".\nginx\nginx-$instances.conf" ".\nginx.conf" -Force

    # Reinicia o ambiente para evitar interferencia entre rodadas de benchmark.
    docker compose down | Out-Null

    # O MySQL e a primeira instancia do WordPress sempre participam dos testes.
    docker compose up -d mysql wordpress1

    # Sobe instancias adicionais somente quando a rodada exigir.
    if ($instances -ge 2) {
        docker compose up -d wordpress2
    }

    if ($instances -ge 3) {
        docker compose up -d wordpress3
    }

    # Inicia o balanceador depois que as instancias WordPress necessarias estiverem ativas.
    docker compose up -d nginx

    # Aguarda os containers aceitarem requisicoes antes de disparar carga.
    Start-Sleep -Seconds 10

    foreach ($test in $tests) {
        foreach ($u in $usersList) {

            # O prefixo define o nome base dos CSVs gerados pelo Locust dentro de results/.
            $resultName = "$($test.name)_${instances}wp_${u}users"
            $prefix = "/mnt/locust/results/$resultName"

            Write-Host "Teste: $($test.name) | $instances wp | $u users"

            # Executa o Locust em modo headless contra o Nginx, salvando as metricas em CSV.
            docker compose run --rm locust `
                -f "/mnt/locust/$($test.file)" `
                --headless `
                --host http://nginx `
                -u $u `
                -r $spawnRate `
                --run-time $runTime `
                --csv $prefix `
                --only-summary
        }
    }
}

Write-Host "Finalizado!"
