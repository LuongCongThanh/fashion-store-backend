#Requires -Version 7
# Tạo role/database `fashion` trên PostgreSQL cài thẳng trên Windows (bộ cài EDB hoặc winget).
# Script không cài PostgreSQL: việc cài cần quyền Admin và mật khẩu superuser, làm tay một lần.
# Chạy lại nhiều lần vẫn an toàn. Xem docs/architecture/08-local-development.md mục 2.2
# và docs/adr/0017-windows-native-dev-api-on-host.md.
[CmdletBinding()]
param([switch]$Help)

$ErrorActionPreference = 'Stop'

$DbUser = 'fashion'
$DbPassword = 'fashion'
$DbName = 'fashion'
$Extensions = @('unaccent', 'pg_trgm', 'btree_gist')
$MinUvVersion = [version]'0.13'

function Info([string]$Message) { Write-Host "==> $Message" -ForegroundColor Blue }
function Warn([string]$Message) { Write-Host "[!] $Message" -ForegroundColor Yellow }
function Die([string]$Message) { Write-Host "[x] $Message" -ForegroundColor Red; exit 1 }

if ($Help) {
    @"
Cách dùng: pwsh scripts/setup/postgres.ps1

Tìm PostgreSQL bản major cao nhất đã cài trên Windows, hỏi mật khẩu 'postgres'
(hoặc lấy từ biến môi trường PGPASSWORD), tạo role '$DbUser' (quyền CREATEDB)
và database '$DbName', rồi in DATABASE_URL. Không lưu mật khẩu 'postgres'.
"@
    exit 0
}

if (-not $IsWindows) { Die 'Script này chỉ dành cho Windows. macOS/Ubuntu dùng scripts/setup/postgres.sh.' }

# ---------------------------------------------------------------- Công cụ khác (chỉ kiểm tra)

function Test-Tools {
    Info 'Kiểm tra công cụ (chỉ báo thiếu, không tự cài)'
    foreach ($tool in 'git', 'make', 'docker') {
        if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { Warn "Thiếu '$tool' (xem 08 mục 2.1)." }
    }
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        $uvVersion = [version](((uv --version) -split ' ')[1])
        if ($uvVersion -lt $MinUvVersion) { Warn "uv $uvVersion cũ hơn $MinUvVersion, chạy 'uv self update'." }
    }
    else {
        Warn "Thiếu 'uv' (xem 08 mục 2.1)."
    }
}

# ---------------------------------------------------------------- Tìm cluster

function Get-LatestWingetMajor {
    try {
        $out = winget search --id PostgreSQL.PostgreSQL. --source winget --accept-source-agreements 2>$null
        $majors = $out | Select-String 'PostgreSQL\.PostgreSQL\.(\d+)' -AllMatches |
            ForEach-Object { $_.Matches } | ForEach-Object { [int]$_.Groups[1].Value }
        return ($majors | Sort-Object | Select-Object -Last 1)
    }
    catch { return $null }
}

function Find-Cluster {
    # Bộ cài EDB đăng ký service postgresql-x64-<major>, chạy pg_ctl với -D <data directory>.
    $services = @(Get-CimInstance Win32_Service -Filter "Name LIKE 'postgresql-x64-%'")
    if ($services.Count -eq 0) {
        $major = Get-LatestWingetMajor
        $id = if ($major) { "PostgreSQL.PostgreSQL.$major" } else { 'PostgreSQL.PostgreSQL.<major>' }
        Write-Host ''
        Write-Host 'Chưa cài PostgreSQL. Cài bản major mới nhất bằng PowerShell quyền Administrator:'
        Write-Host "  winget install $id"
        Write-Host "Bộ cài hỏi mật khẩu cho 'postgres' và cổng (để 5432 nếu trống). Cài xong chạy lại script này."
        exit 1
    }

    $service = $services | Sort-Object { [int]($_.Name -replace '^postgresql-x64-', '') } | Select-Object -Last 1
    $script:PgMajor = $service.Name -replace '^postgresql-x64-', ''
    if ($services.Count -gt 1) { Info "Có nhiều bản PostgreSQL, dùng bản cao nhất: $PgMajor" }
    if ($service.State -ne 'Running') {
        Die "Service $($service.Name) đang $($service.State). Bật bằng PowerShell quyền Administrator: Start-Service $($service.Name)"
    }

    if ($service.PathName -notmatch '^"?(?<pgctl>.+?pg_ctl\.exe)"?\s.*-D\s+"?(?<data>[^"]+)"?') {
        Die "Không đọc được đường dẫn từ service $($service.Name): $($service.PathName)"
    }
    $script:Psql = Join-Path (Split-Path $Matches.pgctl) 'psql.exe'
    if (-not (Test-Path $Psql)) { Die "Không thấy $Psql." }

    # Cổng do bộ cài EDB chọn, ghi trong postgresql.conf; dòng 'port' cuối cùng có hiệu lực.
    $conf = Join-Path $Matches.data 'postgresql.conf'
    $script:PgPort = 5432
    try {
        $line = Get-Content $conf | Select-String '^\s*port\s*=\s*(\d+)' | Select-Object -Last 1
        if ($line) { $script:PgPort = [int]$line.Matches[0].Groups[1].Value }
    }
    catch {
        Warn "Không đọc được $conf, dùng cổng mặc định 5432."
    }
    Info "Dùng PostgreSQL $PgMajor ($($service.Name)) ở cổng $PgPort"
}

# ---------------------------------------------------------------- psql

function Invoke-Psql {
    param([string]$User, [string]$Password, [string]$Database, [string]$Sql)
    # PGPASSWORD chỉ đặt trong lúc gọi psql rồi trả lại giá trị cũ, không ghi ra đâu cả.
    $previous = $env:PGPASSWORD
    $env:PGPASSWORD = $Password
    try {
        $out = $Sql | & $Psql -X -q -v ON_ERROR_STOP=1 -h localhost -p $PgPort -U $User -d $Database -tA 2>&1
        return [pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = ($out | Out-String).Trim() }
    }
    finally {
        $env:PGPASSWORD = $previous
    }
}

function Invoke-AdminSql([string]$Sql) {
    $result = Invoke-Psql -User postgres -Password $AdminPassword -Database postgres -Sql $Sql
    if ($result.ExitCode -ne 0) { Die "psql lỗi: $($result.Output)" }
    return $result.Output
}

function Read-AdminPassword {
    if ($env:PGPASSWORD) {
        $script:AdminPassword = $env:PGPASSWORD
    }
    else {
        $secure = Read-Host "Mật khẩu của 'postgres' (đặt lúc cài PostgreSQL)" -AsSecureString
        $script:AdminPassword = [System.Net.NetworkCredential]::new('', $secure).Password
    }
    $check = Invoke-Psql -User postgres -Password $AdminPassword -Database postgres -Sql 'SELECT 1'
    if ($check.ExitCode -ne 0) { Die "Không đăng nhập được bằng 'postgres' tại localhost:${PgPort}: $($check.Output)" }
}

# ---------------------------------------------------------------- Role, database, extension

function New-RoleAndDatabase {
    Info "Tạo role '$DbUser' và database '$DbName'"
    Invoke-AdminSql @"
DO `$`$
BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = '$DbUser') THEN
    ALTER ROLE $DbUser LOGIN CREATEDB PASSWORD '$DbPassword';
  ELSE
    CREATE ROLE $DbUser LOGIN CREATEDB PASSWORD '$DbPassword';
  END IF;
END
`$`$;
"@ | Out-Null
    if ((Invoke-AdminSql "SELECT 1 FROM pg_database WHERE datname = '$DbName'") -ne '1') {
        Invoke-AdminSql "CREATE DATABASE $DbName OWNER $DbUser" | Out-Null
    }
    else {
        # Database có sẵn (vd. tạo tay bằng pgAdmin với user postgres): migration cần chủ database để tạo extension.
        Invoke-AdminSql "ALTER DATABASE $DbName OWNER TO $DbUser" | Out-Null
    }
}

function Test-Extensions {
    # Extension do migration tạo (giống CI và RDS); ở đây chỉ kiểm tra có sẵn để cài.
    $missing = $Extensions | Where-Object {
        (Invoke-AdminSql "SELECT 1 FROM pg_available_extensions WHERE name = '$_'") -ne '1'
    }
    if ($missing) { Die "Thiếu extension: $($missing -join ', ') (cài lại PostgreSQL $PgMajor bằng bộ cài EDB đầy đủ)." }
}

function Test-Login {
    Info "Thử đăng nhập bằng '$DbUser' qua TCP"
    $result = Invoke-Psql -User $DbUser -Password $DbPassword -Database $DbName -Sql 'SELECT 1'
    if ($result.ExitCode -ne 0) { Die "Không đăng nhập được bằng '$DbUser' tại localhost:${PgPort}; kiểm tra pg_hba.conf. $($result.Output)" }
}

# ---------------------------------------------------------------- main

Test-Tools
Find-Cluster
Read-AdminPassword
New-RoleAndDatabase
Test-Extensions
Test-Login

@"

PostgreSQL $PgMajor đang chạy ở cổng $PgPort, database '$DbName' sẵn sàng.

Ghi vào .env ở gốc repo:
  DATABASE_URL=postgres://${DbUser}:${DbPassword}@localhost:$PgPort/$DbName
  PG_PORT=$PgPort

Container trong Docker Compose tự dùng host.docker.internal:$PgPort (xem 08 mục 7).
Bước tiếp theo: make up && make migrate && make seed
"@
