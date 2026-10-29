import os
import signal
import subprocess
import shutil

CGROUP_BASE = "/sys/fs/cgroup"
LOGS_DIR = os.path.abspath("storage/logs")

def _get_root_disk_maj_min():
    """
    Descobre o Major:Minor number do disco principal (ex: 8:0 para /dev/sda)
    para aplicar o limite de I/O no Cgroup v2.
    """
    try:
        out = subprocess.check_output(["lsblk", "-ndo", "MAJ:MIN,MOUNTPOINT"]).decode()
        for line in out.strip().split("\n"):
            parts = line.split()
            if len(parts) == 2 and parts[1] == "/":
                # Em partições (ex: 8:1), o Cgroup v2 exige o dispositivo pai (ex: 8:0)
                maj = parts[0].split(":")[0]
                return f"{maj}:0"
    except Exception:
        pass
    return "8:0"  # Padrão do VirtualBox (sda)

def start_environment(env_id, script_path, cpu_percent, mem_mb, io_mbps):
    """
    1. Cria o Cgroup e configura limites de CPU, Memória e I/O.
    2. Dispara o script isolado em Namespaces (PID, Mount, UTS, IPC).
    3. Redireciona todo o output para arquivo (suporta processos infinitos).
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    cgroup_path = os.path.join(CGROUP_BASE, f"cloud_env_{env_id}")
    log_path = os.path.join(LOGS_DIR, f"env_{env_id}.log")
    exit_file = os.path.join(LOGS_DIR, f"env_{env_id}.exit")

    # Remove arquivo de exit anterior caso exista
    if os.path.exists(exit_file):
        os.remove(exit_file)

    # 1. Criação do diretório do Cgroup
    os.makedirs(cgroup_path, exist_ok=True)

    # Habilita controladores na raiz por segurança
    try:
        with open(os.path.join(CGROUP_BASE, "cgroup.subtree_control"), "w") as f:
            f.write("+cpu +memory +io")
    except Exception:
        pass

    # 2. Configura Limite de CPU (Período padrão de 100.000 us = 100ms)
    period = 100000
    quota = max(1000, int(period * (int(cpu_percent) / 100.0)))
    try:
        with open(os.path.join(cgroup_path, "cpu.max"), "w") as f:
            f.write(f"{quota} {period}\n")
    except Exception as e:
        print(f"Aviso ao configurar CPU: {e}")

    # 3. Configura Limite de Memória (Converte MB para Bytes)
    mem_bytes = int(mem_mb) * 1024 * 1024
    try:
        with open(os.path.join(cgroup_path, "memory.max"), "w") as f:
            f.write(f"{mem_bytes}\n")
    except Exception as e:
        print(f"Aviso ao configurar Memória: {e}")

    # 4. Configura Limite de I/O (Converte MB/s para Bytes/s)
    io_bytes = int(io_mbps) * 1024 * 1024
    maj_min = _get_root_disk_maj_min()
    try:
        with open(os.path.join(cgroup_path, "io.max"), "w") as f:
            f.write(f"{maj_min} rbps={io_bytes} wbps={io_bytes}\n")
    except Exception as e:
        print(f"Aviso ao configurar I/O: {e}")

    # Garante permissão de execução no script enviado pelo usuário
    os.chmod(script_path, 0o755)

    # 5. Monta o comando de execução:
    # - Move o próprio PID ($$) para dentro do cgroup antes de rodar o unshare
    # - Executa o script dentro de novos namespaces (PID, Mount, UTS, IPC)
    # - Ao terminar, grava o código de retorno ($?) no arquivo .exit
    wrapped_cmd = (
        f"echo $$ > {cgroup_path}/cgroup.procs && "
        f"unshare --pid --mount-proc --uts --ipc --fork {script_path}; "
        f"echo $? > {exit_file}"
    )

    log_file = open(log_path, "w")
    
    # start_new_session=True cria um Process Group próprio para podermos matar toda a árvore depois
    proc = subprocess.Popen(
        ["/bin/bash", "-c", wrapped_cmd],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True
    )

    return proc.pid, cgroup_path, log_path

def check_environment_status(env_id, pid, current_status):
    """
    Verifica em tempo real se o ambiente ainda está rodando, se terminou com sucesso
    ou se parou por erro.
    """
    if current_status == "Terminado (Removido)":
        return current_status

    if not pid:
        return "Erro"

    exit_file = os.path.join(LOGS_DIR, f"env_{env_id}.exit")

    # Verifica se o processo existe no sistema e não é um processo zumbi (Z)
    proc_stat_path = f"/proc/{pid}/stat"
    is_alive = False
    if os.path.exists(proc_stat_path):
        try:
            with open(proc_stat_path, "r") as f:
                stat_content = f.read()
                # O estado fica logo após o nome do executável entre parênteses: "pid (comm) STATE ..."
                state = stat_content.split(")")[1].split()[0]
                if state != 'Z':
                    is_alive = True
        except Exception:
            is_alive = False

    if is_alive:
        return "Em execução"

    # Se não está mais vivo, checa o código de saída deixado pelo wrapper
    if os.path.exists(exit_file):
        try:
            with open(exit_file, "r") as f:
                code = int(f.read().strip())
            return "Terminado" if code == 0 else "Erro"
        except Exception:
            return "Erro"

    return "Terminado"

def stop_and_cleanup_environment(env_id, pid, cgroup_path):
    """
    Encerra todos os processos dentro do Cgroup/Namespace e remove o Cgroup do sistema.
    """
    # 1. Mata todos os processos registrados dentro do cgroup
    if cgroup_path and os.path.exists(cgroup_path):
        procs_file = os.path.join(cgroup_path, "cgroup.procs")
        if os.path.exists(procs_file):
            try:
                with open(procs_file, "r") as f:
                    pids = [int(p.strip()) for p in f.readlines() if p.strip()]
                for p in pids:
                    try:
                        os.kill(p, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            except Exception:
                pass

    # 2. Garante a morte do grupo de processos principal
    if pid:
        try:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except Exception:
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

    # 3. Remove o diretório do Cgroup (No cgroupfs usa-se rmdir)
    if cgroup_path and os.path.exists(cgroup_path):
        try:
            os.rmdir(cgroup_path)
        except Exception:
            pass