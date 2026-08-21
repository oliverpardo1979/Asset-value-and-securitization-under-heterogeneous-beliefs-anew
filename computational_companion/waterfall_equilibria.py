"""Compute the least and greatest waterfall-equilibrium prices.

The implementation follows Proposition 1 in the paper.  It is intentionally
small: economies may have at most three states and tranchings may have at most
three tranches.  The number of subjective theories is unrestricted.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.typing import NDArray


Array = NDArray[np.float64]
MAX_STATES = 3
MAX_TRANCHES = 3


@dataclass
class WaterfallEconomy:
    """Inputs needed by the waterfall price-forming operator.

    ``theories[f, x, y]`` is the probability assigned by theory ``f`` to
    next-period state ``y`` conditional on current state ``x``.

    ``attachment_points`` contains the lower endpoint of each tranche.  It
    must start at zero and be strictly increasing.  For example, ``(0, 14,
    17)`` represents ``[0, 14)``, ``[14, 17)``, and ``[17, infinity)``.
    """

    dividends: Sequence[float]
    gross_returns: float | Sequence[float]
    theories: Sequence[Sequence[Sequence[float]]]
    attachment_points: Sequence[float]
    state_names: Sequence[str] | None = None
    theory_names: Sequence[str] | None = None

    def __post_init__(self) -> None:
        self.dividends = np.asarray(self.dividends, dtype=float)
        if self.dividends.ndim != 1:
            raise ValueError("dividends must be a one-dimensional vector")

        state_count = self.dividends.size
        if not 1 <= state_count <= MAX_STATES:
            raise ValueError(f"the number of states must be between 1 and {MAX_STATES}")
        if np.any(~np.isfinite(self.dividends)) or np.any(self.dividends < 0):
            raise ValueError("dividends must be finite and nonnegative")

        returns = np.asarray(self.gross_returns, dtype=float)
        if returns.ndim == 0:
            returns = np.full(state_count, float(returns))
        if returns.shape != (state_count,):
            raise ValueError("gross_returns must be a scalar or one value per state")
        if np.any(~np.isfinite(returns)) or np.any(returns <= 1):
            raise ValueError("every gross return must be finite and greater than one")
        self.gross_returns = returns

        theories = np.asarray(self.theories, dtype=float)
        if theories.ndim == 2:
            theories = theories[np.newaxis, :, :]
        if theories.ndim != 3 or theories.shape[1:] != (state_count, state_count):
            raise ValueError(
                "theories must have shape (number of theories, states, states)"
            )
        if theories.shape[0] == 0:
            raise ValueError("at least one theory is required")
        if np.any(~np.isfinite(theories)) or np.any(theories < 0):
            raise ValueError("transition probabilities must be finite and nonnegative")
        if not np.allclose(theories.sum(axis=2), 1.0, atol=1e-12, rtol=0.0):
            raise ValueError("every row of every transition matrix must sum to one")
        self.theories = theories

        attachments = np.asarray(self.attachment_points, dtype=float)
        if attachments.ndim != 1:
            raise ValueError("attachment_points must be one-dimensional")
        if not 1 <= attachments.size <= MAX_TRANCHES:
            raise ValueError(
                f"the number of tranches must be between 1 and {MAX_TRANCHES}"
            )
        if np.any(~np.isfinite(attachments)) or np.any(attachments < 0):
            raise ValueError("attachment points must be finite and nonnegative")
        if attachments[0] != 0 or np.any(np.diff(attachments) <= 0):
            raise ValueError(
                "attachment points must start at zero and increase strictly"
            )
        self.attachment_points = attachments

        if self.state_names is None:
            self.state_names = tuple(f"x{i + 1}" for i in range(state_count))
        elif len(self.state_names) != state_count:
            raise ValueError("state_names must contain one label per state")
        else:
            self.state_names = tuple(self.state_names)

        theory_count = theories.shape[0]
        if self.theory_names is None:
            self.theory_names = tuple(f"F{i + 1}" for i in range(theory_count))
        elif len(self.theory_names) != theory_count:
            raise ValueError("theory_names must contain one label per theory")
        else:
            self.theory_names = tuple(self.theory_names)

    @property
    def state_count(self) -> int:
        return self.dividends.size

    @property
    def tranche_count(self) -> int:
        return self.attachment_points.size

    @property
    def upper_bound(self) -> float:
        """Return the scalar M_T from the proof of Proposition 1."""

        highest_attachment = self.attachment_points[-1]
        return (self.dividends.max() + highest_attachment) / (
            self.gross_returns.min() - 1.0
        )


@dataclass(frozen=True)
class ExtremeEquilibria:
    q_min: Array
    q_max: Array
    iterations_min: int
    iterations_max: int
    residual_min: float
    residual_max: float

    @property
    def gap(self) -> Array:
        return self.q_max - self.q_min

    def multiplicity_detected(self, tolerance: float = 1e-8) -> bool:
        """Return True when the numerical extreme equilibria are distinct."""

        return bool(np.max(np.abs(self.gap)) > tolerance)


def tranche_payoffs(economy: WaterfallEconomy, q: Sequence[float]) -> Array:
    """Return one row of state-contingent payoffs for each tranche."""

    prices = _price_vector(economy, q)
    payoffs = np.empty((economy.tranche_count, economy.state_count), dtype=float)

    for index, lower in enumerate(economy.attachment_points):
        payoff = np.maximum(prices - lower, 0.0)
        if index + 1 < economy.tranche_count:
            upper = economy.attachment_points[index + 1]
            payoff -= np.maximum(prices - upper, 0.0)
        payoffs[index] = payoff

    return payoffs


def price_operator(economy: WaterfallEconomy, q: Sequence[float]) -> Array:
    """Evaluate the waterfall price-forming operator Psi_T at ``q``."""

    total_security_value = np.zeros(economy.state_count, dtype=float)
    for payoff in tranche_payoffs(economy, q):
        expected_payoffs = np.einsum("fxy,y->fx", economy.theories, payoff)
        total_security_value += expected_payoffs.max(axis=0)

    return (economy.dividends + total_security_value) / economy.gross_returns


def compute_extreme_equilibria(
    economy: WaterfallEconomy,
    *,
    absolute_tolerance: float = 1e-12,
    relative_tolerance: float = 1e-12,
    max_iterations: int = 1_000_000,
) -> ExtremeEquilibria:
    """Compute q_min and q_max by the monotone iterations in Proposition 1."""

    if absolute_tolerance <= 0 or relative_tolerance < 0:
        raise ValueError("tolerances must be positive")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")

    q_min, iterations_min, residual_min = _iterate(
        economy,
        np.zeros(economy.state_count),
        increasing=True,
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
        max_iterations=max_iterations,
    )
    q_max, iterations_max, residual_max = _iterate(
        economy,
        np.full(economy.state_count, economy.upper_bound),
        increasing=False,
        absolute_tolerance=absolute_tolerance,
        relative_tolerance=relative_tolerance,
        max_iterations=max_iterations,
    )

    ordering_tolerance = 10 * (
        absolute_tolerance
        + relative_tolerance * max(1.0, np.max(np.abs(q_max)))
    )
    if np.any(q_min > q_max + ordering_tolerance):
        raise RuntimeError("the computed lower bound exceeds the computed upper bound")

    return ExtremeEquilibria(
        q_min=q_min,
        q_max=q_max,
        iterations_min=iterations_min,
        iterations_max=iterations_max,
        residual_min=residual_min,
        residual_max=residual_max,
    )


def _iterate(
    economy: WaterfallEconomy,
    initial_value: Array,
    *,
    increasing: bool,
    absolute_tolerance: float,
    relative_tolerance: float,
    max_iterations: int,
) -> tuple[Array, int, float]:
    current = initial_value.astype(float, copy=True)

    for iteration in range(1, max_iterations + 1):
        updated = price_operator(economy, current)
        scale = max(1.0, float(np.max(np.abs(updated))))
        tolerance = absolute_tolerance + relative_tolerance * scale

        if increasing and np.any(updated < current - 10 * tolerance):
            raise RuntimeError("the lower iteration ceased to be nondecreasing")
        if not increasing and np.any(updated > current + 10 * tolerance):
            raise RuntimeError("the upper iteration ceased to be nonincreasing")

        step = float(np.max(np.abs(updated - current)))
        current = updated
        if step <= tolerance:
            residual = float(
                np.max(np.abs(price_operator(economy, current) - current))
            )
            if residual <= tolerance:
                return current, iteration, residual

    direction = "lower" if increasing else "upper"
    raise RuntimeError(
        f"the {direction} iteration did not converge after {max_iterations} iterations"
    )


def _price_vector(economy: WaterfallEconomy, q: Sequence[float]) -> Array:
    prices = np.asarray(q, dtype=float)
    if prices.shape != (economy.state_count,):
        raise ValueError("q must contain one price per state")
    if np.any(~np.isfinite(prices)) or np.any(prices < 0):
        raise ValueError("prices must be finite and nonnegative")
    return prices
