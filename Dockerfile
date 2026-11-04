# Một image cho worker, beat, relay, migrate (08 mục 7). API chạy trên máy, không trong
# container (ADR 0017).
FROM ghcr.io/astral-sh/uv:0.13.5 AS uv

FROM python:3.14.9-slim

COPY --from=uv /uv /usr/local/bin/uv

# Venv ở /opt/venv, ngoài /app: Compose bind mount gốc repo vào /app, nên .venv của máy
# không đè lên venv của container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Cài dependency trước khi chép code để đổi code không phải cài lại.
# --locked: lỗi nếu uv.lock lệch pyproject.toml; --no-build: chỉ cài wheel, giống CI
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-build --no-dev

# Chép tường minh phần code chạy được, không chép cả thư mục (tránh lọt file nhạy cảm vào image)
COPY manage.py ./
COPY config ./config
COPY shared ./shared
COPY modules ./modules

RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
USER app
