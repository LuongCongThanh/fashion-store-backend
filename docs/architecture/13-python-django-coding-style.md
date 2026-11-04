# 13. Coding style Python/Django

Cẩm nang tổng hợp cách viết code Python/Django cho toàn bộ repo: code production, migration,
management command và test. Quy ước TypeScript/Next.js chỉ bổ sung sau khi frontend được bootstrap và có
cấu hình lint/format thực tế.

Mức độ quy tắc:

- **MUST** (`phải`, `không được`): bắt buộc để giữ correctness, security hoặc contract kiến trúc.
- **SHOULD** (`nên`, `ưu tiên`): mặc định phải theo; được làm khác khi có lý do cụ thể ghi tại code/PR.
- **MAY** (`có thể`): lựa chọn hợp lệ, không phải yêu cầu.

| Loại quy tắc | Nguồn sở hữu |
|---|---|
| Rule máy kiểm được | `pyproject.toml`, `.editorconfig`, `.pre-commit-config.yaml`, `Makefile` |
| Design constraint | Tài liệu architecture và ADR được dẫn chiếu tại từng mục |
| Convention không tự động kiểm | Tài liệu này |

Tài liệu này chỉ tóm tắt design constraint, không thay thế nguồn sở hữu. Nếu lệch, ưu tiên nguồn sở hữu
và sửa tài liệu này trong cùng PR.

## 1. Phạm vi và ngoại lệ

Ngoại lệ dưới đây được ưu tiên hơn rule chung nhưng không miễn trừ yêu cầu về secret, PII và correctness:

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
| Tiền | DB dùng `BigIntegerField` theo đồng VND; code dùng `common.money.Money`; API trả object gồm `amount` và `currency` |
| Thời gian | Lưu UTC với `USE_TZ = True`, lấy giờ bằng `django.utils.timezone.now()`; hiển thị theo `Asia/Ho_Chi_Minh` |

- Không dùng `Any` để né type checking khi biểu diễn được kiểu cụ thể.
- Không thêm `# type: ignore` hay `# noqa` chỉ để CI xanh. Suppression phải hẹp, có mã rule; thêm comment
  khi lý do không hiển nhiên hoặc là workaround cho type stub/tooling (ví dụ ở mục 11.7).

## 3. Ranh giới tầng và module

- View/API chỉ parse, validate, phân quyền và gọi service/selector; không chứa nghiệp vụ hoặc transaction.
- `services` ghi; `selectors` đọc; `models` giữ schema và invariant cục bộ, không thành service layer ẩn.
- Module khác gọi đồng bộ qua `contracts.py`, dùng schema sự kiện công khai trong `events.py` và bắt
  domain exception thuộc contract từ `exceptions.py`; ngoại lệ FK chốt trong
  [02](./02-backend-structure.md#5-giao-tiếp-giữa-module).
- Không import trực tiếp `models`, `services`, `selectors` hoặc test factory nội bộ của module khác.
- `common` chỉ chứa hạ tầng dùng chung, không chứa nghiệp vụ riêng của một module.
- Không tạo abstraction dùng chung khi mới có một use case; chỉ tách khi đã có trách nhiệm chung ổn định.
- `import-linter` chỉ thực thi một phần các ranh giới trên; vẫn cần code review vì ORM traversal có thể
  vượt module mà không tạo import.

### 3.1. View, serializer và permission

- View khai báo permission phù hợp; dữ liệu request là không tin cậy cho tới khi serializer validate xong.
- Serializer chỉ chuyển đổi representation và validate cấu trúc/field cục bộ. Không mở transaction, gọi
  provider, ghi nhiều aggregate hoặc điều phối workflow trong `create()`, `update()` hay `validate()`.
- Validation cần query nhiều model hoặc phụ thuộc trạng thái cạnh tranh thuộc service; service kiểm tra
  lại trong transaction, không tin kết quả serializer trước đó.
- View gọi service cho command, selector cho query. Không gọi ORM trực tiếp, trừ boundary hạ tầng
  [02](./02-backend-structure.md) cho phép rõ ràng.
- Dùng `APIView`, generic view hoặc ViewSet theo hình dạng API; không tạo base view riêng chỉ để giảm vài
  dòng lặp. Pagination, filtering, permission dùng component chuẩn của DRF hoặc component chung đã có.
- Không trả Django model, exception message nội bộ hoặc `serializer.errors` chưa qua API error contract.
- Lý do: cùng service được gọi từ API, command hoặc task mà không sao chép nghiệp vụ; service chịu
  invariant và race condition tại thời điểm ghi.

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


# ❌ View tự query, mở transaction và thực hiện business rule.
class OrderCreateView(APIView):
    def post(self, request: Request) -> Response:
        with transaction.atomic():
            cart = Cart.objects.select_for_update().get(id=request.data["cart_id"])
            if cart.items.count() == 0:
                raise ValidationError("Cart is empty")
            order = Order.objects.create(account=request.user, total=cart.total)
        return Response({"id": order.id})
```

### 3.2. ORM và query

- Query đọc dùng selector; query ghi, row lock và kiểm tra invariant cạnh tranh dùng service.
- Tránh N+1: `select_related()` cho quan hệ đơn (JOIN), `prefetch_related()` cho collection (query riêng).
  Chỉ prefetch dữ liệu response cần; xác nhận query count ở test cho endpoint có nguy cơ hồi quy.
- Không đưa `QuerySet` chưa evaluate qua module boundary nếu caller có thể nối traversal vào model nội
  bộ. Public contract trả DTO hoặc kiểu [02](./02-backend-structure.md) cho phép.
- `get_or_create()`/`update_or_create()` chỉ dùng khi database constraint bảo đảm tính duy nhất và
  semantics khi race đã xử lý; không thay cho lock hoặc idempotency.
- `bulk_create()`/`bulk_update()` bỏ qua `save()` và nhiều hook; chỉ dùng khi invariant, event, audit và
  timestamp đã xử lý tường minh.
- Không dùng raw SQL khi ORM biểu diễn rõ được. Raw SQL phải parameterized, nằm sau API hẹp và có test
  trên PostgreSQL thật.

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

### 3.3. Quy tắc theo file của module

Vị trí file và ranh giới import ở [02 mục 4.1](./02-backend-structure.md#41-vai-trò-từng-file). Mục này ghi
quy tắc hành vi của từng file.

- **`contracts.py`**: chỉ đưa vào những gì module khác thực sự cần; trả DTO pydantic, không trả model.
  Docstring của hàm ghi dữ liệu nêu rõ: gọi trong transaction của bên gọi được không, khoá dòng nào, ném
  lỗi gì.
- **`exceptions.py`**: mỗi lớp lỗi khai `code` tiếng Anh (ví dụ `OUT_OF_STOCK`), `http_status` (409 hoặc 422
  theo [04](./04-api-contract.md) mục 3, mặc định 422) và `message` mặc định bọc `gettext_lazy`; khi ném có
  thể truyền `message`, `details` riêng. Lỗi báo consumer thử lại sau (ví dụ `TransitionNotYetValid`) kế
  thừa `common.exceptions.RetryLater`. Lỗi thuộc module ném ra nó: module khác import để bắt, không khai
  báo lại.
- **`services`**: mỗi nghiệp vụ ghi là một hàm có tham số keyword; phần ghi chạy trong
  `transaction.atomic`, phát sự kiện qua `common.events.publish`. Hàm điều phối tích hợp chia thành các
  transaction ngắn, không bọc toàn hàm khi có HTTP. Không nhận `request`. Không import `tasks.py`: đẩy task
  theo tên qua `enqueue_on_commit`, để không có vòng import `services` ↔ `tasks`.
- **`handlers.py`**: khai `@handles("payments.payment-succeeded", version=1,
  name="ordering.handle_payment_succeeded")`; `name` cố định như tên Celery task, đổi tên hàm không đổi
  `name`. Mỗi handler gọi **một** service của chính module. Không tự chống xử lý trùng: consumer khoá
  delivery và chuyển `completed` cùng transaction với handler. Sự kiện tới sớm hoặc không áp dụng được thì
  báo bằng exception ([07](./07-async-events-jobs.md) mục 1.3). Handler chạy trong transaction của consumer,
  nên không gọi HTTP hay đẩy Celery task trực tiếp.
- **`tasks.py`**: task mỏng, chỉ gọi service. Mỗi task khai `name="<module>.<task>"` cố định.
- **`api/*/views.py`**: dùng `APIView` hoặc `GenericAPIView`; không dùng `ModelViewSet` để tự sinh CRUD.
- **`api/*/serializers.py`**: không gọi `.save()` lên model.
- **`api/permissions.py`**: không ghi dữ liệu, không gọi contract ghi, không import phần auth hay model nội
  bộ của module khác.

## 4. Service, transaction và tác vụ bên ngoài

- Chỉ mở `transaction.atomic()` tại service của module hoặc các điểm hạ tầng sau: outbox
  (`common.events`: publisher, relay, consumer, operations), `common.idempotency`, và management command
  hạ tầng (`load_geo`, `sync_beat_schedule`). Không mở transaction trong view, serializer hay selector.
- Sự kiện outbox phải được ghi cùng transaction với thay đổi nghiệp vụ.
- Không gọi HTTP, gửi email hoặc gọi provider trong transaction. Read/quote idempotent có thể thực hiện
  trước transaction khi kết quả được kiểm tra lại theo contract. Side effect bên ngoài phải được kích
  hoạt bền vững qua outbox/task sau commit, không gọi trực tiếp trước transaction.
- Code nghiệp vụ không gọi `.delay()` hay `.apply_async()` trực tiếp. Dùng
  `common.tasks.enqueue_on_commit(...)`.
- Tôn trọng thứ tự khoá đã chốt: checkout mới khoá Cart → StockItem theo `variant_id` → Variant theo `id`
  → Voucher; transition của Order đã tồn tại khoá Order trước rồi StockItem → Variant → Voucher.
- Mọi cart mutation/merge khoá Cart theo `id` tăng dần và không lấy Cart sau StockItem.
- Writer của catalog làm thay đổi dữ liệu ảnh hưởng checkout phải khoá các Variant liên quan theo `id`
  tăng dần và tăng `checkout_version`.
- Không xoá cứng dữ liệu đã tham gia Đơn hàng; dùng trạng thái hoặc `archived` theo thiết kế dữ liệu.

Mục này là nguồn sở hữu thứ tự khoá và quy tắc writer của catalog. Luồng checkout ở
[`ordering` mục 5.1](./modules/ordering.md#51-luồng-checkout); ràng buộc dữ liệu ở [03](./03-data-model.md),
[10](./10-nfr.md) và [ADR-0012](../adr/0012-checkout-price-snapshot.md). Ví dụ ở mục 11.2.

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
| Test module | Soi gương file nguồn: `tests/<đường dẫn>/test_<file>.py` (02 mục 4.4); `tests/tooling/test_test_layout.py` chặn file đặt sai | `tests/services/test_checkout.py` |
| Test xuyên module | Đặt trong `tests/flows/` | `test_cod_checkout_flow.py` |

Project chủ ý dùng `<verb>_<noun>`, khác `<entity>_<action>` của HackSoft Styleguide; không trộn hai cách.

### 5.2. Khai báo hàm

- Hàm public có type hints đầy đủ cho parameter và return type; hàm không trả giá trị khai `-> None`,
  không bỏ return type dù mypy suy luận được.
- Service, selector và public contract dùng keyword-only parameter (`*`). Positional chỉ cho hàm nhỏ có
  thứ tự tự nhiên, ví dụ value object hoặc callback theo protocol của framework.
- Thứ tự parameter: bắt buộc trước, tuỳ chọn sau; dependency inject đặt riêng, tên mô tả vai trò.
- Không thêm boolean flag làm hàm chạy hai workflow khác nhau; tách hai hàm có tên thể hiện intent.
- Không dùng mutable default (`items=[]`, `options={}`); dùng `None` rồi khởi tạo trong hàm, hoặc
  tuple/frozenset khi đó là contract phù hợp. Mutable default chỉ tạo một lần nên dữ liệu rò giữa các lần gọi.
- Hàm bắt đầu bằng động từ, làm một việc ở cùng mức abstraction. Tách helper private `_name` khi nó đặt
  tên được một bước nghiệp vụ hoặc bỏ nhánh phức tạp; không tách chỉ để đạt số dòng tuỳ ý.
- Không bắt `Exception` để đổi mọi lỗi thành giá trị mặc định. Return `None` chỉ khi absence là phần được
  đặt tên rõ trong contract, thường bằng tiền tố `find_`.
- Chỉ dùng `async def` khi toàn bộ call chain và dependency hỗ trợ async; không bọc ORM/HTTP client sync
  trong async function rồi chặn event loop.

```python
# ✅ Call site tự mô tả; không có mutable default.
def reserve_stock(
    *, reference: str, items: Sequence[StockLine], expires_at: datetime
) -> Reservation: ...
def find_order_for_guest(*, order_code: str, email: str) -> Order | None: ...
def list_orders_backoffice(*, status: OrderStatus | None = None) -> QuerySet[Order]: ...


class ShippingQuoteDTO(pydantic.BaseModel):
    amount: int
    currency: Literal["VND"]


# ❌
def reserve(order_id, lines=[], notify=True): ...  # Positional primitive, flag mơ hồ, mutable default.
def order_get(code, email): ...  # Sai convention, thiếu type hints, không rõ có thể trả None không.
def process(data: Any) -> Any: ...  # Tên mơ hồ và dùng Any để né contract.
class ShippingQuote(pydantic.BaseModel): ...  # DTO public thiếu hậu tố DTO.
```

### 5.3. Tên biến

- Tên thể hiện vai trò nghiệp vụ, không chỉ kiểu. Tránh `data`, `obj`, `item`, `value`, `result`, `tmp`
  khi có tên cụ thể hơn như `order_payload`, `variant`, `shipping_quote`.
- Boolean dùng tiền tố `is_`, `has_`, `can_`, `should_`; không phủ định kép (`not_disabled`) hoặc tên không
  rõ `True` nghĩa là gì.
- Collection dùng số nhiều (`orders`, `variant_ids`); mapping thể hiện hai phía khi cần (`price_by_variant_id`).
- Phân biệt object và identifier: `order`/`order_id`, `account`/`account_id`. Không dùng `id` đứng một
  mình ngoài scope rất ngắn và không nhập nhằng.
- Giá trị có đơn vị thể hiện bằng type (`Money`, `timedelta`) hoặc tên (`timeout_seconds`, không `timeout`).
- Trong test, dùng `actual`/`expected` khi phép so sánh có thể nhập nhằng; nếu không, ưu tiên tên nghiệp
  vụ như `available_quantity`.

### 5.4. Class và OOP

- Ưu tiên function/module cho logic stateless. Chỉ tạo class khi giữ invariant/state qua nhiều thao tác,
  biểu diễn value/domain object, hoặc implement protocol/framework extension.
- Ưu tiên composition và dependency injection hơn inheritance. Chỉ kế thừa khi subtype thực sự thay thế
  được base type; không tạo base class chỉ để chia sẻ vài helper.
- Không tạo class chỉ chứa `@staticmethod`; đặt hàm stateless ở module. `@classmethod` dùng cho named
  constructor cần `cls` (`from_payload`, `from_model`).
- `@property` phải rẻ, deterministic, không I/O hoặc query ẩn. Hành động có side effect dùng method mang động từ.
- Attribute nội bộ dùng tiền tố `_`; không coi name mangling `__name` là security boundary. Public API
  nhỏ, thể hiện invariant qua method thay vì cho caller sửa state tuỳ ý.
- Django model cho persistence/schema, Pydantic model cho contract/validation ở boundary và event,
  `dataclass(frozen=True)` cho value object nội bộ. Không dùng một type cho cả ba vai trò để tránh mapping.
- `Protocol` khi consumer cần interface nhỏ và có nhiều implementation/adapter. ABC chỉ khi cần chia sẻ
  lifecycle hoặc framework bắt buộc; không tạo interface dự phòng cho một use case.
- Exception biểu diễn thất bại, không làm control flow trong vòng lặp nóng. Hierarchy nông; bắt exception
  cụ thể tại boundary chịu trách nhiệm chuyển đổi/log/retry.

```python
# ✅ Consumer phụ thuộc capability nhỏ; adapter giữ chi tiết provider, test thay bằng fake.
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

```

## 6. Format, import và static analysis

- Python 3.14, indent 4 space, UTF-8, LF, dòng tối đa 100 ký tự, nháy kép.
- Chỉ dùng `ruff format`; không chạy Black, isort hoặc flake8 riêng.
- Import theo nhóm stdlib → third-party → `config`, `common`, `infrastructure`, `apps`; để Ruff sắp xếp.
- `ruff check` là lint chuẩn. Không tắt rule ở cấp file/project nếu lý do không áp dụng cho toàn phạm vi đó.
- `mypy` với Django/DRF plugin là type checker chuẩn; service, selector và contract đạt mức strict cấu hình
  trong `pyproject.toml`.
- File không phải Python theo `.editorconfig` và pre-commit hooks. Project không dùng Prettier.
- Không sửa tay vùng `# BEGIN gen_importlinter` trong `pyproject.toml`; chạy generator ghi ở [02](./02-backend-structure.md#6-kiểm-tra-ranh-giới-bằng-import-linter).
- `make fmt` tự sửa format; `make lint` là cổng kiểm tra, phải giữ cùng thứ tự với CI.

## 7. Django model và migration

- Model nghiệp vụ do dự án sở hữu kế thừa `common.models.BaseModel`, dùng UUID v7, không tự khai `id`.
  Model địa giới, framework và audit/history dùng khoá riêng; xem [03](./03-data-model.md) và
  [ADR-0008](../adr/0008-uuid-v7-primary-keys.md).
- `TextChoices` đặt ở cấp module; không tạo alias class chỉ khác hoa/thường với field (`Status` cạnh `status`).
- Khai báo rõ `Meta.db_table`, constraint và index theo [03](./03-data-model.md); không chỉ dựa vào
  validation ở serializer.
- Không đặt business workflow trong `save()`, signal hoặc serializer; workflow thuộc service.
- Cột `NOT NULL` thêm vào bảng đã có dữ liệu cần kế hoạch migration tương thích ngược. Khi code cũ còn
  INSERT trong rolling deploy, dùng `db_default`, không chỉ `default` (ví dụ ở mục 11.3).
- Không sửa migration đã chạy ở môi trường dùng chung; tạo migration mới.
- Migration do Django sinh giữ style framework (mục 1).

### 7.1. Model, manager và command

- Model giữ field, constraint và invariant cục bộ kiểm tra được từ chính instance. Workflow chạm nhiều
  aggregate, provider hoặc event thuộc service, kể cả khi viết trong model method ngắn hơn.
- Custom `QuerySet`/manager chỉ chứa query primitive compose được, không che side effect. Query theo use
  case vẫn đặt sau selector.
- Chuyển trạng thái hàng loạt của một model (`UPDATE` theo danh sách id caller đã khoá và lọc) là
  `@classmethod` của model, không phải method của `QuerySet`: model quyết cột nào được ghi, `QuerySet` giữ
  là primitive không side effect. Ví dụ: `EventDelivery.reopen`, `EventDelivery.mark_dispatched`.
- Không dùng signal cho workflow nghiệp vụ. Signal chỉ cho tích hợp hạ tầng cục bộ, phải có lý do vì sao
  explicit call không phù hợp và có test chứng minh transaction semantics.
- Django Admin và management command là adapter: parse/validate input, gọi service/selector, trình bày
  kết quả. Không sao chép nghiệp vụ vào `ModelAdmin`, `handle()` hoặc form admin, để mọi entry point
  (API, task, command, admin) dùng chung validation, transaction, event và audit.
- Code chạy lúc import hoặc `AppConfig.ready()` không query database hay gọi mạng. Import đăng ký check,
  event handler hoặc admin phải idempotent và tránh circular import.

## 8. Comment và docstring

- Public function trong `contracts.py` và `services/` có Google-style docstring mô tả contract.
- Chỉ ghi mã `BR-xxx` và mục `Raises` khi thực sự áp dụng; không chèn reference hình thức hoặc lặp type hints.
- Comment giải thích **vì sao**, constraint hoặc đánh đổi; không diễn giải từng dòng code.
- Reference tài liệu bằng file và mục ổn định khi constraint không thể hiện đủ trong code.
- Xoá comment lỗi thời trong cùng thay đổi; comment sai nguy hiểm hơn không có comment.

## 9. Test

Chiến lược, marker, coverage và CI gate nằm ở [12](./12-testing-strategy.md). Khi viết test:

- Dùng `factory-boy`; không dùng JSON fixture.
- Không mock ORM. Test trên PostgreSQL thật và chỉ fake hệ thống bên ngoài.
- Mỗi public service function có bằng chứng cho happy path và từng hành vi lỗi contract công bố; có thể
  dùng flow test nếu đó là cấp kiểm chứng phù hợp nhất.
- Test business rule gắn `@pytest.mark.br("BR-xxx")`.
- Cố định thời gian bằng `time-machine`; không patch `timezone.now()` thủ công.
- Factory đặt trong module sở hữu và chỉ dùng factory của module đó hoặc module lớp dưới.
- Hành vi cần commit thật, nhiều connection hoặc lock dùng `django_db(transaction=True)`.
- Service test cần chạy callback `on_commit` dùng `django_capture_on_commit_callbacks(execute=True)`;
  flow test dùng `drain_events()`.
- Trong `pytest.raises`, chỉ để một lời gọi có thể ném exception.
- Assert dạng `actual == expected`; đặt kết quả thực vào biến khi biểu thức có thể gây hiểu nhầm.
- Model test kế thừa `common.models.BaseModel` khai báo manager phù hợp để mypy không suy sai kiểu.
- Tên test mô tả hành vi quan sát được, không mô tả implementation.
- Test độc lập thứ tự chạy, không phụ thuộc dữ liệu còn lại từ test khác.

## 10. Logging, exception và dữ liệu nhạy cảm

- Dùng `logger = structlog.get_logger(__name__)`; không dùng `print` hoặc `logging.getLogger` trong code
  ứng dụng.
- Message là tên sự kiện tiếng Anh `snake_case`; dữ liệu truyền bằng keyword, không ghép bằng f-string hoặc `%`.
- Log level: domain error dự kiến ở API thường `INFO`; event/job bị từ chối cần quan sát có thể `WARNING`;
  lỗi ngoài dự kiến `ERROR`. Consumer và task xem [07](./07-async-events-jobs.md).
- Không log PII, IP thô, email, số điện thoại, địa chỉ, token, mật khẩu, secret hoặc payload thanh toán.
  Processor redact chỉ là lưới an toàn, không phải quyền log dữ liệu nhạy cảm.
- Exception gốc có thể chứa secret hoặc connection URL thì raise exception đã lọc bằng `from None`.
- Không bắt `Exception` rồi im lặng. Phục hồi được thì log đủ identifier không nhạy cảm và giữ semantics
  retry; nếu không, để exception lên boundary chịu trách nhiệm xử lý.

## 11. Mẫu code Good/Bad

Ví dụ minh hoạ hình dạng code, có thể lược import; khi type hoặc namespace có thể nhập nhằng thì ghi rõ
nguồn. Tên model/service chỉ là ví dụ; khi triển khai dùng đúng thuật ngữ trong `GLOSSARY.md` và API thật
của module. View mỏng gọi service: xem ví dụ ở mục 3.1.

### 11.1. Module khác chỉ gọi public contract

```python
# ✅ `ordering` gọi public API của `inventory`.
from apps.inventory.contracts import reserve_stock

reservation = reserve_stock(reference=order.code, items=stock_lines, expires_at=order.expires_at)

# ❌ Import model/service nội bộ của module khác hoặc traversal ORM qua quan hệ của nó.
from apps.inventory.models import StockItem
from apps.inventory.services.reservations import create_reservation

stock = StockItem.objects.select_for_update().get(variant_id=variant_id)
shipment__provider__status = order.shipment.provider.status
```

### 11.2. Transaction không chứa I/O bên ngoài

```python
# ✅ Ghi DB/outbox trong transaction và enqueue sau commit.
def confirm_order(*, order_id: UUID) -> Order:
    """Xác nhận Đơn hàng và lên lịch tạo Vận đơn sau khi transaction commit."""
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        order.status = OrderStatus.CONFIRMED
        order.save(update_fields=["status", "updated_at"])
        publish(OrderConfirmedV1(order_id=order.id))
        enqueue_on_commit("shipping.create_shipment", order_id=str(order.id))
    return order


# ❌ Gọi HTTP và đẩy Celery task khi transaction chưa commit.
with transaction.atomic():
    order.status = OrderStatus.CONFIRMED
    order.save()
    ghn_client.create_shipment(order)  # HTTP có thể treo trong lúc giữ DB lock.
    create_shipment.delay(order.id)  # Worker có thể chạy trước khi DB commit.
```

### 11.3. Model giữ schema; workflow nằm trong service

```python
# ✅
class Order(common.models.BaseModel):
    status = models.CharField(max_length=32, choices=OrderStatus.choices)

    class Meta:
        db_table = "ordering_order"
        constraints = (
            models.CheckConstraint(
                condition=models.Q(status__in=OrderStatus.values), name="ordering_order_status_valid"
            ),
        )


# ❌ `save()` che giấu workflow và side effect.
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

### 11.4. Comment và docstring giải thích lý do

```python
# ✅
def reserve_stock(
    *, reference: str, items: Sequence[StockLine], expires_at: datetime
) -> Reservation:
    """Giữ Tồn kho cho Đơn thanh toán online.

    Áp dụng BR-INV-05. Các StockItem phải được khoá theo `variant_id` tăng dần để mọi
    checkout dùng cùng thứ tự khoá.

    Raises:
        OutOfStock: Một Biến thể không còn đủ Số lượng bán được.
    """


# ❌ Docstring lặp type hints, comment diễn giải code.
def reserve_stock(reference, items, expires_at):
    """Reserve stock.

    Args:
        reference: The reference.
    """
    # Loop through every item.
    for item in items: ...
```

### 11.5. Test một hành vi, một nguyên nhân thất bại

```python
# ✅
@pytest.mark.br("BR-INV-05")
def test_reserve_stock_rejects_quantity_above_available(stock_item: StockItem) -> None:
    quantity = stock_item.available_quantity + 1
    items = [StockLine(variant_id=stock_item.variant_id, quantity=quantity)]
    expires_at = timezone.now() + timedelta(minutes=15)

    with pytest.raises(OutOfStock):
        reserve_stock(reference="FS0001", items=items, expires_at=expires_at)

    stock_item.refresh_from_db()
    actual = stock_item.reserved_quantity
    assert actual == 0


# ❌ Mock ORM, nhiều lời gọi có thể fail trong `pytest.raises`, assert không rõ đối tượng.
@patch("apps.inventory.models.StockItem.objects.get")
def test_stock(mock_get):
    with pytest.raises(Exception):
        stock = build_stock()
        reserve_stock("FS0001", [(stock.variant_id, 99)], None)
    assert stock.reserved_quantity == 0
```

### 11.6. Structured logging không chứa PII

```python
# ✅
logger.info("stock_reserved", variant_id=variant.id, quantity=quantity)
logger.warning("shipping_fee_fallback", provider="ghn", reason="timeout")
logger.info(
    "order_confirmed",
    order_id=str(order.id),
    order_code=order.code,
    payment_method=order.payment_method,
)

# ❌
print(f"Confirmed order for {order.customer_email}")
logger.info(f"order confirmed: {order.__dict__}")
logger.info("payment_callback", payload=request.data, access_token=token)
```

### 11.7. Suppression phải hẹp và có lý do

```python
# ✅
result = subprocess.run(  # noqa: S603 -- executable là binary cố định trong virtualenv.
    [LINT_IMPORTS, "--config", str(config_path)], check=False
)

# ❌
# ruff: noqa
result = subprocess.run(command, shell=True)  # type: ignore
```

## 12. Checklist hoàn tất thay đổi

- Code đúng module, đúng tầng; không bypass contract hoặc ORM traversal sang module khác.
- Tên, type hints, docstring và logging theo tài liệu này.
- Migration, API contract, business rule, glossary và tài liệu liên quan được cập nhật nếu thay đổi chạm tới.
- Test bao phủ happy path, domain error và cạnh tranh/transaction khi có liên quan.
- Không thêm secret, PII, debug output, suppression rộng hoặc TODO không có chủ sở hữu.
- Với thay đổi code, đã chạy `make fmt`, `make lint` và test tương xứng với rủi ro; full test suite là cổng
  trước merge/release. Mọi giới hạn kiểm chứng được báo rõ trong kết quả.
