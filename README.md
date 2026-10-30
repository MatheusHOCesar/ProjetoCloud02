# ☁️ Cloud Runner — Gerenciador de Namespaces & Cgroups

Sistema de execução isolada de processos e controle de recursos no kernel Linux utilizando **Namespaces** e **Cgroups v2**, provisionado de forma automatizada via **Vagrant** e persistido em **MySQL**.

---

## 👥 Equipe de Desenvolvimento
* **Johnny** — Infraestrutura (Vagrantfile inline, Provisionamento, Systemd) & Persistência (MySQL)
* **Kafer** — Interface Web & API de Controle (Flask, Bootstrap 5)
* **Mike** — Engine de Isolamento (Linux Namespaces `unshare`, Cgroups v2, Manipulação de Processos)

---

## 🚀 Como Inicializar o Projeto

### Pré-requisitos
* [VirtualBox](https://www.virtualbox.org/) (versão 6.1 ou superior)
* [Vagrant](https://www.vagrantup.com/) (versão 2.2 ou superior)

### Execução em Comando Único
1. Clone o repositório em sua máquina:
   ```bash
   git clone <https://github.com/MatheusHOCesar/ProjetoCloud02>
   cd <ProjetoCloud02>