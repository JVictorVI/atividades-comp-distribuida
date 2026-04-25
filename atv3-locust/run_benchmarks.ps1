
# Criar pasta de resultados se não existir
if (!(Test-Path "results")) {
    New-Item -ItemType Directory -Path "results" | Out-Null
}

# ================================
# CONFIGURAÇÕES
# ================================
$users = @(10, 100, 1000)
$instancesList = @(1, 2, 3)

# URLs dos cenários (WordPress)
$POST_IMAGEM_1MB = "/?name=imagem-com-1mb"
$POST_TEXTO_400KB = "/?name=texto-de-400kb"
$POST_IMAGEM_300KB = "/?name=imagem-de-300kb"

# ================================
# EXECUÇÃO DOS TESTES
# ================================
foreach ($instances in $instancesList) {

    Write-Host ""
    Write-Host "====================================="
    Write-Host "Subindo ambiente com $instances instâncias"
    Write-Host "====================================="

    # 1. Troca configuração do Nginx
    Copy-Item ".\nginx\nginx-$instances.conf" ".\nginx.conf" -Force

    # 2. Derruba tudo
    docker compose down

    # 3. Sobe containers conforme cenário
    if ($instances -eq 1) {
        docker compose up -d mysql wordpress1 nginx
    }
    elseif ($instances -eq 2) {
        docker compose up -d mysql wordpress1 wordpress2 nginx
    }
    elseif ($instances -eq 3) {
        docker compose up -d mysql wordpress1 wordpress2 wordpress3 nginx
    }

    # 4. Aguarda inicialização completa
    Write-Host "Aguardando WordPress e MySQL iniciarem..."
    Start-Sleep -Seconds 60

    foreach ($u in $users) {

        Write-Host ""
        Write-Host "-------------------------------------"
        Write-Host "Executando teste: $instances instâncias / $u usuários"
        Write-Host "-------------------------------------"

        # Nome base do resultado
        $resultName = "result_${instances}inst_${u}users"

        # Executa Locust
        docker run --rm `
            -e POST_IMAGEM_1MB=$POST_IMAGEM_1MB `
            -e POST_TEXTO_400KB=$POST_TEXTO_400KB `
            -e POST_IMAGEM_300KB=$POST_IMAGEM_300KB `
            -v ${PWD}:/mnt/locust `
            locustio/locust `
            -f /mnt/locust/locustfile.py `
            --host http://host.docker.internal `
            --headless `
            -u $u `
            -r 10 `
            -t 30s `
            --csv /mnt/locust/results/$resultName

        Write-Host "Resultado salvo em: results/$resultName"
    }
}

Write-Host ""
Write-Host "====================================="
Write-Host "TODOS OS TESTES FINALIZADOS"
Write-Host "====================================="