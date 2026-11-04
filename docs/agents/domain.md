# Tài liệu domain

Cách các skill engineering đọc tài liệu domain của repo khi tìm hiểu codebase.

## Đọc trước khi tìm hiểu

- **`GLOSSARY.md`** ở gốc repo.
- **`docs/adr/`**: đọc các ADR liên quan tới khu vực sắp làm.
- Khi việc đang làm chạm tới quy tắc nghiệp vụ hoặc vòng đời Đơn hàng, đọc thêm `docs/business/04-business-rules.md` và `docs/business/05-order-lifecycle.md`.

Nếu file nào chưa có thì **bỏ qua, không báo**. Không đề xuất tạo trước. Skill `/domain-modeling` (gọi qua `/grilling` và `/improve-codebase-architecture`) tạo chúng khi thuật ngữ hoặc quyết định thực sự được chốt.

## Cấu trúc

Repo này là single-context:

```
/
├── GLOSSARY.md
├── docs/adr/
│   ├── 0001-nextjs-frontend-django-api.md
│   └── …
├── manage.py, config/, …   # Django project ở gốc repo (ADR 0018)
```

## Dùng đúng thuật ngữ trong glossary

Khi kết quả của bạn gọi tên một khái niệm domain (tiêu đề ticket, đề xuất refactor, giả thuyết, tên test), dùng đúng thuật ngữ trong `GLOSSARY.md`. Không dùng các từ đồng nghĩa mà glossary đã ghi ở mục _Avoid_.

Nếu khái niệm cần dùng chưa có trong glossary, đó là tín hiệu: hoặc bạn đang tự đặt ra từ mà dự án không dùng (cân nhắc lại), hoặc glossary thật sự còn thiếu (ghi lại để xử lý bằng `/domain-modeling`).

## Báo khi mâu thuẫn với ADR

Nếu kết quả của bạn mâu thuẫn với một ADR có sẵn, nói rõ ra thay vì lặng lẽ làm khác:

> _Mâu thuẫn với ADR-0007 (sự kiện qua Outbox + Celery), nhưng đáng xem lại vì…_
