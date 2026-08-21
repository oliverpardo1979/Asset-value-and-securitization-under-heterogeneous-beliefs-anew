"""Regression tests for the computational companion."""

from __future__ import annotations

import unittest

import numpy as np

from computational_companion.paper_examples import (
    REVIEWER_INTERMEDIATE_EQUILIBRIUM,
    all_examples,
    motivating_two_tranche_multiplicity_example,
    reviewer_example,
)
from computational_companion.waterfall_equilibria import (
    WaterfallEconomy,
    compute_extreme_equilibria,
    price_operator,
    tranche_payoffs,
)


class WaterfallEquilibriumTests(unittest.TestCase):
    def test_all_reported_extreme_equilibria(self) -> None:
        for example in all_examples():
            with self.subTest(example=example.name):
                result = compute_extreme_equilibria(example.economy)
                np.testing.assert_allclose(
                    result.q_min, example.expected_q_min, atol=2e-9, rtol=0.0
                )
                np.testing.assert_allclose(
                    result.q_max, example.expected_q_max, atol=2e-9, rtol=0.0
                )
                self.assertLess(result.residual_min, 1e-10)
                self.assertLess(result.residual_max, 1e-10)

    def test_reviewer_example_detects_multiplicity(self) -> None:
        example = reviewer_example(with_tranching=True)
        result = compute_extreme_equilibria(example.economy)
        self.assertEqual(example.economy.tranche_count, 2)
        self.assertTrue(result.multiplicity_detected())
        self.assertTrue(np.all(result.q_min < result.q_max))

    def test_two_tranche_motivating_example_detects_multiplicity(self) -> None:
        example = motivating_two_tranche_multiplicity_example()
        result = compute_extreme_equilibria(example.economy)
        self.assertTrue(result.multiplicity_detected())
        self.assertTrue(np.all(result.q_min < result.q_max))

        junior_is_active_at_q_min = result.q_min > 51.0
        junior_is_active_at_q_max = result.q_max > 51.0
        np.testing.assert_array_equal(junior_is_active_at_q_min, (False, False, True))
        np.testing.assert_array_equal(junior_is_active_at_q_max, (False, True, True))

    def test_reported_intermediate_price_is_a_fixed_point(self) -> None:
        economy = reviewer_example(with_tranching=True).economy
        q_middle = REVIEWER_INTERMEDIATE_EQUILIBRIUM
        np.testing.assert_allclose(
            price_operator(economy, q_middle), q_middle, atol=2e-9, rtol=0.0
        )

        result = compute_extreme_equilibria(economy)
        self.assertTrue(np.all(result.q_min < q_middle))
        self.assertTrue(np.all(q_middle < result.q_max))

        np.testing.assert_array_equal(result.q_min > 17.0, (False, False, False))
        np.testing.assert_array_equal(q_middle > 17.0, (False, False, True))
        np.testing.assert_array_equal(result.q_max > 17.0, (False, True, True))

    def test_tranche_payoffs_are_budget_balanced(self) -> None:
        economy = reviewer_example(with_tranching=True).economy
        prices = np.array((13.0, 15.0, 18.0))
        np.testing.assert_allclose(
            tranche_payoffs(economy, prices).sum(axis=0), prices
        )

    def test_invalid_transition_matrix_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "sum to one"):
            WaterfallEconomy(
                dividends=(1.0, 2.0),
                gross_returns=2.0,
                theories=(((0.8, 0.3), (0.5, 0.5)),),
                attachment_points=(0.0,),
            )

    def test_more_than_three_states_or_tranches_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "number of states"):
            WaterfallEconomy(
                dividends=(1.0, 1.0, 1.0, 1.0),
                gross_returns=2.0,
                theories=(np.eye(4),),
                attachment_points=(0.0,),
            )

        with self.assertRaisesRegex(ValueError, "number of tranches"):
            WaterfallEconomy(
                dividends=(1.0, 1.0, 1.0),
                gross_returns=2.0,
                theories=(np.eye(3),),
                attachment_points=(0.0, 1.0, 2.0, 3.0),
            )


if __name__ == "__main__":
    unittest.main()
