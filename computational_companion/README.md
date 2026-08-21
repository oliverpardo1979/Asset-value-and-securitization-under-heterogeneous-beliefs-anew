# Computational companion

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/oliverpardo1979/Asset-value-and-securitization-under-heterogeneous-beliefs-anew/blob/main/computational_companion/Waterfall_Equilibria.ipynb)

This directory contains a minimal Python implementation of the price-forming
operator in *Asset Value and Securitization under Heterogeneous Beliefs*.

The code deliberately has a narrow scope:

- at most three states;
- at most three waterfall tranches;
- any finite number of subjective theories; and
- computation of the least and greatest equilibrium prices only.

It does not search for all intermediate equilibria. If the computed least and
greatest prices differ, multiplicity is established. If they coincide up to the
chosen numerical tolerance, the calculation provides numerical evidence of
uniqueness.

## Method

For a price vector `q`, the code evaluates

```text
Psi_T(q)(x) = [d(x) + sum_tau max_F E_F(phi_tau(q) | x)] / R(x).
```

The least equilibrium is obtained by iterating `Psi_T` from the zero vector.
The greatest equilibrium is obtained by iterating it from `M_T * 1`, where

```text
M_T = [max_x d(x) + a_T] / [min_x R(x) - 1]
```

and `a_T` is the attachment point of the unbounded tranche. These are the two
monotone iterations used in the proof of Proposition 1.

Attachment points are supplied as a strictly increasing list beginning at
zero. For example, `(0, 14, 17)` represents the tranching
`[0, 14)`, `[14, 17)`, and `[17, infinity)`.

## Installation and use

From the repository root, install the only dependency:

```bash
python -m pip install -r computational_companion/requirements.txt
```

Run every parameterization included in the companion:

```bash
python -m computational_companion.run_examples
```

Run the regression tests:

```bash
python -m unittest computational_companion.test_waterfall_equilibria
```

To evaluate another parameterization, construct a `WaterfallEconomy` and call
the solver:

```python
import numpy as np

from computational_companion import WaterfallEconomy, compute_extreme_equilibria

economy = WaterfallEconomy(
    dividends=(0, 2, 3),
    gross_returns=2,
    theories=(np.full((3, 3), 1 / 3), np.eye(3)),
    attachment_points=(0, 9 / 4),
    state_names=("l", "m", "h"),
)

result = compute_extreme_equilibria(economy)
print(result.q_min)
print(result.q_max)
```

## Included examples

`paper_examples.py` contains five cases:

1. the motivating example without tranching;
2. the motivating example with two tranches;
3. an additional parameterization of the motivating economy in which two
   tranches generate multiplicity;
4. the reviewer's parameterization without tranching; and
5. the reviewer's parameterization with a two-tranche debt--equity structure.

The last case reproduces the least and greatest of the three equilibrium price
vectors reported in the paper. The tests also verify directly that the reported
intermediate vector is a fixed point, although the solver does not search for
or return it.

The expected numerical results are:

| Case | `q_min` | `q_max` | Multiplicity |
| --- | --- | --- | --- |
| Motivating, no tranching | `(1, 2, 3)` | `(1, 2, 3)` | No |
| Motivating, two tranches | `(1.05, 2.25, 3)` | `(1.05, 2.25, 3)` | No |
| Motivating family, two-tranche multiplicity | `(46.634, 48.539, 51.724)` | `(48.497, 51.077, 53.191)` | Yes |
| Reviewer, no tranching | `(14.174, 16.171, 16.979)` | Same | No |
| Reviewer, two-tranche debt--equity structure | `(14.174, 16.171, 16.979)` | `(14.993, 17.194, 17.878)` | Yes |

The motivating example uses `epsilon = 0`, as do the limiting calculations in
the text. The input validator therefore permits zero transition probabilities,
even though the general model assumes strictly positive transition matrices.

## Numerical interpretation

The results are floating-point approximations. Each run reports the fixed-point
residuals and the number of iterations. Multiplicity should be reported only
when the gap between the computed extreme equilibria is materially larger than
the numerical tolerance.
