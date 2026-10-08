"""Checks on the committed publication snapshot, without network or a browser."""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tmp/web-build-deps'))
sys.path.insert(0, str(ROOT / 'scripts'))
from bs4 import BeautifulSoup
from tex_to_web import strip_comments


class WebEditionTests(unittest.TestCase):
    def setUp(self):
        self.meta = json.loads((ROOT / 'docs/generated/manuscript-meta.json').read_text(encoding='utf-8'))
        self.paper = BeautifulSoup((ROOT / 'docs/generated/manuscript.html').read_text(encoding='utf-8'), 'html.parser')
        self.home = BeautifulSoup((ROOT / 'docs/index.html').read_text(encoding='utf-8'), 'html.parser')

    def test_manuscript_and_pdf_hashes(self):
        for path, key in [('main.tex','source_sha256'), ('docs/paper/asset-value-and-securitization.pdf','pdf_sha256')]:
            content = (ROOT / path).read_text(encoding='utf-8').encode('utf-8') if path.endswith('.tex') else (ROOT / path).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), self.meta[key])

    def test_labels_links_and_assets(self):
        source = strip_comments((ROOT / 'main.tex').read_text(encoding='utf-8'))
        labels = set(re.findall(r'\\label\{([^}]+)\}', source))
        ids = [n['id'] for n in self.paper.select('[id]')]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(labels <= set(ids))
        available = set(ids) | {n['id'] for n in self.home.select('[id]')}
        for page in [self.paper, self.home]:
            for link in page.select('a[href^="#"]'):
                self.assertIn(link['href'][1:], available)
            for el in page.select('img[src], script[src], link[href]'):
                path = el.get('src', el.get('href',''))
                if not path.startswith(('https:', '#')):
                    self.assertTrue((ROOT / 'docs' / path).is_file(), path)

    def test_complete_content(self):
        self.assertEqual(len(self.paper.select('figure')), 5)
        self.assertEqual(len(self.paper.select('table')), 3)
        self.assertEqual(len(self.paper.select('.csl-entry')), 30)
        self.assertEqual(len(self.paper.select('.proof')), 16)
        self.assertEqual(len(self.paper.select('.math.display')), 149)
        self.assertIn('review proofs, check notation', self.paper.get_text())
        self.assertIn('anonymous referees', self.paper.get_text())
        self.assertIn('historical account of security innovation', self.paper.select_one('#fn1').get_text())
        self.assertNotIn('Loading', self.paper.get_text())

    def test_known_example_and_data_provenance(self):
        data = json.loads((ROOT / 'docs/generated/examples.json').read_text())
        self.assertEqual(len(data['cases']), 7)
        self.assertEqual(len(data['example1_equilibria']), 3)
        for path, sha in data['sources'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_text(encoding='utf-8').encode('utf-8')).hexdigest(), sha)
        for i, e in enumerate(data['example1_equilibria']):
            self.assertLess(e['residual'], 1e-12)
            self.assertEqual(sum(v > 0 for v in e['payoffs'][1]), i)

    def test_publication_contains_no_editorial_material(self):
        for path in (ROOT / 'docs').rglob('*'):
            if path.is_file():
                self.assertNotIn('response_letter', path.name)
                self.assertNotIn('JME-D', path.name)


if __name__ == '__main__':
    unittest.main()
