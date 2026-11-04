# Module `geo`

> Trạng thái: **Đã chốt cho MVP**, đã có code. Khuôn chung: [02 mục 4](../02-backend-structure.md#4-khuôn-mẫu-một-module).

## 1. Sở hữu

- Địa giới hành chính 2 cấp sau 07/2025: 34 tỉnh/thành và phường/xã. Dữ liệu tham chiếu, chỉ đọc khi chạy, không có nghiệp vụ ghi.
- Lớp 2, dưới mọi module nghiệp vụ: `identity` (sổ địa chỉ), `shipping` (ánh xạ GHN), `ordering` (địa chỉ giao) khai FK tới `Ward`.

## 2. Cây thư mục

```
apps/geo/
├── apps.py                    # name = "apps.geo", label = "geo"
├── models.py                  # Province, Ward (bảng geo_province, geo_ward)
├── selectors.py               # list_provinces, province_exists, list_wards
├── api/store/
│   ├── views.py               # ProvinceListView, WardListView
│   └── urls.py                # GET /api/v1/store/geo/provinces, provinces/{code}/wards
├── management/commands/
│   └── load_geo.py            # nạp dữ liệu từ package vietnam-provinces
├── migrations/
└── tests/                     # soi gương cây ở trên; factories.py (ProvinceFactory, WardFactory)
```

## 3. Quan hệ với module khác

```mermaid
graph LR
    identity -->|"FK Address → Ward"| geo((geo))
    shipping -->|"FK GhnLocationMapping → Ward"| geo
    ordering -->|"FK địa chỉ giao → Ward"| geo
```

Không gọi module nào, không phát sự kiện.

## 4. Public API

Chưa có `contracts.py`, `events.py`, `exceptions.py`: module khác chỉ khai FK tới `Ward` và truyền mã phường/xã dạng chuỗi. Thêm contract khi có module cần đọc tên hoặc kiểm tra mã.

## 5. Quy tắc riêng

- Chỉ nạp bằng `load_geo`: upsert theo mã trong một transaction, chạy lại không đổi gì. Không có API ghi.
- Mã không còn trong nguồn vẫn giữ, vì còn là FK của địa chỉ và Đơn hàng.
- Khoá chính là mã Cục Thống kê (có số 0 đứng đầu), không kế thừa `BaseModel` ([ADR 0008](../../adr/0008-uuid-v7-primary-keys.md), ngoại lệ ở [03 mục 0.1](../03-data-model.md)).

## 6. Tài liệu liên quan

- Schema: [03 mục 1](../03-data-model.md#1-geo-và-common)
- Rủi ro địa chỉ 2 cấp/3 cấp khi gọi GHN: [06](../06-integrations.md) mục 4
- Nguồn: package `vietnam-provinces` ([14](../14-dependencies.md))
