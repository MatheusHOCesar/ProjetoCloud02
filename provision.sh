#!/usr/bin/env bash
set -e

APP_DIR="/opt/cloud-runner"

echo ">>> [2/2] (provision.sh) Instalando dependencias e configurando serviços..."
export DEBIAN_FRONTEND=noninteractive
apt-get install -y python3 python3-pip mysql-server util-linux

echo ">>> Instalando bibliotecas Python (Flask e MySQL)..."
pip3 install flask mysql-connector-python

echo ">>> Configurando Banco de Dados MySQL..."
systemctl start mysql
systemctl enable mysql

mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS cloud_runner;
CREATE USER IF NOT EXISTS 'clouduser'@'localhost' IDENTIFIED BY 'cloudpass';
GRANT ALL PRIVILEGES ON cloud_runner.* TO 'clouduser'@'localhost';
FLUSH PRIVILEGES;

USE cloud_runner;

CREATE TABLE IF NOT EXISTS scripts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filepath VARCHAR(512) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS environments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    env_name VARCHAR(255) NOT NULL,
    script_id INT NOT NULL,
    cpu_limit INT NOT NULL,
    mem_limit INT NOT NULL,
    io_limit INT NOT NULL,
    pid INT,
    cgroup_path VARCHAR(512),
    log_path VARCHAR(512),
    status VARCHAR(50) DEFAULT 'Em execução',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (script_id) REFERENCES scripts(id)
);
EOF

echo ">>> Habilitando delegação de Cgroups v2 na raiz..."
echo "+cpu +memory +io" > /sys/fs/cgroup/cgroup.subtree_control || true

echo ">>> Criando serviço Systemd para rodar a aplicação em background..."
cat <<EOF > /etc/systemd/system/cloud-runner.service
[Unit]
Description=Cloud Runner Web Service
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable cloud-runner
systemctl restart cloud-runner

echo ">>> Setup finalizado! Acesse http://localhost:8080"