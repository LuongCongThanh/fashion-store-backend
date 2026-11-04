"""Value object tiền VND, lưu số đồng nguyên (03 mục 0.5)."""

from dataclasses import dataclass
from functools import total_ordering
from typing import Self

CURRENCIES = frozenset({"VND"})


@total_ordering
@dataclass(frozen=True, slots=True)
class Money:
    """Số tiền nguyên theo đồng.

    Cho phép số âm cho các phép tính trung gian (ví dụ chênh lệch khi tiền về sai số tiền);
    ràng buộc `>= 0` nằm ở cột DB và quy tắc nghiệp vụ. Không có phép chia: cách làm tròn
    thuộc nghiệp vụ (BR-RET-07, BR-REV-01).
    """

    amount: int
    currency: str = "VND"

    def __post_init__(self) -> None:
        # bool là lớp con của int nên phải loại riêng
        if type(self.amount) is not int:
            raise TypeError(f"Money.amount phải là int, nhận {type(self.amount).__name__}")
        if self.currency not in CURRENCIES:
            raise ValueError(f"Không hỗ trợ đơn vị tiền {self.currency!r}")

    def _check_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"Không tính được giữa {self.currency} và {other.currency}")

    def __add__(self, other: object) -> Self:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return type(self)(self.amount + other.amount, self.currency)

    def __radd__(self, other: object) -> Self:
        # `sum()` bắt đầu từ số 0; chỉ nhận đúng 0, không mở cửa cộng Money với int bất kỳ
        if type(other) is int and other == 0:
            return self
        return NotImplemented

    def __sub__(self, other: object) -> Self:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return type(self)(self.amount - other.amount, self.currency)

    def __mul__(self, factor: object) -> Self:
        if type(factor) is not int:
            return NotImplemented
        return type(self)(self.amount * factor, self.currency)

    __rmul__ = __mul__

    def __neg__(self) -> Self:
        return type(self)(-self.amount, self.currency)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount < other.amount
