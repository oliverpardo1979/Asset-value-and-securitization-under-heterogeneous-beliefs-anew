"""Generate the complete HTML reader from unchanged main.tex and its AUX.

Usage: python scripts/build_web_manuscript.py --build-dir tmp/web-latex
The publication PDF is copied byte-for-byte, never silently recompiled here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from tex_to_web import (
    ROOT, ConversionError, Pandoc, EquationNumbering, group, environment_end,
    strip_comments, read_aux, find_pandoc, extract_figures, clean_layout,
    prepare_theorems, prepare_citations, transform_ast, compiled_headings,
    read_bibliography,
)
from bs4 import BeautifulSoup


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_tokens(value):
    if isinstance(value, list):
        return [word for child in value for word in text_tokens(child)]
    if not isinstance(value, dict):
        return []
    kind, content = value.get('t'), value.get('c')
    if kind in ('Math', 'Image'):
        return []
    if kind == 'Str':
        return re.findall(r'\w+', content)
    if kind in ('Code', 'CodeBlock'):
        return re.findall(r'\w+', content[1])
    return text_tokens(content)


def normalize_eqnarray(match):
    # eqnarray's three columns become an AMS aligned pair. Preserve every row.
    kind, body = match.group(1), match.group(2)
    body = re.sub(r'&([^&\n]*?)&', r'&\1', body)
    return r'\begin{align' + kind + '}\n' + body + r'\end{align' + kind + '}'


def build(build_dir, pdf):
    source_path = ROOT / 'main.tex'
    source_commit = subprocess.check_output(['git', 'log', '-1', '--format=%H', '--', 'main.tex'], cwd=ROOT, text=True).strip()
    committed = subprocess.check_output(['git', 'show', source_commit + ':main.tex'], cwd=ROOT).decode('utf-8')
    assert committed.replace('\r\n', '\n') == source_path.read_text(encoding='utf-8'), 'Commit approved manuscript changes before building a public edition'
    assert (build_dir / 'main.aux').stat().st_mtime >= source_path.stat().st_mtime, 'Recompile current source to refresh AUX'
    # A fresh compilation must agree with the approved PDF except for \today.
    import pymupdf
    def pdf_text(path):
        with pymupdf.open(path) as doc:
            value = '\n'.join(page.get_text() for page in doc)
        value = re.sub(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', '<DATE>', value)
        return ' '.join(value.split())
    assert pdf_text(pdf) == pdf_text(build_dir / 'main.pdf'), 'Approved PDF and current compiled manuscript differ'
    source = strip_comments(source_path.read_text(encoding='utf-8'))
    if r'\begin{comment}' in source:
        source = re.sub(r'\\begin\{comment\}[\s\S]*?\\end\{comment\}', '', source)
    labels, citations = read_aux(build_dir / 'main.aux')
    active_labels = re.findall(r'\\label\{([^}]+)\}', source)
    assert len(active_labels) == len(set(active_labels)), 'Duplicate LaTeX labels'
    pandoc = Pandoc(find_pandoc(), ROOT)
    title, _ = group(source, re.search(r'\\title\s*', source).end())
    author, _ = group(source, re.search(r'\\author\s*', source).end())
    # Keep acknowledgments separate so body footnote numbering stays unchanged.
    thanks_start = author.index(r'\thanks')
    acknowledgments, _ = group(author, thanks_start + len(r'\thanks'))
    author = author[:thanks_start]
    body = source.split(r'\begin{document}', 1)[1].split(r'\end{document}', 1)[0]
    abstract_start = re.search(r'\\begin\{abstract\}', body)
    abstract, abstract_end = environment_end(body, abstract_start.start(), 'abstract')
    body = body[:abstract_start.start()] + body[abstract_end:]
    body = body[:body.index(r'\begin{thebibliography}')]
    body, figures = extract_figures(body, ROOT, pdf, ROOT / 'docs/generated/assets', labels, 'generated/assets')
    body = re.sub(r'\\begin\{eqnarray(\*?)\}([\s\S]*?)\\end\{eqnarray\*?\}', normalize_eqnarray, body)
    numbering = EquationNumbering(labels)
    body = numbering.apply(body)
    for short, full in {'thm': 'theorem', 'lmm': 'lemma', 'prp': 'proposition', 'dfn': 'definition', 'crl': 'corollary'}.items():
        body = body.replace('{' + short + '}', '{' + full + '}')
    body = prepare_theorems(clean_layout(body), labels)
    body = ('\\section*{' + title + '}\n' + author + '\n\n'
            + '\\section*{Abstract}\n' + abstract + '\n\n' + body)
    body, cited = prepare_citations(body, citations)
    expected_displays = len(re.findall(r'\\begin\{(?:equation|align|gather)\*?\}|\\\[', body))
    ast = pandoc.ast(body)
    tables = [re.findall(r'\\label\{([^}]+)\}', m.group())[0]
              for m in re.finditer(r'\\begin\{table\}[\s\S]*?\\end\{table\}', body)]
    sections = transform_ast(ast, labels, tables, compiled_headings(build_dir / 'main.aux', pandoc))
    fragment = pandoc.run(json.dumps(ast, ensure_ascii=False), 'json', 'html5', '--mathjax', '--wrap=none')
    bibliography = read_bibliography(source_path)
    bibkeys = {key for key, _ in bibliography}
    assert cited <= bibkeys, 'Missing bibliography entries'
    bib_html = []
    for key, entry in bibliography:
        entry = re.sub(r'\\penalty\s*-?\d+\s*', '', entry)
        entry = re.sub(r'\\natexlab\{([^}]+)\}', r'\1', entry)
        entry = re.sub(r'\\doi\{([^}]+)\}', r'\\href{https://doi.org/\1}{doi: \1}', entry)
        bib_html.append('<div class="csl-entry" id="ref-' + key + '">' + pandoc.fragment(entry) + '</div>')
    result = fragment + '<section id="references"><h1>References</h1>' + '\n'.join(bib_html) + '</section>'
    soup = BeautifulSoup(result, 'html.parser')
    ids = [node['id'] for node in soup.select('[id]')]
    assert len(ids) == len(set(ids)), 'Duplicate HTML IDs'
    assert set(active_labels) <= set(ids), f'Lost labels: {set(active_labels) - set(ids)}'
    broken = {a['href'] for a in soup.select('a[href^="#"]') if a['href'][1:] not in ids}
    assert not broken, f'Broken links: {broken}'
    assert len(soup.select('figure')) == len(figures), 'Lost figures'
    assert len(soup.select('.math.display')) == expected_displays, 'Lost display math'
    rendered = BeautifulSoup(fragment, 'html.parser')
    for math in rendered.select('.math'):
        math.decompose()
    missing = Counter(text_tokens(ast['blocks'])) - Counter(re.findall(r'\w+', rendered.get_text(' ')))
    assert not missing, f'Lost visible text: {missing}'
    assert not pandoc.warnings, f'Pandoc warnings: {pandoc.warnings}'
    author_paragraph = soup.find('p')
    assert author_paragraph.get_text(strip=True) == author, 'Author location changed'
    acknowledgment_html = pandoc.fragment(acknowledgments)
    acknowledgment_block = BeautifulSoup('<details class="author-note"><summary>Author affiliation and acknowledgments</summary>' + acknowledgment_html + '</details>', 'html.parser')
    author_paragraph.insert_after(acknowledgment_block)
    result = '\n'.join(line.rstrip() for line in str(soup).splitlines()) + '\n'
    abstract_source, _ = prepare_citations(abstract, citations)
    meta = {
        'title': title, 'author': 'Oliver Pardo', 'source': 'main.tex',
        'source_commit': source_commit,
        'source_sha256': hashlib.sha256(source_path.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
        'source_hash_line_endings': 'LF', 'pdf_sha256': digest(pdf),
        'abstract_html': pandoc.fragment(abstract_source),
        'sections': sections + [{'id': 'references', 'title': 'References', 'level': 1, 'number': ''}],
        'figures': figures,
        'counts': {'labels': len(active_labels), 'numbered_equations': numbering.numbered_rows,
                   'display_math': expected_displays, 'figures': len(figures),
                   'tables': len(tables), 'references': len(bibliography)},
        'checks': {'all_labels_present': True, 'all_links_resolved': True,
                   'compiled_numbering_checked': True, 'text_inventory_checked': True,
                   'math_inventory_checked': True, 'pandoc_warnings': []},
    }
    out = ROOT / 'docs/generated'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'manuscript.html').write_text(result, encoding='utf-8')
    (out / 'manuscript-meta.json').write_text(json.dumps(meta, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (ROOT / 'docs/paper').mkdir(exist_ok=True)
    shutil.copyfile(pdf, ROOT / 'docs/paper/asset-value-and-securitization.pdf')
    print(json.dumps(meta['counts'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'tmp/web-latex')
    parser.add_argument('--pdf', type=Path, default=ROOT / 'output/pdf/updated/main.pdf')
    args = parser.parse_args()
    build(args.build_dir, args.pdf)
