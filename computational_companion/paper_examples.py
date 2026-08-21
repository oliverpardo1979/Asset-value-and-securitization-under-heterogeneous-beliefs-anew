"""Parameterizations reported in the paper."""

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


def reviewer_example(*, with_tranching: bool) -> PaperExample:
    """Return the non-uniqueness example in Section 3.5."""

    transition = np.array(
        (
            (11.0 / 20.0, 1.0 / 20.0, 2.0 / 5.0),
            (1.0 / 20.0, 9.0 / 10.0, 1.0 / 20.0),
            (2.0 / 5.0, 1.0 / 20.0, 11.0 / 20.0),
        )
    )
    coarse_theory = np.full((3, 3), 1.0 / 3.0)
    q_low = np.array((1070435.0, 1221275.0, 1282295.0)) / 75522.0
    q_high = np.array((30597995.0, 35089765.0, 36486825.0)) / 2040847.0

    return PaperExample(
        name=(
            "Reviewer example: three tranches"
            if with_tranching
            else "Reviewer example: no tranching"
        ),
        economy=WaterfallEconomy(
            dividends=(1.0 / 10.0, 2.0, 16.0 / 5.0),
            gross_returns=28.0 / 25.0,
            theories=(coarse_theory, transition),
            attachment_points=(0.0, 14.0, 17.0) if with_tranching else (0.0,),
            state_names=("l", "m", "h"),
            theory_names=("coarse", "singleton"),
        ),
        expected_q_min=q_low,
        expected_q_max=q_high if with_tranching else q_low,
    )


REVIEWER_INTERMEDIATE_EQUILIBRIUM = (
    np.array((4597760.0, 5256495.0, 5490670.0)) / 320834.0
)


def all_paper_examples() -> tuple[PaperExample, ...]:
    return (
        motivating_example(with_tranching=False),
        motivating_example(with_tranching=True),
        reviewer_example(with_tranching=False),
        reviewer_example(with_tranching=True),
    )
