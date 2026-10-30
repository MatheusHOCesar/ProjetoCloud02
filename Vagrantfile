Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"
  config.vm.network "forwarded_port", guest: 5000, host: 8080, auto_correct: true

  config.vm.provider "virtualbox" do |vb|
    vb.name = "puc-cloud-runner"
    vb.memory = "4096"
    vb.cpus = 1
  end

  # 1. BLOCO INLINE: Instala o Git e clona o repositório direto pelo Vagrantfile
  config.vm.provision "shell", inline: <<-SHELL
    echo ">>> [1/2] (Vagrantfile) Preparando o ambiente e clonando o repositorio..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get install -y git

    APP_DIR="/opt/cloud-runner"
    if [ -d "$APP_DIR" ]; then
        rm -rf "$APP_DIR"
    fi

    # TROQUE ESTA URL PELA URL REAL DO GITHUB DE VOCES:
    git clone https://github.com/SEU_USUARIO/SEU_REPOSITORIO.git $APP_DIR

    # Garante que as pastas de armazenamento existam dentro da VM
    mkdir -p $APP_DIR/storage/scripts $APP_DIR/storage/logs
    chmod -R 777 $APP_DIR/storage
  SHELL

  # 2. BLOCO SCRIPT: Chama o arquivo provision.sh para configurar BD e Python
  config.vm.provision "shell", path: "provision.sh"
end