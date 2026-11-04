"""Small, well-structured example: a review of this file should find (almost) nothing."""

from dataclasses import dataclass

TAX_RATE = 0.13


@dataclass(frozen=True)
class LineItem:
    name: str
    unit_price: float
    quantity: int = 1

    def subtotal(self) -> float:
        return self.unit_price * self.quantity


def order_total(items: list[LineItem], tax_rate: float = TAX_RATE) -> float:
    """Return the order total including tax, rounded to cents."""
    subtotal = sum(item.subtotal() for item in items)
    return round(subtotal * (1 + tax_rate), 2)
