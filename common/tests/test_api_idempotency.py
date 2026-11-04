import hashlib
import threading
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
import time_machine
from django.db import connection, transaction
from rest_framework.test import APIClient

from common import idempotency
from common.idempotency import LEASE, Claim, LeaseLost
from common.idempotency.http import request_hash
from common.idempotency.models import IdempotencyKey, IdempotencyStatus
from common.models import uuid7
from common.tests._helpers import error_of
from common.tests.api_urls import IdempotentEffect, OutOfStock
from common.tests.factories import IdempotencyKeyFactory

pytestmark = pytest.mark.urls("common.tests.api_urls")

URL = "/idempotent/FS2610-7K3QZD/"
# UUID mẫu của Idempotency-Key, không phải secret
KEY = "0192f3a4-5b6c-7d8e-9f01-23456789abcd"  # gitleaks:allow
CART_TOKEN = "cart-token-a"
HEADERS = {"Idempotency-Key": KEY, "X-Cart-Token": CART_TOKEN}
# Scope mà `begin` dựng cho `post(...)` mặc định
SCOPE = f"POST /idempotent/FS2610-7K3QZD|cart:{hashlib.sha256(CART_TOKEN.encode()).hexdigest()}"
NOW = datetime(2026, 10, 30, 8, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def effect_table(db: None) -> Iterator[None]:
    # Model chỉ dùng trong test, không có migration
    with connection.schema_editor() as editor:
        editor.create_model(IdempotentEffect)
    yield
    with connection.schema_editor() as editor:
        editor.delete_model(IdempotentEffect)


def send(
    method: str,
    url: str,
    body: dict[str, Any],
    *,
    key: str | None = KEY,
    cart_token: str | None = CART_TOKEN,
    client: APIClient | None = None,
) -> Any:
    headers: dict[str, str] = {}
    if key is not None:
        headers["Idempotency-Key"] = key
    if cart_token is not None:
        headers["X-Cart-Token"] = cart_token
    return getattr(client or APIClient(), method)(url, body, format="json", headers=headers)


def post(body: dict[str, Any], **kwargs: Any) -> Any:
    return send("post", URL, body, **kwargs)


def account_client(pk: int) -> APIClient:
    client = APIClient()
    user: Any = SimpleNamespace(pk=pk, is_authenticated=True)
    client.force_authenticate(user=user)
    return client


def test_same_key_same_body_replays_saved_response_without_rerun() -> None:
    first = post({"note": "a"})
    second = post({"note": "a"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json() == first.json()
    assert IdempotentEffect.objects.count() == 1


def test_body_key_order_does_not_change_request_hash() -> None:
    first = post({"note": "a", "quantity": 2})
    second = post({"quantity": 2, "note": "a"})

    assert second.status_code == 201
    assert second.json() == first.json()
    assert IdempotentEffect.objects.count() == 1


def test_same_key_different_body_returns_idempotency_conflict() -> None:
    post({"note": "a"})

    response = post({"note": "b"})

    assert response.status_code == 409
    assert error_of(response)["code"] == "IDEMPOTENCY_CONFLICT"
    assert IdempotentEffect.objects.count() == 1


def test_same_key_different_account_does_not_see_other_result() -> None:
    first = post({"note": "a"}, cart_token=None, client=account_client(1))
    second = post({"note": "a"}, cart_token=None, client=account_client(2))

    assert second.status_code == 201
    assert second.json()["effect_id"] != first.json()["effect_id"]
    assert IdempotentEffect.objects.count() == 2


def test_same_key_different_cart_token_does_not_see_other_result() -> None:
    first = post({"note": "a"}, cart_token="cart-token-a")
    second = post({"note": "a"}, cart_token="cart-token-b")

    assert second.status_code == 201
    assert second.json()["effect_id"] != first.json()["effect_id"]
    assert IdempotentEffect.objects.count() == 2


@pytest.mark.parametrize(("method", "url"), [("post", "/idempotent/FS2610-OTHER1/"), ("put", URL)])
def test_same_key_different_path_or_method_does_not_see_other_result(method: str, url: str) -> None:
    first = post({"note": "a"})
    second = send(method, url, {"note": "a"})

    assert second.status_code == 201
    assert second.json()["effect_id"] != first.json()["effect_id"]
    assert IdempotentEffect.objects.count() == 2


def test_account_scope_is_method_path_and_account_pk() -> None:
    post({"note": "a"}, cart_token=None, client=account_client(7))

    assert IdempotencyKey.objects.get().scope == "POST /idempotent/FS2610-7K3QZD|account:7"


def test_multipart_body_returns_unsupported_media_type() -> None:
    # QueryDict gộp giá trị lặp và chứa file: không chuẩn hoá được để tính request_hash
    response = APIClient().post(URL, {"note": "a"}, format="multipart", headers=HEADERS)

    assert response.status_code == 415
    assert error_of(response)["code"] == "UNSUPPORTED_MEDIA_TYPE"
    assert IdempotentEffect.objects.count() == 0
    assert not IdempotencyKey.objects.exists()


def test_lone_surrogate_in_body_is_hashed() -> None:
    # JSON hợp lệ, nhưng `\ud800` không encode được bằng UTF-8 strict
    raw = '{"note": "a", "extra": "\\ud800"}'

    first = APIClient().post(URL, raw, content_type="application/json", headers=HEADERS)
    second = APIClient().post(URL, raw, content_type="application/json", headers=HEADERS)

    assert first.status_code == 201
    assert second.json() == first.json()
    assert IdempotentEffect.objects.count() == 1


def test_claim_inside_outer_transaction_raises() -> None:
    # Transaction ngoài giữ khoá dòng key tới khi nó commit và nuốt việc nhả key
    key = uuid.UUID(KEY)
    body_hash = request_hash({"note": "a"})
    with transaction.atomic(), pytest.raises(RuntimeError):
        idempotency.claim(SCOPE, key, body_hash)

    assert not IdempotencyKey.objects.exists()


def test_request_without_identity_returns_validation_error() -> None:
    response = post({"note": "a"}, cart_token=None)

    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]["fields"]) == {"X-Cart-Token"}
    assert IdempotentEffect.objects.count() == 0


def test_missing_key_returns_validation_error() -> None:
    response = post({"note": "a"}, key=None)

    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]["fields"]) == {"Idempotency-Key"}
    assert IdempotentEffect.objects.count() == 0


def test_non_uuid_key_returns_validation_error() -> None:
    response = post({"note": "a"}, key="order-1")

    assert response.status_code == 400
    error = error_of(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert set(error["details"]["fields"]) == {"Idempotency-Key"}
    assert IdempotentEffect.objects.count() == 0


def in_progress_key(body: dict[str, Any], **kwargs: Any) -> IdempotencyKey:
    """Key mà một worker khác đang giữ cho `post(body)`."""
    return IdempotencyKeyFactory.create(
        scope=SCOPE, key=KEY, request_hash=request_hash(body), **kwargs
    )


def claim_of(row: IdempotencyKey) -> Claim:
    """`Claim` mà worker đang giữ `row` đã nhận từ `begin`."""
    assert row.lease_token is not None
    return Claim(key_id=row.pk, operation_id=row.operation_id, lease_token=row.lease_token)


def test_in_progress_key_returns_pending_with_retry_after() -> None:
    in_progress_key({"note": "a"})

    response = post({"note": "a"})

    assert response.status_code == 202
    assert response.json() == {"code": "IDEMPOTENCY_IN_PROGRESS", "retry_after": 3}
    assert response.headers["Retry-After"] == "3"
    assert IdempotentEffect.objects.count() == 0


def test_different_body_conflicts_even_while_in_progress() -> None:
    in_progress_key({"note": "a"})

    response = post({"note": "b"})

    assert response.status_code == 409
    assert error_of(response)["code"] == "IDEMPOTENCY_CONFLICT"
    assert IdempotentEffect.objects.count() == 0


def test_expired_lease_is_taken_over() -> None:
    with time_machine.travel(NOW, tick=False) as traveller:
        stale = in_progress_key({"note": "a"})
        traveller.shift(LEASE)

        response = post({"note": "a"})

    assert response.status_code == 201
    assert response.json()["operation_id"] == str(stale.operation_id)
    assert IdempotentEffect.objects.count() == 1
    stale.refresh_from_db()
    assert stale.status == IdempotencyStatus.COMPLETED


def finish_with_effect(claim: Claim) -> None:
    """Tác động nghiệp vụ của worker giữ `claim`, viết như view: ghi tác động rồi lưu kết quả."""
    with claim, transaction.atomic():
        IdempotentEffect.objects.create(note="stale")
        claim.complete(201, {"note": "stale"})


def test_stale_lease_complete_rolls_back_effect() -> None:
    with time_machine.travel(NOW, tick=False) as traveller:
        stale = in_progress_key({"note": "a"})
        old_worker = claim_of(stale)
        traveller.shift(LEASE)
        taken_over = post({"note": "a"})

        with pytest.raises(LeaseLost):
            finish_with_effect(old_worker)

    assert IdempotentEffect.objects.get().note == "a"
    stale.refresh_from_db()
    assert stale.response_body == taken_over.json()


def test_complete_after_key_deleted_raises_lease_lost() -> None:
    row = in_progress_key({"note": "a"})
    claim = claim_of(row)
    row.delete()

    with pytest.raises(LeaseLost), transaction.atomic():
        claim.complete(201, {"note": "a"})


def test_complete_without_resource_id_keeps_attached_resource_id() -> None:
    resource_id = uuid7()
    with time_machine.travel(NOW, tick=False) as traveller:
        attached = in_progress_key({"note": "a"}, resource_id=resource_id)
        traveller.shift(1)

        with transaction.atomic():
            claim_of(attached).complete(201, {"note": "a"})

    attached.refresh_from_db()
    assert attached.status == IdempotencyStatus.COMPLETED
    assert attached.resource_id == resource_id
    assert attached.updated_at == NOW + timedelta(seconds=1)


def test_business_rollback_leaves_key_not_completed() -> None:
    body = {"note": "a", "fail_after_effect": True}

    first = post(body)
    retry = post(body)

    assert first.status_code == 409
    assert error_of(first)["code"] == "OUT_OF_STOCK"
    # Gửi lại cùng key chạy lại từ đầu, không nhận 202 hay kết quả lỗi đã lưu
    assert error_of(retry)["code"] == "OUT_OF_STOCK"
    assert IdempotentEffect.objects.count() == 0
    assert not IdempotencyKey.objects.exists()


def test_error_after_complete_leaves_key_not_completed() -> None:
    body = {"note": "a", "fail_after_complete": True}

    first = post(body)
    completed = IdempotencyKey.objects.filter(status=IdempotencyStatus.COMPLETED).exists()
    retry = post(body)

    assert error_of(first)["code"] == "OUT_OF_STOCK"
    assert not completed
    # Kết quả 201 đã lưu rollback cùng tác động: gửi lại chạy lại tác động, không replay
    assert error_of(retry)["code"] == "OUT_OF_STOCK"
    assert IdempotentEffect.objects.count() == 0


def fail_after_effect(claim: Claim) -> None:
    with claim, transaction.atomic():
        IdempotentEffect.objects.create(note="a")
        raise OutOfStock


def test_rollback_keeps_key_with_resource_id() -> None:
    # Payment đã gắn vào key trước khi gọi gateway: luồng khôi phục cần dòng này
    attached = in_progress_key({"note": "a"}, resource_id=uuid7())
    claim = claim_of(attached)

    with pytest.raises(OutOfStock):
        fail_after_effect(claim)

    assert IdempotencyKey.objects.filter(pk=attached.pk).exists()
    assert IdempotentEffect.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_key_runs_effect_once(monkeypatch: pytest.MonkeyPatch) -> None:
    responded = threading.Event()
    complete = Claim.complete

    def complete_after_other_responds(claim: Claim, *args: Any, **kwargs: Any) -> None:
        # Bên giữ key chỉ lưu kết quả sau khi bên kia đã nhận response, để bên kia thấy
        # key còn `in_progress` chứ không phải kết quả đã lưu
        responded.wait(timeout=5)
        complete(claim, *args, **kwargs)

    monkeypatch.setattr(Claim, "complete", complete_after_other_responds)
    barrier = threading.Barrier(2)
    responses: list[Any] = []
    errors: list[BaseException] = []

    def run() -> None:
        try:
            barrier.wait()
            responses.append(post({"note": "a"}))
            responded.set()
        except BaseException as exc:
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 202]
    created = next(response for response in responses if response.status_code == 201)
    assert IdempotentEffect.objects.count() == 1
    assert created.json()["operation_id"] == str(IdempotencyKey.objects.get().operation_id)
