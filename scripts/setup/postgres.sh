#!/usr/bin/env bash
# Cài PostgreSQL bản major mới nhất cho môi trường local và tạo role/database `fashion`.
#   macOS        : Homebrew (postgresql@<major>)
#   Ubuntu/Debian: apt từ repo PGDG (ngoài phạm vi hỗ trợ chính thức)
#   Windows      : dùng scripts/setup/postgres.ps1 (ADR 0017)
# Chạy lại nhiều lần vẫn an toàn. Xem docs/architecture/08-local-development.md mục 2.2.
set -euo pipefail

DB_USER=fashion
DB_PASSWORD=fashion
DB_NAME=fashion
EXTENSIONS=(unaccent pg_trgm btree_gist)
MIN_UV_VERSION=0.13

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<EOF
Cách dùng: scripts/setup/postgres.sh

Cài PostgreSQL bản major mới nhất (nếu máy chưa có), khởi động cluster,
tạo role '$DB_USER' (quyền CREATEDB) và database '$DB_NAME', rồi in DATABASE_URL.
Không đụng tới cluster PostgreSQL khác đang có trên máy.
EOF
}

case "${1:-}" in
  -h | --help) usage; exit 0 ;;
  "") ;;
  *) usage; die "Tham số không hợp lệ: $1" ;;
esac

# ---------------------------------------------------------------- Hệ điều hành

OS=""
case "$(uname -s)" in
  Darwin) OS=macos ;;
  Linux)
    if [ -r /etc/os-release ] && grep -qiE '^(ID|ID_LIKE)=.*(ubuntu|debian)' /etc/os-release; then
      OS=debian
    else
      die "Chỉ hỗ trợ Ubuntu/Debian và macOS."
    fi
    ;;
  MINGW* | MSYS* | CYGWIN*) die "Trên Windows hãy chạy: pwsh scripts/setup/postgres.ps1 (xem 08 mục 2.2)." ;;
  *) die "Hệ điều hành không được hỗ trợ: $(uname -s)." ;;
esac

# ---------------------------------------------------------------- Công cụ khác (chỉ kiểm tra)

version_ge() { [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" = "$2" ]; }

check_tools() {
  info "Kiểm tra công cụ (chỉ báo thiếu, không tự cài)"
  local tool
  for tool in git make docker; do
    command -v "$tool" >/dev/null 2>&1 || warn "Thiếu '$tool' (xem 08 mục 2.1)."
  done
  if command -v uv >/dev/null 2>&1; then
    local uv_version
    uv_version="$(uv --version | awk '{print $2}')"
    version_ge "$uv_version" "$MIN_UV_VERSION" || warn "uv $uv_version cũ hơn $MIN_UV_VERSION, chạy 'uv self update'."
  else
    warn "Thiếu 'uv' (xem 08 mục 2.1)."
  fi
}

port_in_use() {
  if command -v ss >/dev/null 2>&1; then
    ss -ltnH "sport = :$1" 2>/dev/null | grep -q .
  else
    # macOS: netstat thấy socket của mọi user, lsof không sudo thì chỉ thấy của user hiện tại.
    netstat -an -p tcp 2>/dev/null | awk -v p=".$1" '$6 == "LISTEN" && substr($4, length($4) - length(p) + 1) == p' | grep -q .
  fi
}

free_port_from() {
  local port=$1
  while port_in_use "$port"; do port=$((port + 1)); done
  echo "$port"
}

# ---------------------------------------------------------------- Ubuntu/Debian (apt + PGDG)

PG_MAJOR=""
PG_PORT=""

debian_setup_repo() {
  if ! ls /etc/apt/sources.list.d/ 2>/dev/null | grep -q pgdg; then
    info "Thêm repo apt.postgresql.org (PGDG)"
    sudo apt-get update -qq
    sudo apt-get install -y -qq postgresql-common ca-certificates curl
    sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh -y
  else
    sudo apt-get update -qq
  fi
}

debian_latest_major() {
  apt-cache search --names-only '^postgresql-[0-9]+$' | awk '{print $1}' | sed 's/postgresql-//' | sort -n | tail -n1
}

debian_install() {
  debian_setup_repo
  PG_MAJOR="$(debian_latest_major)"
  [ -n "$PG_MAJOR" ] || die "Không tìm thấy gói postgresql-<major> trên PGDG."

  if dpkg -s "postgresql-$PG_MAJOR" >/dev/null 2>&1; then
    # Không nâng bản minor: nâng sẽ restart cluster, cắt kết nối của container đang chạy.
    info "PostgreSQL $PG_MAJOR (bản mới nhất) đã có sẵn, dùng luôn"
  else
    # postgresql-common tự tạo cluster 'main' ở cổng trống đầu tiên từ 5432,
    # nên cluster cũ (nếu có) giữ nguyên cổng của nó.
    info "Cài PostgreSQL $PG_MAJOR"
    sudo apt-get install -y -qq "postgresql-$PG_MAJOR"
  fi

  if ! pg_lsclusters -h | awk -v v="$PG_MAJOR" '$1 == v && $2 == "main"' | grep -q .; then
    sudo pg_createcluster "$PG_MAJOR" main --port "$(free_port_from 5432)"
  fi
  PG_PORT="$(pg_lsclusters -h | awk -v v="$PG_MAJOR" '$1 == v && $2 == "main" {print $3}')"
  if ! pg_lsclusters -h | awk -v v="$PG_MAJOR" '$1 == v && $2 == "main" {print $4}' | grep -q online; then
    # Cluster chưa chạy: nếu cổng của nó đã bị tiến trình khác giữ thì chuyển sang cổng trống.
    if port_in_use "$PG_PORT"; then
      PG_PORT="$(free_port_from "$PG_PORT")"
      info "Cổng cũ đang bận, đặt cluster $PG_MAJOR/main chạy ở cổng $PG_PORT"
      sudo pg_conftool "$PG_MAJOR" main set port "$PG_PORT"
    fi
    sudo pg_ctlcluster "$PG_MAJOR" main start
  fi
}

debian_psql() { sudo -u postgres psql -X -q -v ON_ERROR_STOP=1 -p "$PG_PORT" -d postgres "$@"; }

# ---------------------------------------------------------------- macOS (Homebrew)

BREW_PREFIX=""

macos_install() {
  command -v brew >/dev/null 2>&1 || die "Chưa có Homebrew. Cài theo https://brew.sh rồi chạy lại."
  info "Tìm bản PostgreSQL mới nhất trên Homebrew"
  brew update --quiet
  PG_MAJOR="$(brew search '/^postgresql@[0-9]+$/' 2>/dev/null | sed -n 's/^postgresql@\([0-9]*\)$/\1/p' | sort -n | tail -n1)"
  [ -n "$PG_MAJOR" ] || die "Không tìm thấy formula postgresql@<major> trên Homebrew."

  local formula="postgresql@$PG_MAJOR"
  if brew list --versions "$formula" >/dev/null 2>&1; then
    info "PostgreSQL $PG_MAJOR (bản mới nhất) đã có sẵn, dùng luôn"
  else
    info "Cài $formula"
    brew install "$formula"
  fi
  BREW_PREFIX="$(brew --prefix "$formula")"

  local data_dir conf
  data_dir="$(brew --prefix)/var/$formula"
  conf="$data_dir/postgresql.conf"
  [ -f "$conf" ] || die "Không thấy $conf; thử 'brew reinstall $formula'."

  PG_PORT="$(sed -n 's/^[[:space:]]*port[[:space:]]*=[[:space:]]*\([0-9]*\).*/\1/p' "$conf" | tail -n1)"
  PG_PORT="${PG_PORT:-5432}"

  # Xét postmaster.pid của chính cluster này; pg_isready có thể trả lời thay cho cluster khác cùng cổng.
  local pid_file="$data_dir/postmaster.pid"
  if ! { [ -f "$pid_file" ] && kill -0 "$(head -n1 "$pid_file")" 2>/dev/null; }; then
    # Cluster chưa chạy: nếu cổng đang bị cluster khác giữ thì chuyển sang cổng trống.
    if port_in_use "$PG_PORT"; then
      PG_PORT="$(free_port_from "$PG_PORT")"
      info "Cổng cũ đang bận, đặt $formula chạy ở cổng $PG_PORT"
      printf '\nport = %s\t\t\t\t# đặt bởi scripts/setup/postgres.sh\n' "$PG_PORT" >>"$conf"
    fi
    brew services start "$formula"
  fi
}

macos_psql() { "$BREW_PREFIX/bin/psql" -X -q -v ON_ERROR_STOP=1 -h localhost -p "$PG_PORT" -d postgres "$@"; }

# ---------------------------------------------------------------- Chung

admin_psql() { if [ "$OS" = macos ]; then macos_psql "$@"; else debian_psql "$@"; fi; }

wait_ready() {
  local i
  for i in $(seq 1 30); do
    admin_psql -tAc 'SELECT 1' >/dev/null 2>&1 && return 0
    sleep 1
  done
  die "PostgreSQL $PG_MAJOR không phản hồi ở cổng $PG_PORT."
}

create_role_and_db() {
  info "Tạo role '$DB_USER' và database '$DB_NAME'"
  admin_psql <<SQL
DO \$\$
BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
    ALTER ROLE $DB_USER LOGIN CREATEDB PASSWORD '$DB_PASSWORD';
  ELSE
    CREATE ROLE $DB_USER LOGIN CREATEDB PASSWORD '$DB_PASSWORD';
  END IF;
END
\$\$;
SQL
  if [ "$(admin_psql -tAc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'")" != 1 ]; then
    admin_psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER"
  else
    # Database có sẵn (vd. tạo tay bằng user postgres): migration cần chủ database để tạo extension.
    admin_psql -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER"
  fi
}

check_extensions() {
  # Extension do migration tạo (giống CI và RDS); ở đây chỉ kiểm tra có sẵn để cài.
  local ext missing=()
  for ext in "${EXTENSIONS[@]}"; do
    [ "$(admin_psql -tAc "SELECT 1 FROM pg_available_extensions WHERE name = '$ext'")" = 1 ] || missing+=("$ext")
  done
  [ ${#missing[@]} -eq 0 ] || die "Thiếu extension: ${missing[*]} (cần gói contrib của PostgreSQL $PG_MAJOR)."
}

check_login() {
  info "Thử đăng nhập bằng '$DB_USER' qua TCP"
  local psql_bin=psql
  [ "$OS" = macos ] && psql_bin="$BREW_PREFIX/bin/psql"
  PGPASSWORD="$DB_PASSWORD" "$psql_bin" -X -q -h localhost -p "$PG_PORT" -U "$DB_USER" -d "$DB_NAME" -tAc 'SELECT 1' >/dev/null \
    || die "Không đăng nhập được bằng '$DB_USER' tại localhost:$PG_PORT; kiểm tra pg_hba.conf."
}

main() {
  check_tools
  if [ "$OS" = macos ]; then macos_install; else debian_install; fi
  wait_ready
  create_role_and_db
  check_extensions
  check_login

  cat <<EOF

PostgreSQL $PG_MAJOR đang chạy ở cổng $PG_PORT, database '$DB_NAME' sẵn sàng.

Ghi vào .env ở gốc repo:
  DATABASE_URL=postgres://$DB_USER:$DB_PASSWORD@localhost:$PG_PORT/$DB_NAME
  PG_PORT=$PG_PORT

Container trong Docker Compose tự dùng host.docker.internal:$PG_PORT (xem 08 mục 7).
Bước tiếp theo: make up && make migrate && make seed
EOF
}

main
