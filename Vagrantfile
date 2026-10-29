Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  # Redireciona a porta da aplicação Web (5000 -> 8080)
  config.vm.network "forwarded_port", guest: 5000, host: 8080, auto_correct: true

  # Requisitos mínimos da especificação: 1 Core e 4096MB RAM
  config.vm.provider "virtualbox" do |vb|
    vb.name = "cloud-runner-vm"
    vb.memory = "4096"
    vb.cpus = 1
  end

  config.vm.provision "shell", path: "provision.sh"
end