Vagrant.configure("2") do |config|
  # Imagem Ubuntu 22.04 LTS (suporte estavel a cgroups v2 e unshare)
  config.vm.box = "ubuntu/jammy64"

  # Redireciona a porta 5000 da aplicacao para a porta 8080 do host
  config.vm.network "forwarded_port", guest: 5000, host: 8080, auto_correct: true

  # Requisitos minimos exigidos na especificacao: 1 Core e 4096MB de memoria
  config.vm.provider "virtualbox" do |vb|
    vb.name = "puc-cloud-runner"
    vb.memory = "4096"
    vb.cpus = 1
  end

  # Provisionamento shell direto no Vagrantfile
  config.vm.provision "shell", inline: <<-SHELL
    set -e

    # URL DO REPOSITORIO (Substituir pela URL HTTPS do GitHub de voces)
    REPO_URL="https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git"
    APP_DIR="/opt/cloud-runner"

    echo ">>> [1/6] Atualizando pacotes e instalando dependencias do sistema..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y git python3 python3-pip mysql-server util-linux

    echo ">>> [2/6] Instalando pacotes Python necessarios..."
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
    echo "+cpu +memory +io" > /sys/fs/cgroup/cgroup.subtree_control || true

    echo ">>> [5/6] Executando git clone direto do repositorio..."
    if [ -d "$APP_DIR" ]; then
      rm -rf "$APP_DIR"
    fi

    # Clona diretamente o repositorio remoto no diretorio de producao
    git clone "$REPO_URL" "$APP_DIR" || {
      echo "Aviso: Falha ao clonar remoto. Utilizando pasta sincronizada /vagrant..."
      cp -r /vagrant "$APP_DIR"
    }

    mkdir -p "$APP_DIR/storage/scripts" "$APP_DIR/storage/logs"
    chmod -R 755 "$APP_DIR/storage"

    echo ">>> [6/6] Criando servico Systemd em background..."
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

    echo "=========================================================="
    echo " Provisionamento concluido com sucesso!"
    echo " Servico ativo em background via systemd."
    echo " Acesse: http://localhost:8080"
    echo "=========================================================="
  SHELL
end