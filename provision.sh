#!/usr/bin/env bash
set -e

# Configurações do projeto
REPO_URL="https://github.com/MatheusHOCesar/ProjetoCloud02"
APP_DIR="/opt/cloud-runner"

echo ">>> [1/6] Atualizando pacotes e instalando dependencias do sistema..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git python3 python3-pip mysql-server util-linux

echo ">>> [2/6] Instalando dependencias Python..."
pip3 install flask mysql-connector-python

echo ">>> [3/6] Configurando banco de dados MySQL..."
systemctl start mysql
systemctl enable mysql

mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS cloud_runner;
CREATE USER IF NOT EXISTS 'clouduser'@'localhost' IDENTIFIED BY 'cloudpass';
GRANT ALL PRIVILEGES ON cloud_runner.* TO 'clouduser'@'localhost';
FLUSH PRIVILEGES;
EOF

echo ">>> [4/6] Habilitando controladores de Cgroups v2 (CPU, Memoria e IO)..."
# Libera controladores na arvore raiz para permitir criacao de subgrupos com limites
echo "+cpu +memory +io" > /sys/fs/cgroup/cgroup.subtree_control || true

echo ">>> [5/6] Obtendo codigo da aplicacao..."
if [ -d "$APP_DIR" ]; then
    rm -rf "$APP_DIR"
fi

# Tenta clonar do GitHub remoto; se falhar (ex: repo privado ou offline), usa os arquivos da pasta /vagrant
if git clone "$REPO_URL" "$APP_DIR" 2>/dev/null; then
    echo "Codigo clonado do GitHub com sucesso!"
else
    echo "Aviso: Nao foi possivel clonar do GitHub. Sincronizando arquivos locais de /vagrant..."
    cp -r /vagrant "$APP_DIR"
fi

# Garante a existencia das pastas de persistencia local
mkdir -p "$APP_DIR/storage/scripts" "$APP_DIR/storage/logs"
chmod -R 755 "$APP_DIR/storage"

echo ">>> [6/6] Criando e iniciando servico Systemd (cloud-runner)..."
cat <<EOF > /etc/systemd/system/cloud-runner.service
[Unit]
Description=Cloud Runner - Gerenciador de Namespaces e Cgroups
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cloud-runner
systemctl restart cloud-runner

echo "================================================================="
echo " Provisionamento finalizado!"
echo " Servico ativo em background via systemd."
echo " Acesse: http://localhost:8080"
echo "================================================================="