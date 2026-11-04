# 13. Coding style Python/Django

Tài liệu này là cẩm nang tổng hợp cách viết code Python/Django trong Fashion Store. Nó áp dụng cho
toàn bộ `backend/`, gồm code production, migration, management command và test.
Quy ước TypeScript/Next.js chưa thuộc phạm vi này; chỉ bổ sung sau khi frontend được bootstrap và
có cấu hình lint/format thực tế.

Mức độ của quy tắc:

- **MUST** (`phải`, `không được`): bắt buộc để giữ correctness, security hoặc contract kiến trúc.
- **SHOULD** (`nên`, `ưu tiên`): mặc định phải theo; được làm khác khi có lý do cụ thể ghi tại code/PR.
- **MAY** (`có thể`): một lựa chọn hợp lệ, không phải yêu cầu.

Nguồn sở hữu quy tắc được chia như sau:

| Loại quy tắc | Nguồn sở hữu |
|---|---|
| Rule máy kiểm được | `backend/pyproject.toml`, `.editorconfig`, `.pre-commit-config.yaml`, `backend/Makefile` |
| Design constraint | Tài liệu architecture và ADR được dẫn chiếu tại từng mục |
| Convention không tự động kiểm | Tài liệu này |

Tài liệu này tóm tắt design constraint để tiện dùng hằng ngày nhưng không thay thế nguồn sở hữu. Nếu
ví dụ hoặc bản tóm tắt bị lệch, ưu tiên nguồn sở hữu và sửa tài liệu này trong cùng PR.

## 1. Phạm vi và ngoại lệ

Quy tắc chung áp dụng cho mọi code dưới `backend/`; các ngoại lệ có chủ đích sau được ưu tiên hơn rule
chung nhưng không miễn trừ yêu cầu về secret, PII và correctness:

| Phạm vi | Ngoại lệ |
|---|---|
| Code production | Áp dụng đầy đủ |
| Test | Có thể cố ý dùng invalid type, stdlib logging hoặc suppression hẹp để kiểm tra boundary |
| Migration | Giữ khuôn do Django sinh; không refactor chỉ để giống code production |
| Script/management command | Có thể xuất console có chủ đích; không được in secret, PII hoặc dữ liệu thật |

Quy trình riêng cho AI agent nằm ở `CLAUDE.md`, không thuộc coding convention.

## 2. Ngôn ngữ và kiểu dữ liệu

| Chủ đề | Quy ước |
|---|---|
| Tên trong code | Biến, hàm, class, bảng, field, enum và error code viết bằng tiếng Anh |
| Comment/docstring | Viết tiếng Việt; giữ nguyên thuật ngữ kỹ thuật, tên package và identifier tiếng Anh |
| Chuỗi hiển thị | Bọc `gettext` để hỗ trợ vi/en; không nhúng chuỗi hiển thị trực tiếp nếu cần dịch |
| Chữ trên Swagger | `summary`, `description`, ví dụ trong `extend_schema` / `extend_schema_serializer` viết tiếng Anh, không bọc `gettext` (schema sinh giống nhau ở mọi máy); docstring của view và serializer không vào schema. Mỗi view mới có `summary` và ví dụ; xem [04](./04-api-contract.md) mục 5.6 |
| Type hints | Mọi hàm trong `services`, `selectors`, `contracts` có type hints đầy đủ; dùng `list[X]`, `X \| None`, không dùng `List`, `Optional` |
| Tiền | DB dùng `BigIntegerField` theo đồng VND; code dùng `shared.money.Money`; API trả object gồm `amount` và `currency` |
| Thời gian | Lưu UTC với `USE_TZ = True`, lấy giờ bằng `django.utils.timezone.now()`; hiển thị theo `Asia/Ho_Chi_Minh` |

Không dùng `Any` để né type checking nếu có thể biểu diễn kiểu cụ thể. Không thêm `# type: ignore` hay
`# noqa` chỉ để làm CI xanh. Mỗi suppression phải hẹp và có mã rule; thêm comment giải thích khi lý do
không hiển nhiên hoặc là workaround cho type stub/tooling.

## 3. Ranh giới tầng và module

- View/API chỉ parse, validate, phân quyền và gọi service/selector; không chứa nghiệp vụ hoặc transaction.
- `services` thực hiện hành động ghi; `selectors` thực hiện truy vấn đọc; `models` giữ schema và invariant
  cục bộ, không trở thành service layer ẩn.
- Module khác gọi đồng bộ qua `contracts.py`, dùng schema sự kiện công khai trong `events.py` và bắt
  domain exception thuộc contract từ `exceptions.py`; ngoại lệ FK được chốt trong
  [02](./02-backend-structure.md#63-fk-sang-module-khác).
- Không import trực tiếp `models`, `services`, `selectors` hoặc test factory nội bộ của module khác.
- `shared` chỉ chứa hạ tầng dùng chung, không chứa nghiệp vụ riêng của một module.
- Không tạo abstraction dùng chung khi mới có một use case. Ưu tiên code rõ ràng trong đúng module; chỉ
  tách khi đã có trách nhiệm chung ổn định.

`import-linter` là cổng thực thi cho một phần các ranh giới trên. Việc lint qua không thay thế code review,
vì ORM traversal có thể vượt module mà không tạo import.

### 3.1. View, serializer và permission

- View phải khai báo permission phù hợp và coi dữ liệu từ request là không tin cậy cho tới khi serializer
  validate thành công.
- Serializer chỉ chuyển đổi representation và validate cấu trúc/field cục bộ. Không mở transaction,
  gọi provider, ghi nhiều aggregate hoặc điều phối workflow trong `create()`, `update()` hay `validate()`.
- Validation cần query nhiều model hoặc phụ thuộc trạng thái cạnh tranh thuộc service; service phải kiểm
  tra lại bên trong transaction thay vì tin kết quả kiểm tra trước đó của serializer.
- View gọi service cho command và selector cho query. Không gọi ORM trực tiếp, trừ boundary hạ tầng đã
  được [02](./02-backend-structure.md) cho phép rõ ràng.
- Dùng `APIView`, generic view hoặc ViewSet theo hình dạng API, không tạo base view riêng chỉ để giảm vài
  dòng lặp. Pagination, filtering và permission dùng component chuẩn của DRF hoặc component chung đã có.
- Không trả Django model, exception message nội bộ hoặc `serializer.errors` chưa qua API error contract
  trực tiếp cho client.

```python
# ✅ Serializer kiểm tra representation; view gọi service.
class CartLineInputSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class CartLineCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = CartLineInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        line = add_cart_line(account_id=request.user.pk, **serializer.validated_data)
        return Response(CartLineSerializer(line).data, status=status.HTTP_201_CREATED)


# ❌ Serializer che giấu transaction và workflow ghi nhiều model.
class CartLineInputSerializer(serializers.Serializer):
    def create(self, validated_data: dict[str, object]) -> CartLine:
        with transaction.atomic():
            stock = StockItem.objects.select_for_update().get(...)
            return CartLine.objects.create(stock=stock, **validated_data)
```

**Vì sao:** cùng một service có thể được gọi từ API, command hoặc task mà không sao chép nghiệp vụ.
Serializer vẫn trả lỗi input chuẩn của DRF; service chịu trách nhiệm invariant và race condition tại thời
điểm ghi.

### 3.2. ORM và query

- Query đọc dùng selector; query ghi, row lock và kiểm tra invariant cạnh tranh dùng service.
- Chủ động tránh N+1 bằng `select_related()` cho quan hệ đơn và `prefetch_related()` cho collection. Chỉ
  prefetch dữ liệu response thực sự cần; xác nhận query count ở test cho endpoint có nguy cơ hồi quy.
- Không đưa `QuerySet` chưa evaluate qua module boundary nếu caller có thể nối thêm traversal vào model
  nội bộ. Public contract trả DTO hoặc kiểu đã được [02](./02-backend-structure.md) cho phép.
- Dùng `get_or_create()` hoặc `update_or_create()` chỉ khi database constraint bảo đảm tính duy nhất và
  semantics khi race đã được xử lý. Không coi chúng là thay thế cho lock hoặc idempotency.
- `bulk_create()` và `bulk_update()` bỏ qua `save()` và nhiều hook của Django; chỉ dùng khi invariant,
  event, audit và timestamp đã được xử lý tường minh.
- Không dùng raw SQL khi ORM biểu diễn được truy vấn rõ ràng. Raw SQL phải parameterized, nằm sau một API
  hẹp và có test trên PostgreSQL thật.

```python
# ✅ Selector định nghĩa query shape mà response cần.
def list_order_summaries(*, account_id: UUID) -> list[OrderSummaryDTO]:
    orders = (
        Order.objects.filter(account_id=account_id)
        .select_related("shipping_address")
        .prefetch_related("lines__variant")
        .order_by("-created_at")
    )
    return [OrderSummaryDTO.from_model(order) for order in orders]


# ❌ Query trong view và gây N+1 khi serialize từng quan hệ.
orders = Order.objects.filter(account_id=request.user.pk)
return Response(OrderSerializer(orders, many=True).data)
```

**Vì sao:** selector làm rõ dữ liệu được tải và giữ cấu trúc ORM bên trong module. `select_related()` dùng
JOIN cho quan hệ đơn; `prefetch_related()` tải collection bằng query riêng thay vì query lại cho mỗi
Đơn hàng.

## 4. Service, transaction và tác vụ bên ngoài

- Chỉ mở `transaction.atomic()` tại service hoặc các điểm hạ tầng đã được [02](./02-backend-structure.md)
  cho phép. Không mở transaction trong view, serializer hay selector.
- Sự kiện outbox phải được ghi cùng transaction với thay đổi nghiệp vụ.
- Không gọi HTTP, gửi email hoặc gọi provider trong transaction. Read/quote idempotent có thể thực hiện
  trước transaction khi kết quả được kiểm tra lại theo contract. Side effect bên ngoài phải được kích
  hoạt bền vững qua outbox/task sau commit, không gọi trực tiếp trước transaction.
- Code nghiệp vụ không gọi `.delay()` hay `.apply_async()` trực tiếp. Dùng
  `shared.tasks.enqueue_on_commit(...)`.
- Tôn trọng thứ tự khoá đã chốt: checkout mới khoá Cart → StockItem theo `variant_id` → Variant theo `id`
  → Voucher; transition của Order đã tồn tại khoá Order trước rồi StockItem → Variant → Voucher.
- Mọi cart mutation/merge khoá Cart theo `id` tăng dần và không lấy Cart sau StockItem.
- Writer của catalog làm thay đổi dữ liệu ảnh hưởng checkout phải khoá các Variant liên quan theo `id`
  tăng dần và tăng `checkout_version`.
- Không xoá cứng dữ liệu đã tham gia Đơn hàng; dùng trạng thái hoặc `archived` theo thiết kế dữ liệu.

Các rule transaction, lock order và checkout ở trên là bản tóm tắt; nguồn sở hữu nằm tại
[02](./02-backend-structure.md), [03](./03-data-model.md), [10](./10-nfr.md) và
[ADR-0012](../adr/0012-checkout-price-snapshot.md).

## 5. Đặt tên và cấu trúc Python

### 5.1. Naming theo loại đối tượng

Theo PEP 8: `snake_case` cho hàm, biến, module; `PascalCase` cho class; `UPPER_CASE` cho hằng số.

| Đối tượng | Quy tắc | Ví dụ |
|---|---|---|
| Service | `<verb>_<noun>` | `place_order`, `reserve_stock` |
| Selector trả đúng một object | `get_...`, ném lỗi nếu không tồn tại | `get_cart_with_prices` |
| Selector trả object hoặc `None` | `find_...` | `find_order_for_guest` |
| Selector trả collection | `list_...` | `list_orders_backoffice` |
| Hàm public trong `contracts.py` | Cùng tên service/selector được bọc | `inventory.contracts.reserve_stock` |
| DTO contract | `PascalCase` với hậu tố `DTO` | `ShippingQuoteDTO` |
| Event class | Danh từ + động từ quá khứ + `V<n>` | `OrderPlacedV1` |
| `event_type` | `<module>.<kebab-case>` | `ordering.order-placed` |
| Domain exception | `PascalCase` mô tả tình huống; không bắt buộc hậu tố `Error` | `OutOfStock` |
| Error code | `UPPER_SNAKE_CASE` | `OUT_OF_STOCK` |
| Bảng | `<module>_<model>` qua `Meta.db_table` | `ordering_order` |
| Celery task | `<module>.<snake_case>`, đặt cố định trên decorator | `shipping.create_shipment` |
| File service/selector | Theo chủ đề nghiệp vụ, không theo tên model | `services/checkout.py` |
| Test module | `test_<layer>_<topic>.py` | `test_services_checkout.py` |
| Test xuyên module | Đặt trong `backend/tests/flows/` | `test_cod_checkout_flow.py` |

Project chủ ý dùng `<verb>_<noun>`, khác convention `<entity>_<action>` của HackSoft Styleguide.
Không trộn hai cách đặt tên.

### 5.2. Khai báo hàm

- Hàm public phải có type hints đầy đủ cho parameter và return type. Hàm không trả giá trị khai báo
  `-> None`; không bỏ return type chỉ vì mypy có thể suy luận.
- Service, selector và public contract dùng keyword-only parameter (`*`) để call site tự mô tả và tránh
  lỗi khi nhiều đối số có cùng primitive type. Positional parameter chỉ nên dùng cho hàm nhỏ có thứ tự
  tự nhiên, ví dụ value object hoặc callback theo protocol của framework.
- Thứ tự parameter: dữ liệu bắt buộc trước, tuỳ chọn sau; dependency được inject đặt riêng và có tên mô
  tả vai trò. Không thêm boolean flag làm hàm thực hiện hai workflow khác nhau; tách thành hai hàm có tên
  thể hiện intent.
- Không dùng mutable default như `items=[]` hoặc `options={}`. Dùng `None` rồi khởi tạo trong hàm, hoặc
  immutable value như tuple/frozenset khi đó là contract phù hợp.
- Hàm bắt đầu bằng động từ và làm một việc ở cùng mức abstraction. Tách helper private `_name` khi nó
  đặt tên được cho một bước nghiệp vụ hoặc loại bỏ nhánh phức tạp; không tách chỉ để đạt số dòng tuỳ ý.
- Không bắt `Exception` để đổi mọi lỗi thành một giá trị mặc định. Return `None` chỉ khi absence là một
  phần được đặt tên rõ trong contract, thường bằng tiền tố `find_`.
- Chỉ dùng `async def` khi toàn bộ call chain và dependency thực sự hỗ trợ async. Không bọc ORM sync hoặc
  HTTP client sync trong async function rồi chặn event loop.

```python
# ✅ Call site tự mô tả; không có mutable default.
def reserve_stock(
    *,
    order_id: UUID,
    lines: Sequence[StockLine],
    expires_at: datetime | None = None,
) -> Reservation:
    ...


# ❌ Nhiều positional primitive, boolean flag mơ hồ và mutable default.
def reserve(order_id, lines=[], notify=True): ...
```

**Vì sao:** keyword-only giúp reviewer thấy ngay ý nghĩa từng đối số và cho phép thêm parameter tuỳ chọn
mà ít làm hỏng call site. Mutable default được tạo một lần khi định nghĩa hàm, nên dữ liệu có thể rò từ
lần gọi trước sang lần gọi sau. Boolean flag thường là dấu hiệu hai hành vi cần hai tên hàm riêng.

### 5.3. Tên biến

- Tên phải thể hiện vai trò nghiệp vụ, không chỉ kiểu dữ liệu. Tránh `data`, `obj`, `item`, `value`,
  `result`, `tmp` khi có tên cụ thể hơn như `order_payload`, `variant`, `shipping_quote`.
- Boolean dùng tiền tố tạo thành mệnh đề: `is_`, `has_`, `can_`, `should_`. Không dùng phủ định kép như
  `not_disabled` hoặc tên không cho biết giá trị `True` có nghĩa gì.
- Collection dùng danh từ số nhiều (`orders`, `variant_ids`); mapping nên thể hiện hai phía khi cần,
  ví dụ `price_by_variant_id`.
- Phân biệt object và identifier: `order`/`order_id`, `account`/`account_id`. Không dùng `id` đứng một
  mình ngoài scope rất ngắn và không nhập nhằng.
- Giá trị có đơn vị phải thể hiện bằng type hoặc tên: ưu tiên `Money`, `timedelta`; nếu buộc dùng primitive,
  dùng tên như `timeout_seconds`, không dùng `timeout` mơ hồ.
- Trong test, dùng `actual` và `expected` khi phép so sánh có thể nhập nhằng; nếu không, tên nghiệp vụ cụ
  thể như `available_quantity` tốt hơn tên chung.

```python
# ✅ Tên cho biết domain concept, cardinality và đơn vị.
variant_ids = [line.variant_id for line in order_lines]
price_by_variant_id = get_effective_prices(variant_ids=variant_ids)
has_reservation_expired = reservation.expires_at <= timezone.now()
timeout_seconds = 5

# ❌ Người đọc phải lần theo từng giá trị để đoán ý nghĩa.
ids = [x.variant_id for x in items]
data = get_data(ids)
flag = end > timezone.now()
timeout = 5
```

**Vì sao:** tên biến là phần gần call site nhất của tài liệu thiết kế. Tên chính xác ngăn việc truyền nhầm
`order_id` thành `variant_id`, đồng thời khiến điều kiện boolean đọc như một mệnh đề thay vì một cờ mơ hồ.

### 5.4. Class và OOP

- Ưu tiên function/module cho logic stateless. Chỉ tạo class khi cần giữ invariant/state qua nhiều thao
  tác, biểu diễn một value/domain object, hoặc implement một protocol/framework extension.
- Ưu tiên composition và dependency injection hơn inheritance. Chỉ kế thừa khi subtype thực sự thay thế
  được base type và dùng contract của base; không tạo base class chỉ để chia sẻ vài helper.
- Không tạo class chỉ chứa `@staticmethod`. Đặt các hàm stateless ở module; dùng `@classmethod` cho named
  constructor cần `cls` và có tên như `from_payload`, `from_model`.
- `@property` phải rẻ, deterministic và không thực hiện I/O hoặc query ẩn. Hành động có side effect dùng
  method mang động từ.
- Attribute nội bộ dùng tiền tố `_`; không dựa vào name mangling `__name` như một security boundary.
  Public API nhỏ, thể hiện invariant qua method thay vì cho caller sửa state tuỳ ý.
- Dùng Django model cho persistence/schema, Pydantic model cho contract/validation ở boundary và event,
  `dataclass(frozen=True)` cho value object nội bộ không cần Pydantic. Không dùng một type cho cả ba vai
  trò chỉ để tránh mapping.
- Dùng `Protocol` khi consumer cần một interface nhỏ và có nhiều implementation/adapters. Chỉ dùng ABC
  khi cần chia sẻ lifecycle hoặc framework bắt buộc; không tạo interface dự phòng cho một use case.
- Exception biểu diễn tình huống thất bại, không dùng làm control flow thông thường trong vòng lặp nóng.
  Giữ hierarchy nông và bắt exception cụ thể tại boundary có trách nhiệm chuyển đổi/log/retry.

```python
# ✅ Consumer phụ thuộc một capability nhỏ; adapter giữ chi tiết provider.
class ShippingRateProvider(Protocol):
    def quote(self, *, destination: AddressDTO, lines: Sequence[ShippingLineDTO]) -> Money: ...


class ShippingFeeCalculator:
    def __init__(self, *, provider: ShippingRateProvider, fallback_fee: Money) -> None:
        self._provider = provider
        self._fallback_fee = fallback_fee

    def calculate(self, *, destination: AddressDTO, lines: Sequence[ShippingLineDTO]) -> Money:
        try:
            return self._provider.quote(destination=destination, lines=lines)
        except ShippingProviderUnavailable:
            return self._fallback_fee


# ❌ Class chỉ làm namespace cho static method và tự chọn dependency toàn cục.
class ShippingUtils:
    @staticmethod
    def get_quote(address, lines):
        return ghn_client.quote(address, lines)
```

**Vì sao:** composition cho phép thay adapter thật bằng fake trong test mà không kế thừa calculator.
`Protocol` chỉ mô tả phần consumer cần; calculator sở hữu chính sách Phí ship dự phòng, còn class
`ShippingUtils` không sở hữu state hay invariant nên không mang lại lợi ích so với function/module.

## 6. Format, import và static analysis

- Python 3.14, indent 4 space, UTF-8, LF, dòng tối đa 100 ký tự và nháy kép.
- Chỉ dùng `ruff format`; không chạy Black, isort hoặc flake8 riêng.
- Import theo nhóm stdlib → third-party → `config`, `shared`, `modules`; để Ruff sắp xếp.
- `ruff check` là lint chuẩn. Không vô hiệu hoá rule ở cấp file hoặc project nếu chưa có lý do áp dụng
  cho toàn bộ phạm vi đó.
- `mypy` với Django/DRF plugin là type checker chuẩn. Các service, selector và contract phải đạt mức strict
  được cấu hình trong `backend/pyproject.toml`.
- File không phải Python tuân theo `.editorconfig` và pre-commit hooks. Project không dùng Prettier.
- Không sửa tay vùng `# BEGIN gen_importlinter` trong `backend/pyproject.toml`; chạy generator được ghi ở [02](./02-backend-structure.md#8-kiểm-tra-ranh-giới-module-import-linter).

`make fmt` là lệnh sửa format tự động. `make lint` là cổng kiểm tra và phải giữ cùng thứ tự với CI.

## 7. Django model và migration

- Model nghiệp vụ do dự án sở hữu kế thừa `shared.models.BaseModel`, dùng UUID v7 và không tự khai báo
  `id`. Model dữ liệu địa giới, framework và audit/history dùng khoá theo thiết kế riêng; xem ngoại lệ
  tại [03](./03-data-model.md) và [ADR-0008](../adr/0008-uuid-v7-primary-keys.md).
- `TextChoices` đặt ở cấp module. Không tạo alias class chỉ khác hoa/thường với field, ví dụ `Status`
  cạnh `status`.
- Khai báo rõ `Meta.db_table`, constraint và index theo [03](./03-data-model.md); không chỉ dựa vào
  validation ở serializer.
- Không đặt business workflow trong `save()`, signal hoặc serializer. Workflow thuộc service.
- Cột `NOT NULL` thêm vào bảng đã có dữ liệu phải có kế hoạch migration tương thích ngược. Khi code cũ
  còn có thể INSERT trong rolling deploy, dùng `db_default`, không chỉ `default`.
- Không sửa migration đã chạy ở môi trường dùng chung. Tạo migration mới.
- Migration do Django sinh có thể giữ style framework; không refactor migration chỉ để giống code
  production.

### 7.1. Model, manager và command

- Model giữ field, constraint và invariant cục bộ có thể kiểm tra từ chính instance. Workflow chạm nhiều
  aggregate, provider hoặc event thuộc service, kể cả khi có thể viết ngắn hơn trong model method.
- Custom `QuerySet`/manager chỉ chứa query primitive có thể compose và không che giấu side effect. Query
  theo use case vẫn được đặt sau selector để caller không phụ thuộc cấu trúc ORM.
- Chuyển trạng thái hàng loạt của một model (`UPDATE` theo danh sách id mà caller đã khoá và lọc) là
  `@classmethod` của model, không phải method của `QuerySet`: model quyết cột nào được ghi, còn
  `QuerySet` giữ nguyên là primitive không side effect. Ví dụ: `EventDelivery.reopen`,
  `EventDelivery.mark_dispatched`.
- Không dùng signal cho workflow nghiệp vụ. Signal chỉ phù hợp với tích hợp hạ tầng cục bộ, bắt buộc có
  lý do vì sao explicit call không phù hợp và có test chứng minh transaction semantics.
- Django Admin và management command là adapter: parse/validate input, gọi service/selector và trình bày
  kết quả. Không sao chép nghiệp vụ vào `ModelAdmin`, `handle()` hoặc form admin.
- Code chạy lúc import hoặc `AppConfig.ready()` không query database hay gọi mạng. Import đăng ký check,
  event handler hoặc admin phải idempotent và tránh circular import.

```python
# ✅ Command là adapter mỏng, nghiệp vụ nằm trong service dùng lại được.
class Command(BaseCommand):
    def handle(self, *args: object, **options: object) -> None:
        account = create_staff_account(
            email=str(options["email"]),
            password=str(options["password"]),
            kind=AccountKind.STAFF,
        )
        self.stdout.write(str(account.id))


# ❌ Command ghi model trực tiếp và sao chép invariant của service.
class Command(BaseCommand):
    def handle(self, *args, **options):
        Account.objects.create(email=options["email"], kind="staff")
```

**Vì sao:** management command, Django Admin, API và task chỉ là các entry point khác nhau. Tất cả gọi
cùng service thì validation, transaction, event và audit không bị lệch theo từng đường vào hệ thống.

## 8. Comment và docstring

- Public function trong `contracts.py` và `services/` phải có Google-style docstring mô tả contract.
- Chỉ ghi mã `BR-xxx` và mục `Raises` khi thực sự áp dụng; không chèn reference hình thức hoặc lặp lại
  type hints.
- Comment giải thích **vì sao**, constraint hoặc đánh đổi; không diễn giải từng dòng code đang làm gì.
- Reference tài liệu bằng file và mục ổn định khi constraint không thể hiện đầy đủ trong code.
- Xoá comment lỗi thời trong cùng thay đổi; comment sai nguy hiểm hơn không có comment.

## 9. Test

Chiến lược, marker, coverage và CI gate nằm ở [12](./12-testing-strategy.md). Khi viết test:

- Dùng `factory-boy`; không dùng JSON fixture.
- Không mock ORM. Test trên PostgreSQL thật và chỉ fake hệ thống bên ngoài.
- Mỗi public service function phải có bằng chứng cho happy path và từng hành vi lỗi mà contract của nó
  công bố. Có thể dùng flow test nếu đó là cấp kiểm chứng phù hợp nhất.
- Test business rule gắn `@pytest.mark.br("BR-xxx")`.
- Cố định thời gian bằng `time-machine`; không patch `timezone.now()` thủ công.
- Factory đặt trong module sở hữu và chỉ dùng factory của module đó hoặc module lớp dưới.
- Hành vi cần commit thật, nhiều connection hoặc lock dùng `django_db(transaction=True)`.
- Service test cần chạy callback `on_commit` dùng
  `django_capture_on_commit_callbacks(execute=True)`; flow test dùng `drain_events()`.
- Trong `pytest.raises`, chỉ để một lời gọi có thể ném exception.
- Assert theo dạng `actual == expected`; đặt kết quả thực vào biến khi biểu thức có thể gây hiểu nhầm.
- Model test kế thừa `BaseModel` phải khai báo manager phù hợp để mypy không suy sai kiểu.

Tên test mô tả hành vi quan sát được, không mô tả chi tiết implementation. Test phải độc lập thứ tự chạy
và không phụ thuộc dữ liệu còn lại từ test khác.

## 10. Logging, exception và dữ liệu nhạy cảm

- Dùng `logger = structlog.get_logger(__name__)`; không dùng `print` hoặc `logging.getLogger` trong code
  ứng dụng.
- Message là tên sự kiện tiếng Anh dạng `snake_case`; dữ liệu truyền bằng keyword. Không dùng f-string
  hoặc `%` để ghép message.
- Chọn log level theo boundary và ý nghĩa vận hành: domain error dự kiến ở API thường là `INFO`; event
  hoặc job bị từ chối và cần quan sát có thể là `WARNING`; lỗi ngoài dự kiến là `ERROR`. Xem thêm
  [07](./07-async-events-jobs.md) cho consumer và task.
- Không log PII, IP thô, email, số điện thoại, địa chỉ, token, mật khẩu, secret hoặc payload thanh toán.
  Processor redact chỉ là lưới an toàn, không phải quyền log dữ liệu nhạy cảm.
- Khi exception gốc có thể chứa secret hoặc connection URL, raise exception đã lọc bằng `from None`.
- Không bắt `Exception` rồi im lặng. Nếu có thể phục hồi, log đủ identifier không nhạy cảm và giữ nguyên
  semantics retry; nếu không, để exception truyền lên boundary chịu trách nhiệm xử lý.

```python
logger.info("stock_reserved", variant_id=variant.id, quantity=quantity)
logger.warning("shipping_fee_fallback", provider="ghn", reason="timeout")
```

## 11. Mẫu code Good/Bad

Các ví dụ dưới đây minh hoạ hình dạng code cần hướng tới và có thể lược import. Khi type hoặc namespace
có thể nhập nhằng, ví dụ phải ghi rõ nguồn. Tên model và service chỉ là ví dụ; khi triển khai phải dùng
đúng thuật ngữ trong `GLOSSARY.md` và API thật của module.

### 11.1. View mỏng, nghiệp vụ nằm trong service

✅ **Good** — view chỉ validate input, gọi service và serialize output:

```python
class OrderCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account_id = request.user.pk  # Boundary xác thực bảo đảm đây là Account đang active.

        order = place_order(
            account_id=account_id,
            cart_id=serializer.validated_data["cart_id"],
            payment_method=serializer.validated_data["payment_method"],
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
```

❌ **Bad** — view tự query, mở transaction và thực hiện business rule:

```python
class OrderCreateView(APIView):
    def post(self, request: Request) -> Response:
        with transaction.atomic():
            cart = Cart.objects.select_for_update().get(id=request.data["cart_id"])
            if cart.items.count() == 0:
                raise ValidationError("Cart is empty")
            order = Order.objects.create(account=request.user, total=cart.total)
        return Response({"id": order.id})
```

### 11.2. Module khác chỉ gọi public contract

✅ **Good** — `ordering` gọi public API của `inventory`:

```python
from modules.inventory.contracts import reserve_stock

reservation = reserve_stock(lines=stock_lines, expires_at=expires_at)
```

❌ **Bad** — import model/service nội bộ của module khác hoặc traversal ORM qua quan hệ của nó:

```python
from modules.inventory.models import StockItem
from modules.inventory.services.reservations import create_reservation

stock = StockItem.objects.select_for_update().get(variant_id=variant_id)
shipment__provider__status = order.shipment.provider.status
```

### 11.3. Transaction không chứa I/O bên ngoài

✅ **Good** — ghi DB/outbox trong transaction và enqueue sau commit:

```python
def confirm_order(*, order_id: UUID) -> Order:
    """Xác nhận Đơn hàng và lên lịch tạo Vận đơn sau khi transaction commit."""

    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        order.status = OrderStatus.CONFIRMED
        order.save(update_fields=["status", "updated_at"])
        publish(OrderConfirmedV1(order_id=order.id))
        enqueue_on_commit("shipping.create_shipment", order_id=str(order.id))

    return order
```

❌ **Bad** — gọi HTTP và đẩy Celery task khi transaction chưa commit:

```python
with transaction.atomic():
    order.status = OrderStatus.CONFIRMED
    order.save()
    ghn_client.create_shipment(order)  # HTTP có thể treo trong lúc giữ DB lock.
    create_shipment.delay(order.id)  # Worker có thể chạy trước khi DB commit.
```

### 11.4. Naming và type hints thể hiện contract

✅ **Good**:

```python
from pydantic import BaseModel


def find_order_for_guest(*, order_code: str, email: str) -> Order | None: ...


def list_orders_backoffice(*, status: OrderStatus | None = None) -> QuerySet[Order]: ...


class ShippingQuoteDTO(BaseModel):
    amount: int
    currency: Literal["VND"]
```

❌ **Bad**:

```python
def order_get(code, email): ...  # Sai convention, thiếu type hints, không rõ có thể trả None không.


def process(data: Any) -> Any: ...  # Tên mơ hồ và dùng Any để né contract.


class ShippingQuote(BaseModel): ...  # DTO public thiếu hậu tố DTO.
```

### 11.5. Model giữ schema; workflow nằm trong service

✅ **Good**:

```python
class Order(BaseModel):
    status = models.CharField(max_length=32, choices=OrderStatus.choices)

    class Meta:
        db_table = "ordering_order"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(status__in=OrderStatus.values),
                name="ordering_order_status_valid",
            ),
        )
```

❌ **Bad** — `save()` che giấu workflow và side effect:

```python
class Order(models.Model):
    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.status == "confirmed":
            send_confirmation_email.delay(self.id)
        super().save(*args, **kwargs)
```

Khi thêm cột bắt buộc vào bảng đang có dữ liệu:

```python
# ✅ Good: DB vẫn có default khi code phiên bản cũ INSERT trong rolling deploy.
status = models.CharField(max_length=32, db_default=OrderStatus.PENDING)

# ❌ Bad: `default` chỉ phục vụ Python/migration state và migration có thể DROP DB default.
status = models.CharField(max_length=32, default=OrderStatus.PENDING)
```

### 11.6. Comment và docstring giải thích lý do

✅ **Good**:

```python
def reserve_stock(*, order_id: UUID, lines: list[StockLine]) -> Reservation:
    """Giữ Tồn kho cho Đơn thanh toán online.

    Áp dụng BR-INV-05. Các StockItem phải được khoá theo `variant_id` tăng dần để mọi
    checkout dùng cùng thứ tự khoá.

    Raises:
        OutOfStock: Một Biến thể không còn đủ Số lượng bán được.
    """
```

❌ **Bad**:

```python
def reserve_stock(order_id, lines):
    """Reserve stock.

    Args:
        order_id: The order id.
        lines: The lines.
    """
    # Loop through every line.
    for line in lines:
        ...
```

### 11.7. Test một hành vi, một nguyên nhân thất bại

✅ **Good**:

```python
@pytest.mark.br("BR-INV-05")
def test_reserve_stock_rejects_quantity_above_available(stock_item: StockItem) -> None:
    requested_quantity = stock_item.available_quantity + 1

    with pytest.raises(OutOfStock):
        reserve_stock(variant_id=stock_item.variant_id, quantity=requested_quantity)

    stock_item.refresh_from_db()
    actual = stock_item.reserved_quantity
    assert actual == 0
```

❌ **Bad** — mock ORM, nhiều lời gọi có thể fail trong `pytest.raises`, assert không rõ đối tượng:

```python
@patch("modules.inventory.models.StockItem.objects.get")
def test_stock(mock_get):
    with pytest.raises(Exception):
        stock = build_stock()
        reserve_stock(stock.variant_id, 99)
    assert stock.reserved_quantity == 0
```

### 11.8. Structured logging không chứa PII

✅ **Good**:

```python
logger.info(
    "order_confirmed",
    order_id=str(order.id),
    order_code=order.code,
    payment_method=order.payment_method,
)
```

❌ **Bad**:

```python
print(f"Confirmed order for {order.customer_email}")
logger.info(f"order confirmed: {order.__dict__}")
logger.info("payment_callback", payload=request.data, access_token=token)
```

### 11.9. Suppression phải hẹp và có lý do

✅ **Good**:

```python
result = subprocess.run(  # noqa: S603 -- executable là binary cố định trong virtualenv.
    [LINT_IMPORTS, "--config", str(config_path)],
    check=False,
)
```

❌ **Bad**:

```python
# ruff: noqa
result = subprocess.run(command, shell=True)  # type: ignore
```

## 12. Checklist hoàn tất thay đổi

- Code nằm đúng module và đúng tầng; không bypass contract hoặc ORM traversal sang module khác.
- Tên, type hints, docstring và logging tuân theo tài liệu này.
- Migration, API contract, business rule, glossary và tài liệu liên quan được cập nhật nếu thay đổi chạm
  tới chúng.
- Test bao phủ happy path, domain error và cạnh tranh/transaction khi có liên quan.
- Không thêm secret, PII, debug output, suppression rộng hoặc TODO không có chủ sở hữu.
- Với thay đổi code, `make fmt`, `make lint` và test tương xứng với rủi ro đã chạy; full test suite là
  cổng trước merge/release. Mọi giới hạn kiểm chứng được báo rõ trong kết quả.
