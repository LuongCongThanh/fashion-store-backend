from shared.exceptions import DomainError, RetryLater


class OutOfStock(DomainError):
    code = "OUT_OF_STOCK"
    http_status = 409
    message = "Một số sản phẩm không đủ hàng."


def test_subclass_uses_class_defaults() -> None:
    error = OutOfStock()

    assert (error.code, error.http_status, error.details) == ("OUT_OF_STOCK", 409, {})
    assert str(error) == "Một số sản phẩm không đủ hàng."


def test_message_and_details_can_be_overridden_when_raised() -> None:
    error = OutOfStock("Hết hàng", details={"items": [{"sku": "A", "available": 0}]})

    assert error.message == "Hết hàng"
    assert error.details == {"items": [{"sku": "A", "available": 0}]}
    assert OutOfStock.message == "Một số sản phẩm không đủ hàng."


def test_retry_later_is_not_a_domain_error() -> None:
    # Consumer phân biệt hai loại: DomainError thì rejected, RetryLater thì giữ pending
    assert not issubclass(RetryLater, DomainError)
