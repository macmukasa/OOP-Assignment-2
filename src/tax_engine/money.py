"""Immutable Money Value Object for Ugandan Shillings (UGX).

Strictly enforces decimal.Decimal arithmetic, rejecting floating-point values
to eliminate precision loss and non-deterministic IEEE 754 rounding errors.
"""

from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Any
from .exceptions import CurrencyMismatchError, InvalidIncomeError


class Money:
    """Immutable Value Object representing an amount of money in Ugandan Shillings (UGX).

    Attributes:
        amount (Decimal): Quantized monetary amount.
        currency (str): Currency code (defaults to 'UGX').
    """

    __slots__ = ("_amount", "_currency")

    # Standard UGX quantization: 2 decimal places for fractional precision,
    # with ROUND_HALF_UP tie-breaking per financial auditing standards.
    EXPONENT_TWO_PLACES = Decimal("0.01")
    EXPONENT_WHOLE = Decimal("1")
    DEFAULT_ROUNDING = ROUND_HALF_UP

    def __init__(
        self,
        amount: Union[Decimal, int, str, "Money"],
        currency: str = "UGX",
        round_cents: bool = True,
    ) -> None:
        """Initialize a Money instance.

        Args:
            amount: Amount as Decimal, int, str, or existing Money. Float is strictly rejected.
            currency: 3-letter currency code, defaults to 'UGX'.
            round_cents: Whether to quantize to two decimal places upon instantiation.

        Raises:
            TypeError: If amount is float or unsupported type.
            InvalidIncomeError: If string cannot be converted to Decimal.
        """
        if isinstance(amount, float):
            raise TypeError(
                f"Floating-point value {amount!r} is strictly forbidden for financial calculations. "
                "Use decimal.Decimal, integer, or string instead."
            )

        if isinstance(amount, Money):
            object.__setattr__(self, "_amount", amount._amount)
            object.__setattr__(self, "_currency", amount._currency)
            return

        curr_clean = str(currency).strip().upper()
        if not curr_clean:
            raise ValueError("Currency code must be a non-empty string.")

        if isinstance(amount, (int, Decimal, str)):
            try:
                dec_val = Decimal(str(amount).strip())
            except (InvalidOperation, ValueError) as err:
                raise InvalidIncomeError(f"Cannot parse monetary amount from {amount!r}: {err}") from err
        else:
            raise TypeError(f"Unsupported type {type(amount).__name__} for monetary amount.")

        if round_cents:
            dec_val = dec_val.quantize(self.EXPONENT_TWO_PLACES, rounding=self.DEFAULT_ROUNDING)

        object.__setattr__(self, "_amount", dec_val)
        object.__setattr__(self, "_currency", curr_clean)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(f"{self.__class__.__name__} instances are immutable.")

    def __delattr__(self, name: str) -> None:
        raise AttributeError(f"{self.__class__.__name__} instances are immutable.")

    @classmethod
    def zero(cls, currency: str = "UGX") -> Money:
        """Return a zero Money object."""
        return cls(Decimal("0.00"), currency=currency, round_cents=False)

    @classmethod
    def from_shillings(cls, shillings: Union[int, Decimal, str], currency: str = "UGX") -> Money:
        """Factory method to construct Money rounded to whole shillings."""
        m = cls(shillings, currency=currency, round_cents=False)
        return m.round_to_shilling()

    @property
    def amount(self) -> Decimal:
        """Return the underlying Decimal amount."""
        return self._amount

    @property
    def currency(self) -> str:
        """Return the currency code."""
        return self._currency

    def round_to_shilling(self) -> Money:
        """Return a new Money object rounded to the nearest whole shilling."""
        rounded = self._amount.quantize(self.EXPONENT_WHOLE, rounding=self.DEFAULT_ROUNDING)
        return Money(rounded, currency=self._currency, round_cents=False)

    def is_negative(self) -> bool:
        """Return True if amount is strictly less than zero."""
        return self._amount < Decimal("0")

    def is_zero(self) -> bool:
        """Return True if amount is zero."""
        return self._amount == Decimal("0")

    def _assert_same_currency(self, other: Any) -> None:
        """Assert that other is a Money instance with identical currency."""
        if not isinstance(other, Money):
            raise TypeError(f"Operand must be Money, got {type(other).__name__}")
        if self._currency != other._currency:
            raise CurrencyMismatchError(
                f"Cannot operate between currencies '{self._currency}' and '{other._currency}'"
            )

    # Operator overloading
    def __add__(self, other: Any) -> Money:
        self._assert_same_currency(other)
        return Money(self._amount + other._amount, currency=self._currency)

    def __radd__(self, other: Any) -> Money:
        if other == 0:  # Enables sum() builtin
            return self
        return self.__add__(other)

    def __sub__(self, other: Any) -> Money:
        self._assert_same_currency(other)
        return Money(self._amount - other._amount, currency=self._currency)

    def __mul__(self, scalar: Any) -> Money:
        if isinstance(scalar, float):
            raise TypeError(
                f"Multiplication by float {scalar!r} is forbidden. Use Decimal or int."
            )
        if isinstance(scalar, (int, Decimal)):
            new_amount = self._amount * Decimal(str(scalar))
            return Money(new_amount, currency=self._currency)
        return NotImplemented

    def __rmul__(self, scalar: Any) -> Money:
        return self.__mul__(scalar)

    def __truediv__(self, other: Any) -> Union[Money, Decimal]:
        if isinstance(other, float):
            raise TypeError(
                f"Division by float {other!r} is forbidden. Use Decimal, int, or Money."
            )
        if isinstance(other, Money):
            self._assert_same_currency(other)
            if other._amount == Decimal("0"):
                raise ZeroDivisionError("Cannot divide by zero Money.")
            return self._amount / other._amount
        if isinstance(other, (int, Decimal)):
            divisor = Decimal(str(other))
            if divisor == Decimal("0"):
                raise ZeroDivisionError("Cannot divide Money by zero.")
            return Money(self._amount / divisor, currency=self._currency)
        return NotImplemented

    def __neg__(self) -> Money:
        return Money(-self._amount, currency=self._currency, round_cents=False)

    def __abs__(self) -> Money:
        return Money(abs(self._amount), currency=self._currency, round_cents=False)

    def __lt__(self, other: Any) -> bool:
        self._assert_same_currency(other)
        return self._amount < other._amount

    def __le__(self, other: Any) -> bool:
        self._assert_same_currency(other)
        return self._amount <= other._amount

    def __gt__(self, other: Any) -> bool:
        self._assert_same_currency(other)
        return self._amount > other._amount

    def __ge__(self, other: Any) -> bool:
        self._assert_same_currency(other)
        return self._amount >= other._amount

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return False
        return self._currency == other._currency and self._amount == other._amount

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash((self._amount, self._currency))

    def __bool__(self) -> bool:
        return self._amount != Decimal("0")

    def __int__(self) -> int:
        return int(self.round_to_shilling()._amount)

    def __repr__(self) -> str:
        return f"Money('{self._amount}', currency='{self._currency}')"

    def __str__(self) -> str:
        # Standard formatted display with thousand separators
        return f"{self._currency} {self._amount:,.2f}"

    def format_ugx(self, with_cents: bool = False) -> str:
        """Format as human-readable Ugandan currency string (e.g. 'UGX 335,000')."""
        if with_cents:
            return f"UGX {self._amount:,.2f}"
        return f"UGX {int(self.round_to_shilling()._amount):,}"
