# Trabalho 2 - Wordpress com Múltiplas Instâncias (Docker + Nginx)

## Descrição

Este projeto tem como objetivo configurar um ambiente com múltiplas instâncias do WordPress utilizando Docker Compose, com um servidor Nginx atuando como balanceador de carga.

---

## Arquitetura

O ambiente é composto por 5 containers:

- 1 container Nginx (balanceador de carga)
- 3 containers WordPress
- 1 container MySQL (banco de dados compartilhado)

---

## Configuração

### 🔹 Nginx

O Nginx foi configurado como balanceador de carga utilizando o bloco `upstream`, distribuindo requisições entre três instâncias do WordPress.

Também foi adicionado o header `X-Upstream` para identificar qual container respondeu cada requisição.

---

### 🔹 WordPress

- Foram criadas 3 instâncias do WordPress
- Todas compartilham:
  - O mesmo banco de dados
  - A mesma pasta `/var/www/html` (via volume local)

---

### 🔹 MySQL

- Banco único compartilhado entre todas as instâncias
- Não exposto para acesso externo

---

## Como executar

### 1. Clone ou copie os arquivos

Certifique-se de que `docker-compose.yml` e `nginx.conf` estão na **mesma pasta**.

### 2. Suba os contêineres

```bash
docker-compose up -d
```

O Docker vai baixar as imagens automaticamente na primeira execução. Aguarde até todos os contêineres estarem saudáveis.

### 3. Verifique se os contêineres estão rodando

```bash
docker-compose ps
```

Você deve ver **5 contêineres** com status `Up`:

| Nome       | Imagem                        | Porta      |
| ---------- | ----------------------------- | ---------- |
| nginx      | nginx:1.19.0                  | 0.0.0.0:80 |
| wordpress1 | wordpress:5.4.2-php7.2-apache | —          |
| wordpress2 | wordpress:5.4.2-php7.2-apache | —          |
| wordpress3 | wordpress:5.4.2-php7.2-apache | —          |
| mysql      | mysql:5.7                     | —          |

### 4. Acesse o WordPress

Abra no navegador: **http://localhost/**

É possível que, ao acessar imediatamente o endereço, seja exibido o erro:

```bash
502 Bad Gateway - nginx/1.19.0
```

### 4.1 Por que isso acontece?

Esse comportamento é esperado e ocorre devido ao tempo de inicialização dos serviços:

- O container do MySQL precisa de alguns segundos para iniciar completamente e aceitar conexões;
- As instâncias do WordPress dependem do MySQL e só ficam disponíveis após a inicialização do banco de dados;
- O Nginx, por outro lado, inicia rapidamente e já começa a encaminhar requisições, mesmo que o WordPress ainda não esteja pronto.

### 4.2 O que fazer?

**Aguarde aproximadamente 40 a 60 segundos após subir os containers antes de acessar a aplicação.**

Após esse tempo, o sistema estará totalmente funcional e o balanceamento de carga operando corretamente.

## Testando o balanceamento de carga

Execute o comando:

```bash
curl.exe -I http://localhost
```

Ou múltiplas vezes:

```bash
for ($i=0; $i -lt 5; $i++) { curl.exe -I http://localhost }
```

## Resultado esperado

O header abaixo deve aparecer com IPs diferentes:

```bash
X-Upstream: 172.x.x.x:80
```

Isso indica que o Nginx está distribuindo as requisições entre as instâncias.
