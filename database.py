import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'clouduser',
    'password': 'cloudpass',
    'database': 'cloud_runner'
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            filepath VARCHAR(512) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
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
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def save_script(name, filepath):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scripts (name, filepath) VALUES (%s, %s)", (name, filepath))
    script_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return script_id

def list_scripts():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM scripts ORDER BY created_at DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_script(script_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM scripts WHERE id = %s", (script_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def create_environment(env_name, script_id, cpu_limit, mem_limit, io_limit):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO environments (env_name, script_id, cpu_limit, mem_limit, io_limit, status)
        VALUES (%s, %s, %s, %s, %s, 'Iniciando')
    """, (env_name, script_id, cpu_limit, mem_limit, io_limit))
    env_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return env_id

def update_environment_execution(env_id, pid, cgroup_path, log_path, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE environments 
        SET pid = %s, cgroup_path = %s, log_path = %s, status = %s
        WHERE id = %s
    """, (pid, cgroup_path, log_path, status, env_id))
    conn.commit()
    cursor.close()
    conn.close()

def update_status(env_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE environments SET status = %s WHERE id = %s", (status, env_id))
    conn.commit()
    cursor.close()
    conn.close()

def list_environments():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.*, s.name as script_name 
        FROM environments e
        JOIN scripts s ON e.script_id = s.id
        ORDER BY e.created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_environment(env_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM environments WHERE id = %s", (env_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def delete_environment_record(env_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM environments WHERE id = %s", (env_id,))
    conn.commit()
    cursor.close()
    conn.close()