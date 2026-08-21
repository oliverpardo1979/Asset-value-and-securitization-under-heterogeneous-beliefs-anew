"""Computational companion for the securitization paper."""

from .waterfall_equilibria import (
    ExtremeEquilibria,
    WaterfallEconomy,
    compute_extreme_equilibria,
    price_operator,
    tranche_payoffs,
)

__all__ = (
    "ExtremeEquilibria",
    "WaterfallEconomy",
    "compute_extreme_equilibria",
    "price_operator",
    "tranche_payoffs",
)
