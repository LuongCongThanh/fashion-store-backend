"""Sự kiện qua outbox (07 mục 1, ADR 0007)."""

from shared.events.base import DomainEvent
from shared.events.publisher import publish
from shared.events.registry import handles
from shared.events.selectors import delivery_lag, get_delivery_outcomes

__all__ = ["DomainEvent", "delivery_lag", "get_delivery_outcomes", "handles", "publish"]
