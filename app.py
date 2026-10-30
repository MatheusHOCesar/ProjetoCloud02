import os
import time
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Diretório para armazenamento local dos scripts enviados via formulário
SCRIPTS_DIR = os.path.abspath("storage/scripts")
os.makedirs(SCRIPTS_DIR, exist_ok=True)

# Importações seguras: não quebra se os outros módulos ainda não estiverem na branch
try:
    import database as db
except ImportError:
    db = None

try:
    import engine
except ImportError:
    engine = None

@app.route("/")
def index():
    """Rota principal: lista os ambientes gerenciados e scripts salvos."""
    environments = []
    scripts = []
    
    if db:
        try:
            environments = db.list_environments()
            if engine:
                for env in environments:
                    if env['status'] in ('Em execução', 'Iniciando'):
                        updated_st = engine.check_environment_status(env['id'], env['pid'], env['status'])
                        if updated_st != env['status']:
                            db.update_status(env['id'], updated_st)
                            env['status'] = updated_st
            scripts = db.list_scripts()
        except Exception as e:
            print(f"Aviso ao consultar banco: {e}")

    return render_template("index.html", environments=environments, scripts=scripts)

@app.route("/deploy", methods=["POST"])
def deploy():
    """Recebe parâmetros do formulário, salva o script e dispara a execução isolada."""
    env_name = request.form.get("env_name", "Ambiente-Padrao").strip()
    cpu_limit = int(request.form.get("cpu_limit", 50))
    mem_limit = int(request.form.get("mem_limit", 128))
    io_limit = int(request.form.get("io_limit", 10))
    script_source = request.form.get("script_source")

    script_id = None
    script_path = None

    # Opção 1: Reutilizar script existente
    if script_source == "existing" and db:
        script_id = request.form.get("existing_script_id")
        rec = db.get_script(script_id)
        if rec:
            script_path = rec['filepath']

    # Opção 2: Envio de arquivo .sh
    elif script_source == "upload":
        file = request.files.get("script_file")
        if file and file.filename:
            fname = f"{int(time.time())}_{secure_filename(file.filename)}"
            script_path = os.path.join(SCRIPTS_DIR, fname)
            file.save(script_path)
            if db:
                script_id = db.save_script(file.filename, script_path)

    # Opção 3: Script digitado no textarea da interface
    elif script_source == "inline":
        sname = request.form.get("inline_name", "servico.sh").strip()
        code = request.form.get("inline_code", "")
        fname = f"{int(time.time())}_{secure_filename(sname)}"
        if not fname.endswith(".sh"):
            fname += ".sh"
        script_path = os.path.join(SCRIPTS_DIR, fname)
        with open(script_path, "w", newline="\n") as f:
            f.write(code.replace("\r\n", "\n"))
        if db:
            script_id = db.save_script(sname, script_path)

    # Aciona a camada de persistência e a engine Linux
    if db and engine and script_path:
        env_id = db.create_environment(env_name, script_id, cpu_limit, mem_limit, io_limit)
        try:
            pid, cgroup_path, log_path = engine.start_environment(
                env_id, script_path, cpu_limit, mem_limit, io_limit
            )
            db.update_environment_execution(env_id, pid, cgroup_path, log_path, "Em execução")
        except Exception as e:
            print(f"Erro ao inicializar ambiente na engine: {e}")
            db.update_environment_execution(env_id, None, None, None, "Erro")

    return redirect(url_for("index"))

@app.route("/logs/<int:env_id>")
def get_logs(env_id):
    """Retorna o output em tempo real do ambiente para o modal."""
    if not db:
        return jsonify({"output": "Banco de dados ainda nao configurado."})
    
    env = db.get_environment(env_id)
    if not env or not env.get('log_path') or not os.path.exists(env['log_path']):
        return jsonify({"output": "Nenhum arquivo de output disponivel no momento."})
    
    with open(env['log_path'], "r", errors="replace") as f:
        return jsonify({"output": f.read()})

@app.route("/stop/<int:env_id>", methods=["POST"])
def stop_env(env_id):
    """Encerra a execução de um processo em background."""
    if db and engine:
        env = db.get_environment(env_id)
        if env:
            engine.stop_and_cleanup_environment(env_id, env['pid'], env['cgroup_path'])
            db.update_status(env_id, "Terminado")
    return redirect(url_for("index"))

@app.route("/delete/<int:env_id>", methods=["POST"])
def delete_env(env_id):
    """Remove o ambiente, limpa cgroups e apaga logs associados."""
    if db and engine:
        env = db.get_environment(env_id)
        if env:
            engine.stop_and_cleanup_environment(env_id, env['pid'], env['cgroup_path'])
            if env.get('log_path') and os.path.exists(env['log_path']):
                try:
                    os.remove(env['log_path'])
                except Exception:
                    pass
            db.delete_environment_record(env_id)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)