"""
Скрипт деплоя сервера Zapret Manager на VPS.
Запуск: python deploy.py
"""

import paramiko
import time
import sys
import os

# Фикс кодировки Windows
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOST = "5.42.120.247"
USER = "root"
PASSWORD = "c8,sCBZhqJa*t7"
REPO = "https://github.com/great105/zapret-manager.git"
APP_DIR = "/opt/zapret-manager"


def run(ssh, cmd, check=True):
    print(f"  $ {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=180)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    if out:
        for line in out.split("\n")[:10]:
            print(f"    {line}")
    if err and code != 0:
        for line in err.split("\n")[:5]:
            print(f"    [!] {line}")
    if check and code != 0:
        print(f"    [FAIL] exit={code}")
    return out, err, code


def main():
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASSWORD, timeout=15)
    print("Connected!\n")

    # 1. System packages
    print("[1/6] Installing system packages...")
    run(ssh, "apt-get update -qq 2>&1 | tail -1")
    run(ssh, "apt-get install -y -qq python3-pip python3-venv git 2>&1 | tail -3")

    # 2. Clone repo
    print(f"\n[2/6] Cloning repo...")
    run(ssh, f"rm -rf {APP_DIR}", check=False)
    out, err, code = run(ssh, f"git clone {REPO} {APP_DIR}")
    if code != 0:
        print(f"    Clone failed! Trying with stderr: {err}")
        ssh.close()
        return

    # 3. Python venv + deps
    print("\n[3/6] Setting up Python environment...")
    run(ssh, f"python3 -m venv {APP_DIR}/venv")
    run(ssh, f"{APP_DIR}/venv/bin/pip install --upgrade pip -q 2>&1 | tail -1")
    run(ssh, f"{APP_DIR}/venv/bin/pip install -r {APP_DIR}/server/requirements.txt 2>&1 | tail -3")

    # 4. Create directories
    print("\n[4/6] Creating directories...")
    run(ssh, f"mkdir -p {APP_DIR}/server/binaries {APP_DIR}/server/updates")

    # 5. Systemd service
    print("\n[5/6] Setting up systemd service...")
    service_content = """[Unit]
Description=Zapret Manager Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={app_dir}/server
ExecStart={app_dir}/venv/bin/python {app_dir}/server/main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target""".format(app_dir=APP_DIR)

    # Write service file via heredoc
    run(ssh, f"cat > /etc/systemd/system/zapret-manager.service << 'SERVICEEOF'\n{service_content}\nSERVICEEOF")
    run(ssh, "systemctl daemon-reload")
    run(ssh, "systemctl enable zapret-manager 2>&1 | tail -1")
    run(ssh, "systemctl restart zapret-manager")

    # Open firewall
    run(ssh, "ufw allow 8000/tcp 2>/dev/null; true", check=False)

    # 6. Verify
    print("\n[6/6] Verifying...")
    time.sleep(3)
    run(ssh, "systemctl is-active zapret-manager")
    out, _, _ = run(ssh, "curl -s http://localhost:8000/api/services 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print(f'{len(d)} services loaded')\" 2>&1")
    run(ssh, "curl -s http://localhost:8000/api/update/check 2>/dev/null")

    ssh.close()

    print("\n" + "=" * 50)
    print("  DEPLOY COMPLETE!")
    print("=" * 50)
    print(f"\n  Server:  http://{HOST}:8000")
    print(f"  API Doc: http://{HOST}:8000/docs")
    print(f"  Stats:   http://{HOST}:8000/api/admin/stats")
    print(f"\n  Quick redeploy:")
    print(f"    python deploy.py")


if __name__ == "__main__":
    main()
