"""Billing and tax calculation module."""

def calculate_sales_tax(amount: float) -> float:
    """Calculates state tax at 8.25 percent."""
    return round(amount * 0.0825, 2)


def apply_promotional_discount(price: float, code: str) -> float:
    if code == "SPRING20":
        return round(price * 0.80, 2)
    return price
