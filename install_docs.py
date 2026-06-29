#!/usr/bin/env python3
# install_docs.py
# Enterprise documentation installer and native styler matching Sentinel Commander UI

import os
import sys
import subprocess
from pathlib import Path

# --- STYLES & COLORS ---
class C:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'

# --- CONFIGURATION ---
DOCS_DIR = os.getcwd()
VENV_DIR = os.path.join(DOCS_DIR, "venv")
SYSTEMD_SERVICE = "sentinel-doc"
CONFIG_FILE = "mkdocs.yml"
INTERNAL_PORT = "8800"
# ---------------------

def print_banner():
    banner = fr"""{C.CYAN}{C.BOLD}
     _____            __  _            __   ____                 
    / ___/___  ____  / /_(_)___  ___  / /  / __ \____  __________
    \__ \/ _ \/ __ \/ __/ / __ \/ _ \/ /  / / / / __ \/ ___/ ___/
   ___/ /  __/ / / / /_/ / / / /  __/ /  / /_/ / /_/ / /__(__  ) 
  /____/\___/_/ /_/\__/_/_/ /_/\___/_/  /_____/\____/\___/____/  
{C.RESET}{C.BLUE}{C.BOLD}
[INFO] Sentinel Docs - Enterprise Initialization & Configuration Wizard{C.RESET}
"""
    print(banner)

def check_root():
    if os.geteuid() != 0:
        print(f"{C.RED}{C.BOLD}[ERROR] This script must be run as root (sudo)!{C.RESET}")
        sys.exit(1)

def prompt_user(message, default="n"):
    choices = f" {C.BOLD}(y/N){C.RESET}: " if default == "n" else f" {C.BOLD}(Y/n){C.RESET}: "
    print(f"{C.YELLOW}? {message}{choices}", end="")
    resp = input().strip().lower()
    if not resp:
        return default == "y"
    return resp in ["y", "yes"]

def detect_os():
    if not os.path.exists("/etc/os-release"):
        print(f"{C.RED}[ERROR] Cannot detect operating system template configuration.{C.RESET}")
        sys.exit(1)
        
    os_info = {}
    with open("/etc/os-release", "r") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                os_info[k] = v.strip('"')
                
    return os_info.get("ID", ""), os_info.get("ID_LIKE", "")

def install_system_packages(os_id, os_like, use_nginx, use_https):
    print(f"{C.BLUE}[*] Detecting Operating System:{C.RESET} {os_id}")
    is_debian = "debian" in os_id or "ubuntu" in os_id or "debian" in os_like
    is_rhel = any(x in os_id for x in ["rhel", "rocky", "almalinux"]) or "rhel" in os_like
    
    env = os.environ.copy()
    env["DEBIAN_FRONTEND"] = "noninteractive"

    if is_debian:
        print(f"{C.BLUE}[*] Installing system dependencies via APT...{C.RESET}")
        subprocess.run(["apt-get", "update"], check=True, env=env, stdout=subprocess.DEVNULL)
        pkgs = ["python3", "python3-pip", "python3-venv", "git"]
        if use_nginx:
            pkgs.append("nginx")
        if use_https:
            pkgs.extend(["certbot", "python3-certbot-nginx"])
        subprocess.run(["apt-get", "install", "-y"] + pkgs, check=True, env=env, stdout=subprocess.DEVNULL)
        
    elif is_rhel:
        print(f"{C.BLUE}[*] Installing system dependencies via DNF...{C.RESET}")
        pkgs = ["python3", "python3-pip", "git"]
        if use_nginx:
            pkgs.append("nginx")
        subprocess.run(["dnf", "install", "-y"] + pkgs, check=True, stdout=subprocess.DEVNULL)
        if use_https:
            subprocess.run(["dnf", "install", "-y", "epel-release"], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(["dnf", "install", "-y", "certbot", "python3-certbot-nginx"], check=True, stdout=subprocess.DEVNULL)
    else:
        print(f"{C.RED}[ERROR] Unsupported Linux distribution: {os_id}{C.RESET}")
        sys.exit(1)
    print(f"{C.GREEN}[OK] Native packages installed.{C.RESET}")

def setup_python_environment():
    print(f"{C.BLUE}[*] Creating isolated Python virtual environment...{C.RESET}")
    if not os.path.exists(VENV_DIR):
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
        
    pip_bin = os.path.join(VENV_DIR, "bin", "pip")
    print(f"{C.BLUE}[*] Injecting MkDocs, Material Theme, and extension suites...{C.RESET}")
    subprocess.run([pip_bin, "install", "--upgrade", "pip"], check=True, capture_output=True)
    subprocess.run([pip_bin, "install", "mkdocs", "mkdocs-material", "mkdocs-static-i18n", "pymdown-extensions"], check=True, capture_output=True)
    print(f"{C.GREEN}[OK] Python environment ready.{C.RESET}")

def configure_systemd(resp_nginx, start_service):
    print(f"{C.BLUE}[*] Configuring Systemd Service Unit wrapper...{C.RESET}")
    bind_ip = "127.0.0.1" if resp_nginx else "0.0.0.0"
    
    service_content = f"""[Unit]
Description=Sentinel MkDocs Documentation Server
After=network.target

[Service]
Type=simple
WorkingDirectory={DOCS_DIR}
ExecStart={VENV_DIR}/bin/mkdocs serve --dev-addr {bind_ip}:{INTERNAL_PORT}
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
"""
    sanitized_systemd = service_content.replace('\xa0', ' ')
    service_path = f"/etc/systemd/system/{SYSTEMD_SERVICE}.service"
    with open(service_path, "w", encoding="utf-8") as f:
        f.write(sanitized_systemd)
        
    subprocess.run(["systemctl", "daemon-reload"], check=True)
    
    if start_service:
        print(f"{C.BLUE}[*] Activating and enabling systemd daemon sequence...{C.RESET}")
        subprocess.run(["systemctl", "enable", "--now", SYSTEMD_SERVICE], check=True)
    else:
        print(f"{C.MAGENTA}[*] Service unit provisioned in static manual startup mode.{C.RESET}")

def configure_nginx(domain_name, use_https):
    print(f"{C.BLUE}[*] Provisioning Nginx structural integration routes...{C.RESET}")
    
    nginx_conf_dir = "/etc/nginx/conf.d"
    if os.path.exists("/etc/nginx/sites-available"):
        nginx_conf_dir = "/etc/nginx/sites-available"
        
    target_conf = os.path.join(nginx_conf_dir, "sentinel.conf")
    server_token = domain_name if domain_name else "_"
    
    nginx_content = f"""server {{
    listen 80;
    server_name {server_token};

    location / {{
        proxy_pass [http://127.0.0.1](http://127.0.0.1):{INTERNAL_PORT};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""
    sanitized_nginx = nginx_content.replace('\xa0', ' ')
    with open(target_conf, "w", encoding="utf-8") as f:
        f.write(sanitized_nginx)
        
    debian_link = "/etc/nginx/sites-enabled/sentinel"
    if os.path.exists("/etc/nginx/sites-enabled"):
        if not os.path.exists(debian_link):
            os.symlink(target_conf, debian_link)
        default_site = "/etc/nginx/sites-enabled/default"
        if os.path.exists(default_site):
            os.remove(default_site)
            
    subprocess.run(["systemctl", "enable", "nginx"], check=True)
    subprocess.run(["systemctl", "restart", "nginx"], check=True)
    
    if use_https and domain_name:
        print(f"{C.BLUE}[*] Executing Certbot payload request for: {C.BOLD}{domain_name}{C.RESET}")
        certbot_cmd = [
            "certbot", "--nginx", "-d", domain_name, 
            "--non-interactive", "--agree-tos", 
            "--register-unsafely-without-email", "--redirect"
        ]
        subprocess.run(certbot_cmd, check=True)
        subprocess.run(["systemctl", "restart", "nginx"], check=True)
    
    print(f"{C.GREEN}[OK] Nginx routing active.{C.RESET}")

if __name__ == "__main__":
    check_root()
    print_banner()
    
    print(f"{C.CYAN}Directory context verified:{C.RESET} {DOCS_DIR}\n")
    
    resp_service = prompt_user("Do you want to ENABLE and START systemd service on boot?")
    resp_nginx = prompt_user("Do you want to install and configure Nginx proxy?")
    
    use_https = False
    domain_name = ""
    if resp_nginx:
        use_https = prompt_user("Do you want to configure HTTPS via Let's Encrypt?")
        if use_https:
            print(f"{C.YELLOW}? Enter your domain name (e.g., docs.example.com): {C.RESET}", end="")
            domain_name = input().strip()
            if not domain_name:
                print(f"{C.RED}[ERROR] Domain name cannot be empty for HTTPS setup configurations!{C.RESET}")
                sys.exit(1)

    print("")
    os_id, os_like = detect_os()
    install_system_packages(os_id, os_like, resp_nginx, use_https)
    setup_python_environment()
    generate_mkdocs_config()
    generate_sentinel_css()
    configure_systemd(resp_nginx, resp_service)
    
    if resp_nginx:
        configure_nginx(domain_name, use_https)
        
    print(f"\n{C.GREEN}{C.BOLD}======================================================================{C.RESET}")
    print(f"{C.GREEN}{C.BOLD}[SUCCESS] Production pipeline script execution finished.{C.RESET}")
    print(f"{C.MAGENTA}[NOTE] Folder 'docs/' and existing documents were strictly NOT modified.{C.RESET}")
    print(f"{C.GREEN}{C.BOLD}======================================================================{C.RESET}\n")
    
    if resp_service:
        print(f" {C.CYAN}➔ Systemd Service:{C.RESET} Active on background daemon. Status: {C.BOLD}'sudo systemctl status {SYSTEMD_SERVICE}'{C.RESET}")
    else:
        print(f" {C.CYAN}➔ Foreground testing target execution address run phrase:{C.RESET}")
        print(f"    {C.BOLD}{VENV_DIR}/bin/mkdocs serve --dev-addr 0.0.0.0:{INTERNAL_PORT}{C.RESET}")
        
    if resp_nginx:
        protocol = "https" if use_https else "http"
        host = domain_name if domain_name else "<server_ip_address>"
        print(f" {C.CYAN}➔ Production Proxy URL:{C.RESET} {C.BOLD}{C.GREEN}{protocol}://{host}{C.RESET}")
    else:
        print(f" {C.CYAN}➔ Port Target Access Endpoint:{C.RESET} {C.BOLD}{C.GREEN}http://<server_ip_address>:{INTERNAL_PORT}{C.RESET}")
    print("")
