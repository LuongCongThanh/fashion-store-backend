# Sự kiện qua outbox: publisher, relay, consumer và retry

Status: resolved

**PR:** #36

Blocked by: 09, 15

Spec: [spec.md](../../spec.md)

Các lệnh vận hành và hàm theo dõi tách sang ticket [18](../18-outbox-operations/spec.md).

## Việc cần làm

Làm đúng [07 mục 1 và 3](../../../../docs/architecture/07-async-events-jobs.md) và [ADR 0007](../../../../docs/adr/0007-events-outbox-celery-no-kafka.md):

- Model `OutboxEvent`, `EventDelivery` theo [03 mục 1.3–1.4](../../../../docs/architecture/03-data-model.md#13-common_outbox_event-sự-kiện-chờ-phát).
- `DomainEvent` (pydantic), `publish()` ghi outbox trong transaction hiện tại, decorator `@handles(event_type, version)`.
- Relay (`manage.py run_outbox_relay`): lập delivery cho từng handler, giao các delivery `pending` tới hạn qua Celery, `FOR UPDATE SKIP LOCKED`, chạy hai bản cùng lúc vẫn an toàn. Thêm service `relay` vào `docker-compose.yml` ([08 mục 7](../../../../docs/architecture/08-local-development.md#7-docker-composeyml-rút-gọn)).
- Consumer: khoá delivery, chạy handler trong savepoint, chuyển `completed`/`rejected`/`failed` cùng transaction với tác động DB; `RetryLater` và lịch retry lưu trong DB.
- `shared.tasks.enqueue_on_commit`.
- `shared.testing.events.drain_events()` cho flow test.

## Quyết định

Chốt khi grilling ngày 30/10/2026.

| Chủ đề | Quyết định |
|---|---|
| Tài liệu chi phối | `shared/events/models.py`, `shared/migrations/0003_*`, `shared/models.py`: 03 §1.3–1.4, 02 §9.1 (khoá chính), §9.2 (tên bảng), ADR 0007, ADR 0008. `shared/events/base.py`, `publisher.py`, `registry.py`, `__init__.py`: 07 §1, §2 (version, payload không PII), 02 §5 (cây `shared/events/`), §9.2 (tên class sự kiện, `event_type`). `shared/events/relay.py`, `management/commands/run_outbox_relay.py`: 07 §1.1.1, §1.3. `shared/events/consumer.py`, `shared/events/tasks.py`: 07 §1.1.1, §1.3, §3.1 (queue `events`), 02 §9.2 (tên Celery task). `shared/tasks.py`: 02 §9.1 (*Việc ra ngoài DB*), 07 §1.3. `shared/testing/events.py`: 12 §2.7, 02 §9.5. `config/celery.py`, `config/settings/base.py`: 07 §3.1, §3.3, 02 §5 (`autodiscover_tasks`). `docker-compose.yml`, `Makefile`: 08 §7. Test: 07 §5, 12 §2.2, §2.3, 02 §9.2 (tên file test), §9.5 (factory, time-machine) |
| Model | `OutboxEvent` (`shared_outbox_event`) và `EventDelivery` (`shared_event_delivery`) đúng cột, `CHECK`, `UNIQUE`, partial index của 03 §1.3–1.4. Kế thừa `models.Model`, không kế thừa `BaseModel`: 03 không có `created_at`/`updated_at` cho hai bảng này. `OutboxEvent.id` UUID PK `default=uuid7` (= `event_id`); `EventDelivery` có `id` UUID v7 riêng (ADR 0008), FK `event` `db_column="event_id"` `CASCADE`. `status` là `TextChoices` `pending/completed/rejected/failed`. `shared/models.py` import hai model như với `geo` |
| `DomainEvent` | pydantic `BaseModel` frozen trong `shared/events/base.py`: `event_id` (UUID v7), `occurred_at`, `correlation_id: str \| None` (lấy `request_id` từ contextvars của structlog nếu có); class con khai báo `event_type: ClassVar[str]`, `schema_version: ClassVar[int]`. `__init_subclass__` đăng ký class theo `(event_type, schema_version)`, trùng thì ném lỗi khi import. Payload lưu là `model_dump(mode="json")` trừ `event_id`, `occurred_at` (đã là cột) |
| `publish()` | `shared.events.publish(event)` ghi `OutboxEvent` trong transaction hiện tại; không tự mở transaction, gọi ngoài `transaction.atomic` thì ném `RuntimeError` (thêm khi review, B4). `EventPublisher` là class trong `publisher.py`, `publish` là hàm gọi instance mặc định (chỗ cắm adapter Kafka ở ADR 0007) |
| `@handles` | `@handles(event_type, version=1, name="<module>.<snake_case>")`: `name` bắt buộc, là cột `handler` của delivery, ổn định khi đổi tên file/hàm (giống tên Celery task, 02 §9.2). Trùng `name` hoặc `name` dài quá 100 ký tự (`HANDLER_NAME_MAX_LENGTH`, cột `handler`) ném lỗi khi import (độ dài thêm khi review, B10). `shared.events.registry.autodiscover(package)` nạp `events.py`, `handlers.py` của package con; `ModulesConfig.ready()` gọi `autodiscover("modules")` theo 02 §5 (thêm khi review, B1). Handler nhận instance của class sự kiện đã parse từ payload. Registry ở `registry.py` |
| Relay | `relay.create_deliveries(batch=100)`: khoá `OutboxEvent` chưa có `deliveries_created_at` bằng `select_for_update(skip_locked=True)`, tạo delivery cho mọi handler đăng ký (`bulk_create(ignore_conflicts=True)` trên `UNIQUE(event_id, handler)`), ghi `deliveries_created_at`, cùng transaction; không có handler thì vẫn ghi marker và log `outbox_event_no_handlers`. `relay.dispatch_due(batch=100)`: khoá delivery `pending` có `next_attempt_at ≤ now` và `next_dispatch_at ≤ now` (skip locked), đặt `next_dispatch_at = now + 3 phút`, `last_dispatched_at = now`, commit, rồi mới `dispatch_event.apply_async(...)` (queue `events` do decorator của task định tuyến); chỉ bắt `kombu` `OperationalError`: dừng cả lô ở lỗi đầu, log `WARNING` `outbox_dispatch_failed` kèm `deferred`, các delivery giữ hạn đã lưu; lỗi khác ném ra (07 §1.3, thêm khi review, B5/T3). `run_outbox_relay` lặp hai hàm mỗi 1 giây, mỗi hàm `try` riêng để lỗi bước đầu không chặn bước sau (thêm khi review, B2), dừng sạch khi nhận SIGTERM/SIGINT, có `--once` cho test. Sentry Cron check-in (07 §3.4) chưa làm: Sentry chưa cấu hình ở M0 |
| Consumer | `consumer.process_delivery(event_id, handler_name)` trong `transaction.atomic`: khoá delivery (`select_for_update`, chờ khoá); bỏ qua nếu không còn `pending` hoặc `next_attempt_at > now`. Handler chạy trong savepoint. Kết thúc bình thường → `completed`, `completed_at`. `DomainError` → `rejected`, log `WARNING` `event_rejected` với `event_type`, `handler`, `code`. `RetryLater` hoặc `Exception` khác → `attempts += 1`, `last_error`, `next_attempt_at = next_dispatch_at = now + lịch[attempts-1]` (`now` lấy sau khi handler chạy, cũng dùng cho `completed_at`, `failed_at`; thêm khi review, B8); khi `attempts > 5` → `failed`, `failed_at`, log `ERROR` `event_delivery_failed` (Sentry bắt log ERROR). `DatabaseError` ngoài savepoint không bắt, để toàn transaction rollback (07 §1.3). Handler không có trong registry → giữ `pending`, log `ERROR` `event_handler_missing`, không tăng `attempts` |
| Lịch retry | Hằng `RETRY_DELAYS = (10s, 1m, 5m, 15m, 30m)` trong `consumer.py` (07 §1.3); hết 5 lần retry sau lần đầu → `failed` |
| `last_error` | Chỉ tên class và `code` nếu có, ví dụ `InvalidTransition(INVALID_TRANSITION)`, cắt 500 ký tự; không ghi message để không lọt PII (03 §1.4). Traceback đầy đủ đi qua `logger.exception` |
| Celery task | `shared.events.tasks.dispatch_event(event_id, handler_name)`, `name="shared.dispatch_event"`, queue `events`; chỉ gọi `process_delivery`. `config/celery.py` autodiscover thêm `shared.events` |
| Cấu hình Celery (yêu cầu thêm) | `config/settings/base.py` thêm 07 §3.3: `CELERY_TASK_ACKS_LATE`, `CELERY_TASK_REJECT_ON_WORKER_LOST`, `CELERY_WORKER_PREFETCH_MULTIPLIER = 1`, `CELERY_TASK_TIME_LIMIT = 120`, `CELERY_TASK_IGNORE_RESULT`. Người dùng yêu cầu ngày 30/10/2026: hạn giao lại 3 phút dựa vào time limit 120 giây |
| `enqueue_on_commit` | `shared.tasks.enqueue_on_commit(task_name, **kwargs)`: `transaction.on_commit(..., robust=True)` gọi `app.tasks[task_name].apply_async(kwargs=kwargs)`. Lấy task theo tên trong registry của app (không `send_task`) để `CELERY_TASK_ALWAYS_EAGER` của test có hiệu lực và tên sai lộ ra ngay. Không dùng `apply_async_on_commit` của Celery vì nó cần object task, mà code nghiệp vụ chỉ biết tên |
| `drain_events()` | `shared/testing/events.py`: chạy callback `on_commit` đang chờ trên kết nối hiện tại, rồi lặp `create_deliveries` + `dispatch_due` (Celery eager nên handler chạy ngay) tới khi không còn sự kiện chưa lập danh sách và không còn delivery tới hạn; giới hạn 100 vòng rồi ném lỗi để tránh lặp vô hạn |
| Compose | Service `relay` (`<<: *app`, `command: python manage.py run_outbox_relay`) như 08 §7; `make restart-worker` khởi động lại cả `relay` |
| Test | `shared/events/tests/` theo 07 §5: `test_publisher.py`, `test_relay.py`, `test_consumer.py`, `test_drain.py`; `shared/tests/test_tasks.py` cho `enqueue_on_commit`. Sự kiện và handler mẫu khai báo trong `shared/events/tests/conftest.py`, registry được khôi phục sau mỗi test; tác động DB của handler ghi vào model test tạo bằng `schema_editor` như `shared/tests/test_models.py`. Giao trùng đồng thời và hai relay cùng chạy: `django_db(transaction=True)` + thread + `threading.Barrier` trên PostgreSQL thật (12 §2.2); marker `concurrency` để ticket [02](../02-pytest-markers-and-br-report/spec.md) khai báo. Thời gian cố định bằng `time-machine`. `backend/tests/test_event_payloads.py` (07 §5) làm ở ticket này: hiện chưa có sự kiện thật, test kiểm hàm dò tên field cấm trên class mẫu và chạy trên mọi class đã đăng ký |
| Ngoài phạm vi | `delivery_lag`, `get_delivery_outcomes`, purge, `retry_failed_events`, `replay_events`: ticket [18](../18-outbox-operations/spec.md). Sentry Cron check-in của relay: khi cấu hình Sentry |

## Acceptance criteria

- [x] Một sự kiện mẫu có hai handler: mỗi handler chạy đúng một lần dù task bị giao lặp.
- [x] Transaction ghi sự kiện bị rollback thì không có delivery nào được tạo.
- [x] Handler ném `RetryLater` thì delivery giữ `pending` với `next_attempt_at` theo lịch retry; hết retry thì `failed` có `failed_at`, `last_error`.
- [x] Handler lỗi không làm hỏng tác động DB của handler khác cùng sự kiện.
- [x] Redis mất task sau khi đã nhận thì relay giao lại khi tới `next_dispatch_at`.
- [x] `make up` bật cả `relay`, và service này không khởi động lại liên tục.
- [x] Các kịch bản ở [07 mục 5](../../../../docs/architecture/07-async-events-jobs.md#5-kịch-bản-kiểm-thử) về publish, relay, consumer và retry đều có test.
