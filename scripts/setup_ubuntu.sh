#!/usr/bin/env bash
#
# Automated bootstrap for Django Maps on Ubuntu/Debian.
# Run from the project root: sudo bash scripts/setup_ubuntu.sh
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ $EUID -ne 0 ]]; then
  echo "This script must run with sudo (root) privileges because it installs system packages."
  exit 1
fi

log() { printf "\n[setup] %s\n" "$*"; }

read -rp "Install base dependencies via apt (python3.12, mariadb-client, redis, node)? [Y/n] " install_apt
install_apt=${install_apt:-Y}
if [[ $install_apt =~ ^[Yy]$ ]]; then
  log "Updating apt and installing base packages..."
  apt-get update
  apt-get install -y python3.12 python3.12-venv python3-pip \
    default-mysql-client redis-server build-essential pkg-config \
    nodejs npm
fi

# Configuration questions
read -rp "MariaDB database name (default: mapspro_db): " db_name
db_name=${db_name:-mapspro_db}
read -rp "Database user (default: mapspro_user): " db_user
db_user=${db_user:-mapspro_user}
read -rsp "Database password: " db_password
echo
read -rp "Database host (default: 127.0.0.1): " db_host
db_host=${db_host:-127.0.0.1}
read -rp "Database port (default: 3306): " db_port
db_port=${db_port:-3306}

read -rp "Redis URL (default: redis://127.0.0.1:6379/0): " redis_url
redis_url=${redis_url:-redis://127.0.0.1:6379/0}

read -rp "ALLOWED_HOSTS (comma separated, e.g. localhost,127.0.0.1): " allowed_hosts
allowed_hosts=${allowed_hosts:-localhost,127.0.0.1}

read -rp "Enable Zabbix diagnostics? (ENABLE_DIAGNOSTIC_ENDPOINTS=true) [y/N]: " diag_flag
if [[ $diag_flag =~ ^[Yy]$ ]]; then
  enable_diag=true
else
  enable_diag=false
fi

read -rp "Create Django superuser now? [Y/n] " create_superuser
create_superuser=${create_superuser:-Y}
if [[ $create_superuser =~ ^[Yy]$ ]]; then
  read -rp "Admin username: " admin_user
  read -rp "Admin email: " admin_email
  read -rsp "Admin password: " admin_pass
  echo
fi

# Python environment
log "Creating virtualenv .venv with Python 3.12..."
sudo -u "$SUDO_USER" python3.12 -m venv "$PROJECT_ROOT/.venv"

log "Installing Python dependencies..."
sudo -u "$SUDO_USER" bash -c "source '$PROJECT_ROOT/.venv/bin/activate' && pip install --upgrade pip && pip install -r '$PROJECT_ROOT/requirements.txt'"

log "Installing Node dependencies (npm install)..."
sudo -u "$SUDO_USER" npm install --prefix "$PROJECT_ROOT"

# .env configuration
ENV_FILE="$PROJECT_ROOT/.env"
if [[ ! -f $ENV_FILE ]]; then
  log "Creating .env from .env.example..."
  sudo -u "$SUDO_USER" cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
fi

log "Updating variables inside .env..."
sudo -u "$SUDO_USER" python3 <<PY
from pathlib import Path

env_path = Path("$ENV_FILE")
env_path.touch()
lines = env_path.read_text().splitlines()
mapping = {}
for line in lines:
    if not line or line.strip().startswith("#") or "=" not in line:
        continue
    key, val = line.split("=", 1)
    mapping[key.strip()] = val.strip()

updates = {
    "DATABASE_ENGINE": "django.db.backends.mysql",
    "DATABASE_NAME": "$db_name",
    "DATABASE_USER": "$db_user",
    "DATABASE_PASSWORD": "$db_password",
    "DATABASE_HOST": "$db_host",
    "DATABASE_PORT": "$db_port",
    "REDIS_URL": "$redis_url",
    "ALLOWED_HOSTS": "$allowed_hosts",
    "ENABLE_DIAGNOSTIC_ENDPOINTS": "${'true' if $enable_diag else 'false'}",
}

for key, value in updates.items():
    mapping[key] = value

new_lines = []
handled = set()
for line in lines:
    if not line or line.strip().startswith("#") or "=" not in line:
        new_lines.append(line)
        continue
    key = line.split("=", 1)[0].strip()
    if key in mapping:
        new_lines.append(f"{key}={mapping[key]}")
        handled.add(key)
    else:
        new_lines.append(line)

for key, value in mapping.items():
    if key not in handled:
        new_lines.append(f"{key}={value}")

env_path.write_text("\n".join(new_lines) + "\n")
PY

log "Generating FERNET_KEY..."
sudo -u "$SUDO_USER" bash -c "source '$PROJECT_ROOT/.venv/bin/activate' && python manage.py generate_fernet_key --write --force"

log "Running migrations and collectstatic..."
sudo -u "$SUDO_USER" bash -c "source '$PROJECT_ROOT/.venv/bin/activate' && python manage.py migrate"
sudo -u "$SUDO_USER" bash -c "source '$PROJECT_ROOT/.venv/bin/activate' && python manage.py collectstatic --noinput"

if [[ $create_superuser =~ ^[Yy]$ ]]; then
  log "Creating/updating Django superuser..."
  sudo -u "$SUDO_USER" bash -c "source '$PROJECT_ROOT/.venv/bin/activate' && python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
User = get_user_model()
username = \"$admin_user\"
email = \"$admin_email\"
password = \"$admin_pass\"
user, created = User.objects.get_or_create(username=username, defaults={\"email\": email})
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print(f\"Superuser {'created' if created else 'updated'}: {username}\")
PY"
fi

log "Setup complete!"
cat <<'EOF'
Next manual steps:
  1. Activate the virtualenv: source .venv/bin/activate
  2. Start Django: python manage.py runserver 0.0.0.0:8000
  3. In another terminal, start the Celery worker: celery -A core worker -l info
  4. Open http://<host>:8000/setup_app/first_time/ to finish initial configuration.

To create a release package later:
  sudo pwsh scripts/package-release.ps1   # or craft a zip manually, as described in the README.

Remember to configure database backups (mysqldump) and store .env/FERNET_KEY safely.
EOF
