from trading_objects import Product
from .config import PAYOUT

class PairedFlipProduct(Product):
    def __init__(self, symbol: str) -> None:
        super().__init__(symbol)

    def payout(self) -> None:
        return PAYOUT
