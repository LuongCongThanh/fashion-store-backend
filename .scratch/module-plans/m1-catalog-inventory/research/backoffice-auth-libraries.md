# Nghiên cứu thư viện cho back-office auth

Ngày tra cứu: 04/11/2026.

## PyJWT 2.15.1

- Dùng `jwt.encode(..., algorithm="EdDSA", headers={"kid": ...})` để phát token.
- Chỉ đọc header chưa xác minh để lấy `kid`, rồi tra đúng public key trong keyring nội bộ.
  Không dùng URL hoặc key do token cung cấp.
- Decode với allow-list cố định `algorithms=["EdDSA"]`, `issuer=`, `audience=` và
  `options={"require": [...]}`. Sau decode vẫn kiểm kiểu claim, `token_use`, UUID, `tv >= 0`,
  `iat <= exp` và future `iat` trong leeway 30 giây.
- Nguồn: [PyJWT 2.15.1](https://pyjwt.readthedocs.io/en/stable/),
  [usage/required claims](https://pyjwt.readthedocs.io/en/latest/usage.html#requiring-presence-of-claims).

## redis-py 8.1

- Dùng `Redis.register_script()` cho state transition atomic của failure ledger. `Script` dùng
  `EVALSHA`, tự nạp và retry khi Redis trả `NOSCRIPT`.
- Truyền mọi key qua `keys=` và dữ liệu qua `args=`; không ghép email/IP thô vào Lua hay log.
- Nguồn: [redis-py Lua scripting](https://redis.readthedocs.io/en/v6.3.0/lua_scripting.html),
  [redis-py 8 Script source](https://redis.readthedocs.io/en/latest/_modules/redis/commands/core.html).

## Django và Django REST Framework

- Đặt `Argon2PasswordHasher` đầu `PASSWORD_HASHERS`; giữ các hasher mặc định còn lại để xác
  minh/nâng cấp hash cũ. Test tiếp tục dùng hasher nhanh trong settings test khi không kiểm chính
  thuật toán hash.
- Custom authentication kế thừa `BaseAuthentication`: không có Bearer thì trả `None`; đã thử
  Bearer nhưng token sai thì ném `AuthenticationFailed`; implement `authenticate_header()` để
  lỗi unauthenticated là HTTP 401 có `WWW-Authenticate: Bearer`.
- Nguồn: [Django password management](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/),
  [DRF custom authentication](https://www.django-rest-framework.org/api-guide/authentication/).

## Kết luận

Tái dùng primitive của PyJWT, redis-py, Django và DRF; code của ticket chỉ sở hữu key selection,
claim contract, persistence, failure-ledger state machine và mapping lỗi theo tài liệu dự án.
