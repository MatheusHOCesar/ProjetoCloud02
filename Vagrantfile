Vagrant.configure("2") do |config|
  # Imagem base Ubuntu 22.04 LTS (Kernel com suporte nativo a Cgroups v2)
  config.vm.box = "ubuntu/jammy64"

  # Encaminhamento de portas: 5000 na VM (Flask) -> 8080 no host local
  config.vm.network "forwarded_port", guest: 5000, host: 8080, auto_correct: true

  # Requisitos mínimos de hardware exigidos
  config.vm.provider "virtualbox" do |vb|
    vb.name = "puc-cloud-runner"
    vb.memory = "4096"
    vb.cpus = 1
  end

  # Provisionamento executado inline via Shell
  config.vm.provision "shell", inline: <<-SHELL
    set -e

    # URL HTTPS do repositório do grupo no GitHub
    REPO_URL="https://github.com/MatheusHOCesar/ProjetoCloud02"
    APP_DIR="/opt/cloud-runner"

    echo ">>> [1/7] A corrigir data/hora e a sincronizar o relogio da VM..."
    timedatectl set-ntp true || true
    hwclock -s || true

    echo ">>> [2/7] A atualizar a lista de pacotes e dependencias do SO..."
    export DEBIAN_FRONTEND=noninteractive
    
    # Flag para contornar erros de assinaturas de pacotes invalidas por desvio horario
    apt-get -o Acquire::Check-Valid-Until=false update -y
    apt-get install -y git python3 python3-pip mysql-server util-linux systemd-timesyncd

    systemctl restart systemd-timesyncd || true

    echo ">>> [3/7] A configurar o servico e a base de dados MySQL..."
    systemctl start mysql
    systemctl enable mysql

    mysql -u root <<EOF
CREATE DATABASE IF NOT EXISTS cloud_runner;
CREATE USER IF NOT EXISTS 'clouduser'@'localhost' IDENTIFIED BY 'cloudpass';
GRANT ALL PRIVILEGES ON cloud_runner.* TO 'clouduser'@'localhost';
FLUSH PRIVILEGES;
EOF

    echo ">>> [4/7] A ativar os controladores do Cgroups v2 (CPU, Memoria e IO)..."
    echo "+cpu +memory +io" > /sys/fs/cgroup/cgroup.subtree_control || true

    echo ">>> [5/7] A descarregar o codigo fonte da aplicacao..."
    if [ -d "$APP_DIR" ]; then
      rm -rf "$APP_DIR"
    fi

    # Tenta clonar diretamente do GitHub; se falhar, utiliza a pasta sincronizada do host
    git clone "$REPO_URL" "$APP_DIR" || {
      echo "Aviso: Falha ao clonar do repositorio remoto. A copiar da pasta /vagrant..."
      cp -r /vagrant "$APP_DIR"
    }

    mkdir -p "$APP_DIR/storage/scripts" "$APP_DIR/storage/logs"
    chmod -R 755 "$APP_DIR/storage"

    echo ">>> [6/7] A instalar bibliotecas Python..."
    pip3 install --upgrade pip
    if [ -f "$APP_DIR/requirements.txt" ]; then
      pip3 install -r "$APP_DIR/requirements.txt"
    else
      pip3 install flask mysql-connector-python
    fi

    echo ">>> [7/7] A criar o servico Systemd em segundo plano..."
    cat <<EOF > /etc/systemd/system/cloud-runner.service
[Unit]
Description=Cloud Runner - Gestor de Namespaces e Cgroups
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

    echo "=========================================================="
    echo " Provisionamento concluido com sucesso!"
    echo " Servico ativo em segundo plano via systemd."
    echo " Aceda a: http://localhost:8080"
    echo "=========================================================="
  SHELL
end