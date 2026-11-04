#!/bin/sh
# Chạy script Python bằng trình thông dịch Python 3 có trên máy (Linux, macOS, Windows Git Bash).
# Thử python3 trước; bỏ qua stub Microsoft Store vì stub không chạy được lệnh kiểm tra.
for c in python3 python py; do
  if "$c" -c "import sys; sys.exit(sys.version_info < (3,))" >/dev/null 2>&1; then
    exec "$c" "$@"
  fi
done
echo "Không tìm thấy Python 3 (đã thử python3, python, py)" >&2
exit 1
