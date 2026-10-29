#!/usr/bin/env bash
set -e

# INSIRA AQUI A URL REAL DO REPOSITÓRIO GITHUB DO GRUPO
REPO_URL="https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git"
APP_DIR="/opt/cloud-runner"

echo ">>> [1/5] Atualizando repositórios e instalando dependências base..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3 python3-pip mysql-server util-linux cgroup-tools

echo ">>> [2/5] Instalando bibliotecas Python do projeto..."
pip3 install flask mysql-connector-python

echo ">>> [3/5] Inicializando e configurando o MySQL..."
systemctl start mysql
systemctl enable mysql

mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS cloud_runner;
CREATE USER IF NOT EXISTS 'clouduser'@'localhost' IDENTIFIED BY 'cloudpass';
GRANT ALL PRIVILEGES ON cloud_runner.* TO 'clouduser'@'localhost';
FLUSH PRIVILEGES;
EOF

echo ">>> [4/5] Habilitando controladores de Cgroups v2 (CPU, Memória e I/O)..."
echo "+cpu +memory +io" > /sys/fs/cgroup/cgroup.subtree_control || true

echo ">>> [5/5] Preparando diretório de execução da aplicação..."
if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
fi

if git clone "$REPO_URL" "$APP_DIR" 2>/dev/null; then
    echo "Código clonado do GitHub com sucesso!"
else
    echo "Aviso: Clone remoto indisponível no momento. Sincronizando via /vagrant..."
    cp -r /vagrant "$APP_DIR"
fi

mkdir -p "$APP_DIR/storage/scripts" "$APP_DIR/storage/logs"

echo ">>> Provisionamento base finalizado com sucesso!"