# $usersList = @(25, 75, 155) 1%-5% de erros
$usersList = @(25, 75, 159) # 5%-10% de erros
$instancesList = @(1, 2, 3)

$tests = @(
    @{ name = "light"; file = "locust_light.py" },
    @{ name = "medium"; file = "locust_medium.py" },
    @{ name = "heavy"; file = "locust_heavy.py" },
    @{ name = "hybrid"; file = "locust_hybrid.py" }
)

$runTime = "2m"
$spawnRate = 3
$resultsDir = "results"

New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null

foreach ($instances in $instancesList) {

    Write-Host "====================================="
    Write-Host "Instancias: $instances"
    Write-Host "====================================="

    Copy-Item ".\nginx\nginx-$instances.conf" ".\nginx.conf" -Force

    docker compose down | Out-Null

    docker compose up -d mysql wordpress1

    if ($instances -ge 2) {
        docker compose up -d wordpress2
    }

    if ($instances -ge 3) {
        docker compose up -d wordpress3
    }

    docker compose up -d nginx

    Start-Sleep -Seconds 10

    foreach ($test in $tests) {
        foreach ($u in $usersList) {

            $resultName = "$($test.name)_${instances}wp_${u}users"
            $prefix = "/mnt/locust/results/$resultName"

            Write-Host "Teste: $($test.name) | $instances wp | $u users"

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