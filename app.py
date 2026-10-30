import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

import database as db
import engine

app = Flask(__name__)
SCRIPTS_DIR = os.path.abspath("storage/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# 1. Garante que as tabelas sejam criadas no MySQL ao iniciar o servidor
try:
    db.init_db()
except Exception as e:
    print(f"Aviso ao inicializar banco no boot: {e}")

@app.route("/")
def index():
    # Garante que as tabelas existam antes de listar
    db.init_db()
    
    # Atualiza o status de todos os ambientes antes de renderizar a página
    environments = db.list_environments()
    for env in environments:
        if env['status'] in ('Em execução', 'Iniciando'):
            new_status = engine.check_environment_status(env['id'], env['pid'], env['status'])
            if new_status != env['status']:
                db.update_status(env['id'], new_status)
                env['status'] = new_status

    scripts = db.list_scripts()
    return render_template("index.html", environments=environments, scripts=scripts)

@app.route("/deploy", methods=["POST"])
def deploy():
    # Garante que as tabelas existam antes de inserir
    db.init_db()

    env_name = (request.form.get("env_name") or "Ambiente-Padrao").strip()
    cpu_limit = int(request.form.get("cpu_limit") or 50)
    mem_limit = int(request.form.get("mem_limit") or 128)
    io_limit = int(request.form.get("io_limit") or 10)
    
    script_source = request.form.get("script_source", "inline")
    script_id = None
    script_path = None

    # Opção 1: Reutilizar um script já enviado anteriormente
    if script_source == "existing":
        script_id = request.form.get("existing_script_id")
        script_record = db.get_script(script_id)
        if not script_record:
            return "Script não encontrado no banco de dados.", 400
        script_path = script_record['filepath']
    
    # Opção 2: Enviar um novo arquivo de script via formulário
    elif script_source == "upload":
        uploaded_file = request.files.get("script_file")
        if not uploaded_file or uploaded_file.filename == "":
            return "Nenhum arquivo de script enviado.", 400
        
        filename = f"{int(time.time())}_{secure_filename(uploaded_file.filename)}"
        script_path = os.path.join(SCRIPTS_DIR, filename)
        uploaded_file.save(script_path)
        
        # Converte quebras de linha CRLF (Windows) para LF (Linux)
        with open(script_path, "rb") as f:
            content = f.read().replace(b"\r\n", b"\n")
        with open(script_path, "wb") as f:
            f.write(content)

        script_id = db.save_script(uploaded_file.filename, script_path)

    # Opção 3 (Padrão): Digitar o código do script direto na interface
    else:
        sname = (
            request.form.get("inline_name") 
            or request.form.get("script_name") 
            or "servico.sh"
        ).strip()
        scode = (
            request.form.get("inline_code") 
            or request.form.get("script_code") 
            or "#!/bin/bash\necho 'Executando...'"
        )
        filename = f"{int(time.time())}_{secure_filename(sname)}"
        if not filename.endswith(".sh"):
            filename += ".sh"
        script_path = os.path.join(SCRIPTS_DIR, filename)
        
        with open(script_path, "w", newline="\n") as f:
            f.write(scode.replace("\r\n", "\n"))
            
        script_id = db.save_script(sname, script_path)

    # 1. Registra o ambiente no banco de dados
    env_id = db.create_environment(env_name, script_id, cpu_limit, mem_limit, io_limit)

    # 2. Dispara a execução isolada via Cgroups + Namespaces
    try:
        pid, cgroup_path, log_path = engine.start_environment(
            env_id, script_path, cpu_limit, mem_limit, io_limit
        )
        db.update_environment_execution(env_id, pid, cgroup_path, log_path, "Em execução")
    except Exception as e:
        db.update_environment_execution(env_id, None, None, None, "Erro")
        print(f"Erro ao iniciar ambiente {env_id}: {e}")

    return redirect(url_for("index"))

@app.route("/logs/<int:env_id>")
def get_logs(env_id):
    """Retorna o conteúdo do arquivo de output do ambiente em JSON."""
    env = db.get_environment(env_id)
    if not env or not env['log_path'] or not os.path.exists(env['log_path']):
        return jsonify({"output": "Nenhum log disponível ainda para este ambiente."})
    
    with open(env['log_path'], "r", errors="replace") as f:
        content = f.read()
    return jsonify({"output": content if content else "(Arquivo de output vazio no momento)"})

@app.route("/stop/<int:env_id>", methods=["POST"])
def stop_env(env_id):
    """Interrompe a execução de um programa/serviço em andamento."""
    env = db.get_environment(env_id)
    if env:
        engine.stop_and_cleanup_environment(env_id, env['pid'], env['cgroup_path'])
        db.update_status(env_id, "Terminado")
    return redirect(url_for("index"))

@app.route("/delete/<int:env_id>", methods=["POST"])
def delete_env(env_id):
    """Para o processo (se estiver rodando), limpa o cgroup e remove da listagem."""
    env = db.get_environment(env_id)
    if env:
        engine.stop_and_cleanup_environment(env_id, env['pid'], env['cgroup_path'])
        if env['log_path'] and os.path.exists(env['log_path']):
            try:
                os.remove(env['log_path'])
            except Exception:
                pass
        db.delete_environment_record(env_id)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)