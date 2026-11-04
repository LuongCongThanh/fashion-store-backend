"""HMAC cho định danh cá nhân bằng keyring `PII_HMAC_KEYS` (ADR 0016).

Dùng cho bằng chứng sau ẩn danh, IP trong log và key failure ledger. Hàm không tự chuẩn hoá
đầu vào: bên gọi đưa số E.164 (`shared.phones.normalize_vn_phone`) hoặc IP đã chuẩn.
"""

import hashlib
import hmac

from django.conf import settings


def _digest(kid: str, secret: str, value: str) -> str:
    mac = hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()
    return f"{kid}:{mac}"


def pii_hmac(value: str) -> str:
    """Trả `<kid>:<hex>` bằng khoá đầu của keyring, dùng khi ghi giá trị mới."""
    kid, secret = settings.PII_HMAC_KEYS[0]
    return _digest(kid, secret, value)


def pii_hmac_candidates(value: str) -> list[str]:
    """Trả giá trị HMAC với mọi khoá còn trong keyring, để tra cứu bằng `__in`.

    Giá trị cũ có thể được ghi bằng khoá đã xoay; khoá cũ không bị xoá khỏi keyring.
    """
    return [_digest(kid, secret, value) for kid, secret in settings.PII_HMAC_KEYS]


def parse_keyring(raw: str) -> tuple[tuple[str, str], ...]:
    """Đọc keyring dạng `kid2:secret2,kid1:secret1` thành các cặp `(kid, secret)`.

    Khoá đầu dùng cho giá trị mới; khoá sau giữ để kiểm tra giá trị cũ (ADR 0016).
    Thông báo lỗi không chứa secret.
    """
    keys: list[tuple[str, str]] = []
    for entry in raw.split(","):
        kid, sep, secret = entry.partition(":")
        # kid đi vào giá trị lưu DB (`<kid>:<hex>`) nên không được giữ khoảng trắng thừa
        kid, secret = kid.strip(), secret.strip()
        if not sep or not kid or not secret:
            raise ValueError("mỗi khoá phải có dạng kid:secret, kid và secret không rỗng")
        if any(kid == seen for seen, _ in keys):
            raise ValueError(f"kid {kid!r} bị trùng")
        keys.append((kid, secret))
    return tuple(keys)
