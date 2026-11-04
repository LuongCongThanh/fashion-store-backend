# Module `shipping`

> Trạng thái: **Đã chốt cho MVP**, code _(kế hoạch)_. Khuôn chung: [02 mục 4](../02-backend-structure.md#4-khuôn-mẫu-một-module).

## 1. Sở hữu

Báo giá Phí ship, Vận đơn GHN, webhook, Đối soát Vận đơn, ánh xạ địa chỉ sang mã của GHN, cấu hình Phí ship dự phòng.

`shipping` ở lớp 3 và **không biết gì về Đơn hàng**: chỉ làm việc với `reference` (Mã đơn) và báo kết quả lên bằng sự kiện. Code gọi API GHN nằm ở `infrastructure/shipping/`.

## 2. Cây thư mục

```
apps/shipping/
├── apps.py                    # name = "apps.shipping", label = "shipping"
├── contracts.py               # mục 4.1
├── events.py                  # mục 4.2
├── exceptions.py
├── constants.py               # ShipmentStatus (có creation_unknown, cancel_requested)…
├── models.py                  # Shipment, ShipmentEvent (webhook gốc), GhnLocationMapping, ShippingSettings
├── services.py                # báo giá, tạo/huỷ Vận đơn, ghi webhook
├── tasks.py                   # mục 5.2
├── api/
│   ├── webhooks/              # POST /api/v1/webhooks/ghn
│   └── backoffice/            # settings/ghn-locations
├── migrations/
└── tests/                     # soi gương cây ở trên; factories.py

infrastructure/shipping/       # không phải module; chỉ shipping được import
├── base.py                    # interface ShippingProvider: quote, create_shipment, find_by_client_code,
│                              # get_status, cancel_shipment
├── ghn.py
└── fake.py                    # chỉ dùng được khi FAKE_PROVIDERS_ENABLED
```

## 3. Quan hệ với module khác

```mermaid
graph LR
    ordering -->|"quote_fee, request_shipment<br/>request_shipment_cancellation<br/>get_shipment_status<br/>redact_provider_payloads"| shipping((shipping))
    shipping -->|"FK GhnLocationMapping → Ward"| geo
    shipping -->|"ShippingProvider"| ghn[infrastructure.shipping]

    shipping -.->|"shipment-created, shipment-creation-failed<br/>shipment-delivered, shipment-returned<br/>shipment-exception"| ordering
```

## 4. Public API

### 4.1. `contracts.py`

Trừ `quote_fee`, mọi hàm chỉ đọc, ghi DB và đẩy task sau commit, nên gọi trong transaction (kể cả trong handler) là an toàn. HTTP tới GHN chỉ chạy trong task.

| Hàm | Ghi chú |
|---|---|
| `quote_fee(ward_code, weight_grams, value) -> ShippingQuoteDTO` | Gọi GHN trực tiếp nên phải gọi **ngoài** transaction. Cache theo hash toàn bộ request đã chuẩn hoá (gồm cấu hình shop, service, kích thước, mapping); không cache Phí ship dự phòng chung với giá GHN thật. `ordering` tự áp Ngưỡng miễn phí ship |
| `request_shipment(ShipmentRequestDTO)` | Tạo Vận đơn `requested` với snapshot và mã shop ổn định, đẩy task sau commit. Dùng lại Vận đơn `failed` chỉ khi chắc chắn chưa có Vận đơn bên ngoài; `creation_unknown` thì không tạo lại |
| `request_shipment_cancellation(reference)` | Ghi `cancel_requested`, đẩy task `cancel_shipment` sau commit |
| `get_shipment_status(reference) -> ShipmentStatusDTO \| None` | |
| `redact_provider_payloads(reference)` | Ẩn danh dữ liệu webhook gốc |

### 4.2. `events.py`

| Sự kiện | Phát khi |
|---|---|
| `ShipmentCreatedV1` | Tạo Vận đơn thành công chắc chắn |
| `ShipmentCreationFailedV1` | Tạo Vận đơn thất bại chắc chắn |
| `ShipmentDeliveredV1` | GHN báo đã giao |
| `ShipmentReturnedV1` | GHN báo Hoàn hàng |
| `ShipmentExceptionV1` | Sự cố Vận đơn: GHN báo mất hàng, hư hàng, sự cố, hoặc tự huỷ Vận đơn mà hệ thống không yêu cầu (`provider_status`) |

## 5. Quy tắc riêng

### 5.1. Tạo và huỷ Vận đơn

- Task `create_shipment` (queue `integrations`): claim lease, tra theo mã shop trước khi retry. Chỉ khi biết chắc kết quả mới phát `ShipmentCreatedV1` hoặc `ShipmentCreationFailedV1`; timeout thì giữ `creation_unknown` ([06 mục 4.3](../06-integrations.md#43-khôi-phục-tạo-vận-đơn-chưa-rõ-kết-quả)).
- Task `cancel_shipment` (queue `integrations`, có retry): thành công thì Vận đơn `cancelled`. Hết retry thì giữ `cancel_requested` và báo Sentry; Staff xử lý tay theo Cờ cần xử lý `shipment_after_cancel`.
- `GhnLocationMapping` ánh xạ `geo.Ward` sang ID của GHN; Admin sửa qua back-office. Service tra mapping rồi truyền mã vào adapter; adapter không đọc database.

### 5.2. Job

| Task | Tần suất | Việc |
|---|---|---|
| `reconcile_shipments` | Mỗi 15 phút | Đối soát: quét `requested`/`creation_unknown` hết lease để tra theo mã shop; `cancel_requested` quá 15 phút thì thử huỷ lại; chỉ hỏi GHN về Vận đơn không có cập nhật trong 6 giờ ([06](../06-integrations.md) mục 4) |

## 6. Tài liệu liên quan

- Schema: [03 mục 7](../03-data-model.md#7-shipping)
- Tích hợp GHN, ánh xạ trạng thái, địa chỉ 2 cấp và 3 cấp: [06](../06-integrations.md) mục 4
- Quyết định: [ADR 0005](../../adr/0005-provider-adapters-fake-gateways.md)
