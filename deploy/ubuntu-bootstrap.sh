#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-sleep.xihaoping.xyz}"
REPO_URL="${REPO_URL:-https://github.com/wkyfuling/sleep-system.git}"
APP_DIR="${APP_DIR:-/opt/sleep-system}"
FRONTEND_ROOT="${FRONTEND_ROOT:-/var/www/sleep-system/frontend}"
DB_DIR="${DB_DIR:-/var/lib/sleep-system}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root."
  exit 1
fi

echo "==> Installing system packages"
apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  gnupg \
  openssl \
  build-essential \
  pkg-config \
  default-libmysqlclient-dev \
  fonts-noto-cjk \
  fonts-wqy-zenhei \
  python3-dev \
  python3-venv \
  nginx \
  certbot \
  python3-certbot-nginx

if ! command -v node >/dev/null 2>&1 || ! node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 20 ? 0 : 1)" >/dev/null 2>&1; then
  echo "==> Installing Node.js 22"
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

echo "==> Fetching application code"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  rm -rf "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "==> Preparing backend"
cd "$APP_DIR/backend"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

SECRET_KEY="$(openssl rand -hex 32)"
if [ -f .env ]; then
  EXISTING_SECRET="$(grep -E '^SECRET_KEY=' .env | sed 's/^SECRET_KEY=//' || true)"
  if [ -n "$EXISTING_SECRET" ]; then
    SECRET_KEY="$EXISTING_SECRET"
  fi
fi

read_existing_env() {
  local key="$1"
  if [ -f .env ]; then
    grep -E "^${key}=" .env | tail -n 1 | sed "s/^${key}=//" || true
  fi
}

EXISTING_DEEPSEEK_API_KEY="$(read_existing_env DEEPSEEK_API_KEY)"
EXISTING_DEEPSEEK_BASE_URL="$(read_existing_env DEEPSEEK_BASE_URL)"
EXISTING_DEEPSEEK_MODEL="$(read_existing_env DEEPSEEK_MODEL)"
DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-$EXISTING_DEEPSEEK_API_KEY}"
DEEPSEEK_BASE_URL="${DEEPSEEK_BASE_URL:-${EXISTING_DEEPSEEK_BASE_URL:-https://api.deepseek.com}}"
DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-${EXISTING_DEEPSEEK_MODEL:-deepseek-chat}}"

mkdir -p "$DB_DIR"
chown www-data:www-data "$DB_DIR"
chmod 750 "$DB_DIR"

cat > .env <<EOF
DEBUG=False
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$DOMAIN,1.14.191.87,localhost,127.0.0.1
DATABASE_URL=sqlite:///$DB_DIR/db.sqlite3
ACCESS_TOKEN_LIFETIME_MINUTES=60
REFRESH_TOKEN_LIFETIME_DAYS=7
CORS_ALLOWED_ORIGINS=https://$DOMAIN,http://$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN,http://$DOMAIN
TRUST_X_FORWARDED_PROTO=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
DEEPSEEK_API_KEY=$DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL=$DEEPSEEK_BASE_URL
DEEPSEEK_MODEL=$DEEPSEEK_MODEL
DEEPSEEK_TIMEOUT_SECONDS=20
DEEPSEEK_MAX_TOKENS=500
DEEPSEEK_TEMPERATURE=0.7
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=sleep-system@$DOMAIN
EOF
chmod 640 .env
chown root:www-data .env

mkdir -p media staticfiles
chown -R www-data:www-data media staticfiles

ADMIN_PASSWORD_FILE="$DB_DIR/admin-password.txt"
if [ ! -f "$ADMIN_PASSWORD_FILE" ]; then
  openssl rand -base64 18 | tr -d '=+/' > "$ADMIN_PASSWORD_FILE"
  chown root:root "$ADMIN_PASSWORD_FILE"
  chmod 600 "$ADMIN_PASSWORD_FILE"
fi
ADMIN_PASSWORD="$(cat "$ADMIN_PASSWORD_FILE")"

runuser -u www-data -- env ADMIN_PASSWORD="$ADMIN_PASSWORD" "$APP_DIR/backend/venv/bin/python" manage.py migrate
runuser -u www-data -- env ADMIN_PASSWORD="$ADMIN_PASSWORD" "$APP_DIR/backend/venv/bin/python" manage.py shell -c "import os; from django.contrib.auth import get_user_model; U=get_user_model(); u,_=U.objects.get_or_create(username='admin', defaults={'role':'admin','is_staff':True,'is_superuser':True,'email':'admin@sleep-system.example'}); u.role='admin'; u.is_staff=True; u.is_superuser=True; u.set_password(os.environ['ADMIN_PASSWORD']); u.save(); print('admin ready')"
./venv/bin/python manage.py collectstatic --noinput

echo "==> Building frontend"
cd "$APP_DIR/frontend"
npm install
npm run build
mkdir -p "$FRONTEND_ROOT"
rm -rf "$FRONTEND_ROOT/dist"
cp -r dist "$FRONTEND_ROOT/dist"
chown -R www-data:www-data "$FRONTEND_ROOT"

echo "==> Installing systemd services"
cp "$APP_DIR/deploy/systemd/sleep-system.service" /etc/systemd/system/sleep-system.service
cp "$APP_DIR/deploy/systemd/sleep-system-scheduler.service" /etc/systemd/system/sleep-system-scheduler.service
systemctl daemon-reload
systemctl enable --now sleep-system
systemctl restart sleep-system
systemctl enable --now sleep-system-scheduler
systemctl restart sleep-system-scheduler

echo "==> Configuring Nginx"
sed "s/example.com www.example.com/$DOMAIN/g" "$APP_DIR/deploy/nginx/sleep-system.conf" > /etc/nginx/sites-available/sleep-system
ln -sf /etc/nginx/sites-available/sleep-system /etc/nginx/sites-enabled/sleep-system
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> Trying HTTPS certificate"
RESOLVED_IP="$(getent ahostsv4 "$DOMAIN" | awk '{print $1; exit}' || true)"
PUBLIC_IP="$(curl -fsS4 https://api.ipify.org || true)"
if [ -n "$RESOLVED_IP" ] && [ -n "$PUBLIC_IP" ] && [ "$RESOLVED_IP" = "$PUBLIC_IP" ]; then
  if [ -n "$CERTBOT_EMAIL" ]; then
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$CERTBOT_EMAIL"
  else
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email
  fi
  sed -i \
    -e 's/^SECURE_SSL_REDIRECT=.*/SECURE_SSL_REDIRECT=True/' \
    -e 's/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=True/' \
    -e 's/^CSRF_COOKIE_SECURE=.*/CSRF_COOKIE_SECURE=True/' \
    "$APP_DIR/backend/.env"
  systemctl restart sleep-system
else
  echo "Skipped HTTPS: $DOMAIN resolves to '$RESOLVED_IP', server public IP is '$PUBLIC_IP'."
  echo "Set the A record to the server IP, then run: certbot --nginx -d $DOMAIN"
fi

echo "==> Health check"
curl -fsS "http://127.0.0.1:8000/api/healthz/" || true
echo
echo "Deployment finished."
echo "URL: http://$DOMAIN"
echo "Admin username: admin"
echo "Admin password: $ADMIN_PASSWORD"
echo "Admin password file: $ADMIN_PASSWORD_FILE"
