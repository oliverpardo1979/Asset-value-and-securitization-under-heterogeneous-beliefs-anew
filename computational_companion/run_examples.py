"""Run the parameterizations included in the computational companion."""

from __future__ import annotations

import numpy as np

from .paper_examples import all_examples
from .waterfall_equilibria import compute_extreme_equilibria


def main() -> None:
    np.set_printoptions(precision=9, suppress=True)

    for example in all_examples():
        result = compute_extreme_equilibria(example.economy)
        print(example.name)
        print(f"  q_min = {result.q_min}")
        print(f"  q_max = {result.q_max}")
        print(f"  max gap = {np.max(result.gap):.9g}")
        print(f"  multiplicity detected = {result.multiplicity_detected()}")
        print(
            "  residuals = "
            f"({result.residual_min:.3e}, {result.residual_max:.3e})"
        )
        print(
            "  iterations = "
            f"({result.iterations_min}, {result.iterations_max})"
        )
        print()


if __name__ == "__main__":
    main()
