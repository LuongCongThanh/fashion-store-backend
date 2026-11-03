# Hướng dẫn đóng góp

Đọc theo thứ tự:

1. [GLOSSARY.md](./GLOSSARY.md): thuật ngữ dùng chung trong code và tài liệu.
2. [Môi trường phát triển local](./docs/architecture/08-local-development.md): cài đặt trên macOS hoặc Windows.
3. [Cấu trúc Backend](./docs/architecture/02-backend-structure.md): module, quy tắc từng file, ranh giới giữa các module.
4. [Coding style Python/Django](./docs/architecture/13-python-django-coding-style.md): quy ước bắt buộc khi viết và review code.
5. [Quy ước Git](./docs/architecture/11-git-workflow.md): nhánh, commit, PR, release.

## Tóm tắt quy trình

```bash
git switch dev
git pull --ff-only origin dev
git switch -c feat/<mo-ta-ngan>
# code + test
cd backend
make fmt
make lint
make test
cd ..
git push -u origin feat/<mo-ta-ngan>
# mở PR vào dev, tiêu đề theo Conventional Commits
```

| Quy tắc | Chi tiết |
|---|---|
| Nhánh chính | `main` (production) ← `uat` (nghiệm thu, triển khai lên staging) ← `dev` (tích hợp) ← nhánh tính năng |
| Commit, tên nhánh, tiêu đề PR | Tiếng Anh, theo Conventional Commits: `feat(ordering): add COD checkout` |
| Merge vào `dev` | Squash merge |
| Merge `dev` → `uat` và `uat` → `main` | Merge commit (không squash) |
| Push thẳng vào `dev` | Chỉ khi thay đổi nhỏ, gấp và đã chạy `make fmt`, `make lint`, `make test` |
| Push thẳng vào `uat` hoặc `main` | Không được |
| Force-push | Chỉ trên nhánh tính năng của mình, không bao giờ trên `dev`, `uat` hoặc `main` |

## Quy ước code

Chi tiết ở [Coding style Python/Django](./docs/architecture/13-python-django-coding-style.md). Tóm tắt:

- Tên trong code bằng tiếng Anh; comment và docstring bằng tiếng Việt.
- Hàm service đặt tên `<verb>_<noun>` (`place_order`); selector dùng `get_` / `find_` / `list_`.
- Format bằng `ruff format` (dòng tối đa 100 ký tự), lint bằng `ruff check` + `mypy` + `lint-imports`. Chạy `make fmt` trước khi commit.
- Docstring Google style, bắt buộc cho hàm public trong `contracts.py` và `services/`.
- Model kế thừa `shared.models.BaseModel` (khoá chính UUID v7), không tự khai báo `id`. Tên thuộc tính class không trùng tên field chỉ khác hoa/thường (alias `Status` cạnh field `status`); dùng thẳng class `TextChoices` ở cấp module.
- Cột NOT NULL thêm vào bảng đã có khai báo `db_default`, không chỉ `default`: `default` làm migration `DROP DEFAULT`, code bản cũ còn chạy trong lúc rolling deploy INSERT lỗi (09 mục 4, migration tương thích ngược).
- Test: dữ liệu tạo bằng `factory-boy`, không mock ORM, chỉ giả lập hệ thống bên ngoài. Branch coverage của `services/` và `handlers.py` tối thiểu 80%, tính riêng từng module.
- Hành vi dựa vào việc một transaction đã commit (code chạy nhiều transaction nối tiếp, `on_commit`, khoá giữa các kết nối) test bằng `@pytest.mark.django_db(transaction=True)`; `django_db` thường bọc test trong một transaction nên `transaction.atomic()` bên trong chỉ là savepoint.
- Model chỉ dùng trong test mà kế thừa `BaseModel` khai báo lại `objects = BaseQuerySet.as_manager()`, nếu không mypy chạy từ đầu (như CI) suy sai kiểu manager.
- Trong khối `pytest.raises` chỉ có một lời gọi có thể ném lỗi: dựng tham số, object, decorator và mở context manager khác (`transaction.atomic()`) ở trước khối. Assert viết `actual == expected`, giá trị kỳ vọng ở vế phải; giá trị thực là tuple/list dựng tại chỗ hoặc hằng viết hoa thì gán vào biến trước (`after = (a.x, a.y)`), vì SonarCloud đọc chúng là giá trị kỳ vọng còn ruff `SIM300` đòi đặt hằng ở vế trái.
- Log bằng `structlog.get_logger(__name__)`, message là tên sự kiện `snake_case` kèm keyword, không f-string. Không log PII, token hay payload thanh toán.
- Exception gốc có thể chứa secret (URL kết nối, khoá, phần URL bị parse sai) thì raise lỗi mới `from None`, để traceback chỉ in thông báo đã lọc.
- Lặp trên dict mà cần hai giá trị thì dùng `.items()`; không tách cặp từ key là tuple (`for a, b in d`), SonarCloud báo lỗi. Bỏ trùng giữ thứ tự cho dữ liệu dạng cặp thì dựng list.

## Bảo mật khi dùng AI agent

- `.claude/settings.json` có rule `deny` chặn Claude Code đọc `.env*` (trừ `.env.example`), `.secrets/` và `*.pem`. Không xoá hoặc ghi đè các rule này trong `settings.local.json`.
- Mở Claude Code từ **gốc repo**. Rule chỉ áp dụng cho thư mục đang mở và các thư mục con, nên mở từ `docs/` thì `.env` ở gốc repo không được bảo vệ.
- Rule không chặn được script tự đọc file (ví dụ một script Python mở `.env`). Đừng chạy lệnh do agent đề xuất nếu lệnh đó in nội dung secret.
- Không dán secret, token hoặc dữ liệu khách hàng thật vào prompt.

## Khi nào cần cập nhật tài liệu

Tài liệu đã chốt cho MVP; code chạm tới phần nào thì sửa tài liệu phần đó **trong cùng PR** ([quy ước](./README.md#trạng-thái-tài-liệu)).

- Thêm hoặc đổi thuật ngữ nghiệp vụ → `GLOSSARY.md`.
- Đổi quy tắc nghiệp vụ → `docs/business/04-business-rules.md` (giữ mã `BR-xxx`).
- Quyết định khó đảo ngược, có đánh đổi thật → thêm ADR mới trong `docs/adr/`.
- Thêm endpoint → OpenAPI tự sinh; chỉ cập nhật `docs/architecture/04-api-contract.md` nếu đổi quy ước chung.
