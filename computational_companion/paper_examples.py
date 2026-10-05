"""Parameterizations used in the paper and the computational companion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from .waterfall_equilibria import WaterfallEconomy


Array = NDArray[np.float64]


@dataclass(frozen=True)
class PaperExample:
    name: str
    economy: WaterfallEconomy
    expected_q_min: Array
    expected_q_max: Array


def motivating_example(*, with_tranching: bool) -> PaperExample:
    """Return the limiting example in Sections 2.1 and 2.2 (epsilon = 0)."""

    coarse_theory = np.full((3, 3), 1.0 / 3.0)
    singleton_theory = np.eye(3)
    attachment_points = (0.0, 9.0 / 4.0) if with_tranching else (0.0,)
    expected = (
        np.array((21.0 / 20.0, 9.0 / 4.0, 3.0))
        if with_tranching
        else np.array((1.0, 2.0, 3.0))
    )

    return PaperExample(
        name=(
            "Motivating example: two tranches"
            if with_tranching
            else "Motivating example: no tranching"
        ),
        economy=WaterfallEconomy(
            dividends=(0.0, 2.0, 3.0),
            gross_returns=2.0,
            theories=(coarse_theory, singleton_theory),
            attachment_points=attachment_points,
            state_names=("l", "m", "h"),
            theory_names=("A", "B"),
        ),
        expected_q_min=expected,
        expected_q_max=expected,
    )


def motivating_two_tranche_multiplicity_example() -> PaperExample:
    """Return a two-tranche multiplicity case in the motivating family."""

    epsilon = 1.0 / 10.0
    coarse_theory = np.full((3, 3), 1.0 / 3.0)
    persistent_theory = np.full((3, 3), epsilon / 2.0)
    np.fill_diagonal(persistent_theory, 1.0 - epsilon)

    return PaperExample(
        name="Motivating family: two-tranche multiplicity",
        economy=WaterfallEconomy(
            dividends=(0.0, 2.0, 3.0),
            gross_returns=21.0 / 20.0,
            theories=(coarse_theory, persistent_theory),
            attachment_points=(0.0, 51.0),
            state_names=("l", "m", "h"),
            theory_names=("A", "B"),
        ),
        expected_q_min=np.array((28400.0 / 609.0, 29560.0 / 609.0, 1500.0 / 29.0)),
        expected_q_max=np.array(
            (154560.0 / 3187.0, 162783.0 / 3187.0, 169521.0 / 3187.0)
        ),
    )


def multiplicity_example(*, with_tranching: bool) -> PaperExample:
    """Return the economy in Example 1 of the paper, with or without tranching."""

    transition = np.array(
        (
            (4.0 / 8.0, 1.0 / 8.0, 3.0 / 8.0),
            (1.0 / 8.0, 6.0 / 8.0, 1.0 / 8.0),
            (3.0 / 8.0, 1.0 / 8.0, 4.0 / 8.0),
        )
    )
    coarse_theory = np.full((3, 3), 1.0 / 3.0)
    q_low = np.array((848.0, 930.0, 978.0)) / 327.0
    q_high = np.array((2201.0, 2425.0, 2523.0)) / 803.0

    return PaperExample(
        name=(
            "Example 1: two-tranche debt-equity structure"
            if with_tranching
            else "Example 1: no tranching"
        ),
        economy=WaterfallEconomy(
            dividends=(0.0, 3.0 / 12.0, 5.0 / 12.0),
            gross_returns=13.0 / 12.0,
            theories=(coarse_theory, transition),
            attachment_points=(0.0, 3.0) if with_tranching else (0.0,),
            state_names=("l", "m", "h"),
            theory_names=("coarse", "singleton"),
        ),
        expected_q_min=q_low,
        expected_q_max=q_high if with_tranching else q_low,
    )


MULTIPLICITY_INTERMEDIATE_EQUILIBRIUM = (
    np.array((259.0, 285.0, 297.0)) / 97.0
)


REALIZED_PAYOFF_OBJECTIVE_TRANSITION = np.array(
    (
        (1.0 / 2.0, 1.0 / 4.0, 1.0 / 4.0),
        (1.0 / 4.0, 1.0 / 2.0, 1.0 / 4.0),
        (1.0 / 4.0, 1.0 / 4.0, 1.0 / 2.0),
    )
)
REALIZED_PAYOFF_STATIONARY_DISTRIBUTION = np.full(3, 1.0 / 3.0)
REALIZED_PAYOFF_PRIORITY = (0, 1, 2)
REALIZED_PAYOFF_EXPECTED_DELTAS = {
    False: np.array((0.0, -373.0 / 4464.0, 0.0)),
    True: np.array((0.0, -1.0 / 16.0, -1.0 / 36.0)),
}


def realized_payoff_example(*, with_tranching: bool) -> PaperExample:
    """Return the full-support realized-payoff example in Appendix 6.5."""

    theory_a = np.array(
        (
            (1.0 / 2.0, 1.0 / 4.0, 1.0 / 4.0),
            (1.0 / 4.0, 3.0 / 8.0, 3.0 / 8.0),
            (1.0 / 4.0, 3.0 / 8.0, 3.0 / 8.0),
        )
    )
    theory_b = np.array(
        (
            (3.0 / 8.0, 1.0 / 4.0, 3.0 / 8.0),
            (1.0 / 4.0, 1.0 / 2.0, 1.0 / 4.0),
            (3.0 / 8.0, 1.0 / 4.0, 3.0 / 8.0),
        )
    )
    theory_c = np.full((3, 3), 1.0 / 3.0)
    expected = (
        np.array((2.0, 5.0 / 2.0, 4.0))
        if with_tranching
        else np.array((4451.0 / 2232.0, 5579.0 / 2232.0, 8927.0 / 2232.0))
    )

    return PaperExample(
        name=(
            "Realized-payoff example: three tranches"
            if with_tranching
            else "Realized-payoff example: no tranching"
        ),
        economy=WaterfallEconomy(
            dividends=(245.0 / 48.0, 113.0 / 16.0, 209.0 / 16.0),
            gross_returns=4.0,
            theories=(theory_a, theory_b, theory_c),
            attachment_points=(0.0, 2.0, 5.0 / 2.0) if with_tranching else (0.0,),
            state_names=("l", "m", "h"),
            theory_names=("A", "B", "C"),
        ),
        expected_q_min=expected,
        expected_q_max=expected,
    )


def all_examples() -> tuple[PaperExample, ...]:
    return (
        motivating_example(with_tranching=False),
        motivating_example(with_tranching=True),
        motivating_two_tranche_multiplicity_example(),
        multiplicity_example(with_tranching=False),
        multiplicity_example(with_tranching=True),
        realized_payoff_example(with_tranching=False),
        realized_payoff_example(with_tranching=True),
    )
