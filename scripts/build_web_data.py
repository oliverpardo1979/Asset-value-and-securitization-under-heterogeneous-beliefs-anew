"""Export verified examples and iteration histories from the existing companion.

No browser-side solver and no search for all equilibria. Every saved step uses
the companion's price_operator. The known middle fixed point is checked separately.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from computational_companion.paper_examples import all_examples, MULTIPLICITY_INTERMEDIATE_EQUILIBRIUM
from computational_companion.waterfall_equilibria import compute_extreme_equilibria, price_operator, tranche_payoffs


def sha(path):
    return hashlib.sha256(path.read_text(encoding='utf-8').encode('utf-8')).hexdigest()


def trace(e, initial, count):
    values = [np.asarray(initial)]
    for _ in range(count):
        values.append(price_operator(e, values[-1]))
    return np.asarray(values)


def build():
    cases = []
    ids = ['motivating-benchmark', 'motivating-tranches', 'motivating-multiplicity',
           'example1-benchmark', 'example1-tranches', 'payoffs-benchmark', 'payoffs-tranches']
    for id_, example in zip(ids, all_examples()):
        e = example.economy
        result = compute_extreme_equilibria(e)
        np.testing.assert_allclose(result.q_min, example.expected_q_min, atol=2e-8, rtol=0)
        np.testing.assert_allclose(result.q_max, example.expected_q_max, atol=2e-8, rtol=0)
        lower = trace(e, np.zeros(e.state_count), result.iterations_min)
        upper = trace(e, np.full(e.state_count, e.upper_bound), result.iterations_max)
        assert np.all(np.diff(lower, axis=0) >= -1e-12)
        assert np.all(np.diff(upper, axis=0) <= 1e-12)
        np.testing.assert_allclose(lower[-1], result.q_min, atol=1e-13, rtol=0)
        np.testing.assert_allclose(upper[-1], result.q_max, atol=1e-13, rtol=0)
        cases.append({
            'id': id_, 'name': example.name,
            'dividends': e.dividends.tolist(), 'returns': e.gross_returns.tolist(),
            'theories': e.theories.tolist(), 'theory_names': list(e.theory_names),
            'states': list(e.state_names), 'attachments': e.attachment_points.tolist(),
            'upper_bound': e.upper_bound, 'q_min': result.q_min.tolist(), 'q_max': result.q_max.tolist(),
            'residual_min': result.residual_min, 'residual_max': result.residual_max,
            'iterations_min': result.iterations_min, 'iterations_max': result.iterations_max,
            'lower_path': lower.tolist(), 'upper_path': upper.tolist(),
            'full_support': bool(np.all(e.theories > 0)),
        })
    e = all_examples()[4].economy
    known = [all_examples()[4].expected_q_min, MULTIPLICITY_INTERMEDIATE_EQUILIBRIUM,
             all_examples()[4].expected_q_max]
    equilibria = []
    for q in known:
        residual = float(np.max(np.abs(price_operator(e, q) - q)))
        assert residual < 1e-12
        payoffs = tranche_payoffs(e, q)
        # [tranche, theory, current state], discounted values.
        values = np.einsum('fxy,ty->tfx', e.theories, payoffs) / e.gross_returns
        np.testing.assert_allclose(payoffs.sum(axis=0), q, atol=1e-14)
        np.testing.assert_allclose(e.dividends / e.gross_returns + values.max(axis=1).sum(axis=0), q, atol=1e-13)
        equilibria.append({'q': q.tolist(), 'payoffs': payoffs.tolist(),
                           'valuations': values.tolist(), 'residual': residual})
    # Motivating example at current state m. Separately priced senior and junior claims.
    e_m = all_examples()[1].economy
    q_m = all_examples()[1].expected_q_min
    payoff_m = tranche_payoffs(e_m, q_m)
    valuation_m = np.einsum('fxy,ty->tfx', e_m.theories, payoff_m) / e_m.gross_returns
    output = {
        'scope': 'Stored examples. Only extreme equilibria are computed. Known intermediate fixed point verified separately.',
        'tolerances': {'absolute': 1e-12, 'relative': 1e-12},
        'source_commit': '569840397ac65ab5e8bede250cf86e1ae1d45b8a',
        'sources': {p: sha(ROOT / p) for p in ['computational_companion/paper_examples.py',
                    'computational_companion/waterfall_equilibria.py']},
        'cases': cases, 'example1_equilibria': equilibria,
        'motivating': {'payoffs': payoff_m.tolist(), 'valuations': valuation_m.tolist()},
    }
    out = ROOT / 'docs/generated/examples.json'
    out.parent.mkdir(exist_ok=True, parents=True)
    encoded = json.dumps(output, indent=2, allow_nan=False) + '\n'
    if '--check' in sys.argv:
        def compare(saved, current):
            # Allow last-bit BLAS/platform differences, not changed inputs or code.
            if isinstance(current, dict):
                assert saved.keys() == current.keys()
                for key in current:
                    compare(saved[key], current[key])
            elif isinstance(current, list):
                assert len(saved) == len(current)
                for a, b in zip(saved, current):
                    compare(a, b)
            elif isinstance(current, float):
                np.testing.assert_allclose(saved, current, atol=1e-12, rtol=1e-12)
            else:
                assert saved == current, 'Stored web results are stale'
        compare(json.loads(out.read_text(encoding='utf-8')), output)
    else:
        out.write_text(encoded, encoding='utf-8')
    print(f'Validated {len(cases)} cases, all iteration paths, and 3 known fixed points.')


if __name__ == '__main__':
    build()
