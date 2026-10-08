"""LaTeX conversion helpers adapted from Oliver Pardo's ai-growth-and-labor digital edition.

Retains compiled numbering and fails on unsupported content. No manuscript edits.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
# Optional, gitignored installation for the desktop's isolated Python runtime.
if (ROOT / "tmp/web-build-deps").is_dir():
    sys.path.insert(0, str(ROOT / "tmp/web-build-deps"))


class ConversionError(RuntimeError):
    """A construct or discrepancy that must not be silently omitted."""


def group(text: str, pos: int, opening: str = "{", closing: str = "}") -> tuple[str, int]:
    """Read a balanced TeX group, including nested groups and escaped braces."""
    while pos < len(text) and text[pos].isspace():
        pos += 1
    if pos >= len(text) or text[pos] != opening:
        raise ConversionError(f"Expected {opening!r} near {text[pos:pos + 70]!r}")
    start, depth = pos + 1, 1
    pos += 1
    while pos < len(text):
        if text[pos] == "\\":
            # An escaped delimiter is not a group delimiter; control words
            # can be skipped character by character without changing depth.
            if pos + 1 < len(text) and text[pos + 1] in "{}[]%\\":
                pos += 2
                continue
        if text[pos] == opening:
            depth += 1
        elif text[pos] == closing:
            depth -= 1
            if not depth:
                return text[start:pos], pos + 1
        pos += 1
    raise ConversionError("Unterminated TeX group")


def groups(text: str) -> list[str]:
    result, pos = [], 0
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
        else:
            item, pos = group(text, pos)
            result.append(item)
    return result


def strip_comments(text: str) -> str:
    """Honor TeX's escaped percent signs and literal verbatim environments."""
    result, literal = [], False
    for line in text.splitlines(keepends=True):
        if r"\begin{verbatim}" in line:
            literal = True
        if literal:
            result.append(line)
            if r"\end{verbatim}" in line:
                literal = False
            continue
        if not line.strip():
            # A physically empty TeX line inserts a paragraph break even
            # when the preceding comment suppressed that line's end token.
            result.append("\n\n")
            continue
        cut = None
        for i, ch in enumerate(line):
            if ch == "%":
                backslashes, j = 0, i - 1
                while j >= 0 and line[j] == "\\":
                    backslashes += 1
                    j -= 1
                if backslashes % 2 == 0:
                    cut = i
                    break
        # A TeX comment suppresses its line ending too, not the next line.
        result.append(line if cut is None else line[:cut])
    if literal:
        raise ConversionError("Unterminated verbatim environment")
    return "".join(result)


def flatten(path: Path, root: Path, seen: list[Path], stack: tuple[Path, ...] = ()) -> str:
    path = path.resolve()
    if path in stack:
        raise ConversionError(f"Cyclic input: {path}")
    if not path.is_relative_to(root.resolve()):
        raise ConversionError(f"Input escapes manuscript directory: {path}")
    seen.append(path)
    source = strip_comments(path.read_text(encoding="utf-8"))

    def replace(match: re.Match[str]) -> str:
        target = root / match.group(1)
        if not target.suffix:
            target = target.with_suffix(".tex")
        if not target.is_file():
            raise ConversionError(f"Missing active input: {target}")
        return "\n" + flatten(target, root, seen, stack + (path,)) + "\n"

    return re.sub(r"\\(?:input|include)\s*\{([^}]+)\}", replace, source)


def read_aux(path: Path, require_citations: bool = True) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]]]:
    labels, citations = {}, {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(r"\newlabel{"):
            key, pos = group(line, len(r"\newlabel"))
            value, _ = group(line, pos)
            fields = groups(value)
            if key in labels:
                raise ConversionError(f"Duplicate compiled label: {key}")
            labels[key] = {"number": fields[0].strip("{}"), "page": fields[1],
                           "title": fields[2], "destination": fields[3]}
        elif line.startswith(r"\bibcite{"):
            key, pos = group(line, len(r"\bibcite"))
            value, _ = group(line, pos)
            fields = groups(value)
            citations[key] = {"year": fields[1], "author": fields[2].strip("{}")}
    if not labels or (require_citations and not citations):
        raise ConversionError("Compiled AUX is missing labels or bibliography metadata")
    return labels, citations


def find_pandoc(explicit: str | None = None) -> str:
    candidates = [explicit, os.environ.get("PANDOC"), shutil.which("pandoc")]
    candidates.extend(str(path) for path in (ROOT / "tmp").glob("**/pandoc.exe"))
    try:
        import pypandoc
        candidates.append(pypandoc.get_pandoc_path())
    except (ImportError, OSError, AttributeError):
        pass
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise ConversionError("Pandoc not found; install Pandoc 3 or pypandoc_binary, or pass --pandoc")


class Pandoc:
    def __init__(self, executable: str, root: Path):
        self.executable, self.root = executable, root
        self.warnings: list[str] = []

    def run(self, text: str, source: str, target: str, *args: str) -> str:
        proc = subprocess.run([self.executable, "-f", source, "-t", target, *args],
                              input=text, capture_output=True, encoding="utf-8", cwd=self.root)
        if proc.returncode:
            raise ConversionError(f"Pandoc failed: {proc.stderr}")
        if proc.stderr.strip():
            self.warnings.append(proc.stderr.strip())
        return proc.stdout

    def ast(self, text: str) -> dict[str, Any]:
        return json.loads(self.run(text, "latex+raw_tex", "json"))

    def fragment(self, text: str) -> str:
        return self.run(text, "latex", "html5", "--mathjax", "--wrap=none").strip()

    def plain(self, text: str) -> str:
        return self.run(text, "latex", "plain", "--wrap=none").strip()


def command_rewrite(source: str, command: str, callback: Any) -> str:
    pattern = re.compile(r"\\" + re.escape(command) + r"(?![A-Za-z])")
    result, pos = [], 0
    for match in pattern.finditer(source):
        if match.start() < pos:
            continue
        value, end = group(source, match.end())
        result.append(source[pos:match.start()])
        result.append(callback(value))
        pos = end
    result.append(source[pos:])
    return "".join(result)


def environment_end(source: str, start: int, name: str) -> tuple[str, int]:
    opening = re.match(r"\\begin\{" + re.escape(name) + r"\}", source[start:])
    if not opening:
        raise ConversionError(f"Missing opening environment {name}")
    body_start, depth = start + opening.end(), 1
    pattern = re.compile(r"\\(begin|end)\{" + re.escape(name) + r"\}")
    for token in pattern.finditer(source, body_start):
        depth += 1 if token.group(1) == "begin" else -1
        if not depth:
            return source[body_start:token.start()], token.end()
    raise ConversionError(f"Unclosed environment: {name}")


def split_math_rows(source: str) -> list[str]:
    """Split top-level AMS rows without splitting matrices or grouped math."""
    result, start, pos, depth, environments = [], 0, 0, 0, []
    while pos < len(source):
        token = re.match(r"\\(begin|end)\{([^}]+)\}", source[pos:])
        if token:
            if token.group(1) == "begin":
                environments.append(token.group(2))
            elif environments:
                environments.pop()
            pos += token.end()
            continue
        if source.startswith("\\\\", pos) and depth == 0 and not environments:
            result.append(source[start:pos])
            pos += 2
            # Optional inter-row spacing has no semantic content.
            if pos < len(source) and source[pos] == "[":
                _, pos = group(source, pos, "[", "]")
            start = pos
            continue
        if source[pos] == "\\" and pos + 1 < len(source) and source[pos + 1] in "{}":
            pos += 2
            continue
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
        pos += 1
    result.append(source[start:])
    return result


class EquationNumbering:
    def __init__(self, labels: dict[str, dict[str, str]], section_prefix: str | None = None):
        self.labels, self.counter, self.numbered_rows = labels, 0, 0
        self.checked_labels: set[str] = set()
        self.section_prefix = section_prefix
        self.appendix_section: int | None = 0 if section_prefix is not None else None
        self.within_section = section_prefix is not None
        self.section_separator = "."

    def validate(self, source: str, number: str) -> None:
        for label in re.findall(r"\\label\{([^}]+)\}", source):
            if label not in self.labels or self.labels[label]["number"] != number:
                actual = self.labels.get(label, {}).get("number", "MISSING")
                raise ConversionError(f"Equation numbering mismatch for {label}: source {number}, AUX {actual}")
            self.checked_labels.add(label)

    def next_number(self) -> str:
        self.counter += 1
        if not self.within_section:
            return str(self.counter)
        if self.section_prefix is not None:
            if not self.appendix_section:
                raise ConversionError("Section-numbered equations require a preceding section")
            return self.section_prefix + str(self.appendix_section) + self.section_separator + str(self.counter)
        if self.appendix_section is None or not 1 <= self.appendix_section <= 26:
            raise ConversionError("Section-numbered equations require appendix sections A through Z")
        return chr(64 + self.appendix_section) + self.section_separator + str(self.counter)

    def apply(self, source: str, sub: dict[str, Any] | None = None) -> str:
        # Read numbering controls before layout cleanup. Derive each number
        # from source order, then check the AUX; never infer counters from it.
        pattern = re.compile(
            r"\\begin\{(?P<environment>subequations|equation\*?|align\*?|gather\*?)\}"
            r"|\\(?P<command>appendix|section\*?|numberwithin)(?![A-Za-z])"
            r"|(?P<format>\\renewcommand\s*\{\s*\\theequation\s*\})")
        result, pos = [], 0
        while match := pattern.search(source, pos):
            result.append(source[pos:match.start()])
            name = match.group("environment")
            if name is None:
                if sub is not None:
                    raise ConversionError("Numbering controls inside subequations are unsupported")
                command, end = match.group("command"), match.end()
                if command == "appendix":
                    if self.section_prefix is not None:
                        raise ConversionError("Appendix reset inside a supplementary section series is unsupported")
                    self.appendix_section = 0
                elif command == "numberwithin":
                    counter, end = group(source, end)
                    parent, end = group(source, end)
                    if (counter.strip(), parent.strip()) != ("equation", "section") or self.appendix_section is None:
                        raise ConversionError("Only appendix equation numbering within section is supported")
                    self.within_section = True
                    self.section_separator = "."
                elif match.group("format"):
                    value, end = group(source, end)
                    if not self.within_section or re.sub(r"\s+", "", value) != r"\thesection\arabic{equation}":
                        raise ConversionError("Unsupported equation-number format")
                    self.section_separator = ""
                else:
                    while end < len(source) and source[end].isspace():
                        end += 1
                    if source[end:end + 1] == "[":
                        _, end = group(source, end, "[", "]")
                    _, end = group(source, end)
                    if command == "section" and self.appendix_section is not None:
                        self.appendix_section += 1
                        if self.within_section:
                            self.counter = 0
                    result.append(source[match.start():end])
                pos = end
                continue
            body, end = environment_end(source, match.start(), name)
            if name == "subequations":
                if sub is not None:
                    raise ConversionError("Nested subequations are unsupported")
                parent = self.next_number()
                before_inner = re.split(r"\\begin\{", body, maxsplit=1)[0]
                self.validate(before_inner, parent)
                # Pandoc need not understand the wrapper; its parent label stays.
                result.append(self.apply(body, {"parent": parent, "row": 0}))
            elif name.endswith("*"):
                result.append(source[match.start():end])
            else:
                rows = split_math_rows(body) if name in ("align", "gather") else [body]
                tagged = []
                for row in rows:
                    if not row.strip():
                        continue
                    if not re.search(r"\\(?:nonumber|notag)\b", row):
                        if sub is None:
                            number = self.next_number()
                        else:
                            sub["row"] += 1
                            if sub["row"] > 26:
                                raise ConversionError("More than 26 subequations")
                            number = sub["parent"] + chr(96 + sub["row"])
                        self.validate(row, number)
                        row = row.rstrip() + r"\tag{" + number + "}"
                        self.numbered_rows += 1
                    tagged.append(row)
                result.append(r"\begin{" + name + "}\n" + "\\\\\n".join(tagged) + r"\end{" + name + "}")
            pos = end
        result.append(source[pos:])
        return "".join(result)


def prepare_theorems(source: str, labels: dict[str, dict[str, str]],
                     prefixes: dict[str, str] | None = None) -> str:
    pattern = re.compile(r"\\begin\{(proposition|corollary|lemma|definition|assumption|remark|example|theorem)\}")
    counters: dict[str, int] = {}
    result, pos = [], 0
    for match in pattern.finditer(source):
        kind, end = match.group(1), match.end()
        while end < len(source) and source[end].isspace():
            end += 1
        title = ""
        if source[end:end + 1] == "[":
            title, end = group(source, end, "[", "]")
        counters[kind] = counters.get(kind, 0) + 1
        number = (prefixes or {}).get(kind, "") + str(counters[kind])
        first_label = re.match(r"\s*\\label\{([^}]+)\}", source[end:])
        if first_label:
            key = first_label.group(1)
            if key not in labels or labels[key]["number"] != number:
                raise ConversionError(f"Theorem numbering mismatch: {key}, expected {number}")
        heading = f"{kind.capitalize()} {number}" + (f" ({title})" if title else "") + "."
        result.extend([source[pos:match.start()], r"\begin{quote}", "\n\\textbf{" + heading + "}\n\n"])
        pos = end
    result.append(source[pos:])
    return re.sub(r"\\end\{(?:proposition|corollary|lemma|definition|assumption|remark|example|theorem)\}", r"\\end{quote}", "".join(result))


def prepare_citations(source: str, citations: dict[str, dict[str, str]]) -> tuple[str, set[str]]:
    pattern = re.compile(r"\\(citep|citet|cite)(?![A-Za-z])")
    result, pos, used = [], 0, set()
    for match in pattern.finditer(source):
        end, options = match.end(), []
        while source[end:end + 1] == "[":
            value, end = group(source, end, "[", "]")
            options.append(value)
        keys, end = group(source, end)
        prefix, suffix = (options[0], options[1]) if len(options) == 2 else ("", options[0] if options else "")
        if len(options) > 2:
            raise ConversionError("More than two citation optional arguments")
        rendered = []
        for key in [part.strip() for part in keys.split(",")]:
            if key not in citations:
                raise ConversionError(f"Citation absent from compiled AUX: {key}")
            used.add(key)
            item = citations[key]
            value = item["author"] + (" (" + item["year"] + ")" if match.group(1) in ("cite", "citet") else ", " + item["year"])
            rendered.append(r"\hyperlink{ref-" + key + "}{" + value + "}")
        text = "; ".join(rendered)
        if prefix:
            text = prefix + " " + text
        if suffix:
            if match.group(1) == "citet" and len(rendered) == 1:
                text = text[:-2] + ", " + suffix + ")}"  # append inside linked year parentheses
            else:
                text += ", " + suffix
        if match.group(1) == "citep":
            text = "(" + text + ")"
        result.extend([source[pos:match.start()], text])
        pos = end
    result.append(source[pos:])
    return "".join(result), used


def read_bibliography(path: Path) -> list[tuple[str, str]]:
    source = strip_comments(path.read_text(encoding="utf-8"))
    pattern = re.compile(r"\\bibitem(?:\[[\s\S]*?\])?\{([^}]+)\}")
    items = list(pattern.finditer(source))
    result = []
    for i, match in enumerate(items):
        end = items[i + 1].start() if i + 1 < len(items) else source.index(r"\end{thebibliography}")
        entry = source[match.end():end].strip().replace(r"\newblock", " ")
        result.append((match.group(1), entry))
    if not result:
        raise ConversionError("Empty compiled bibliography")
    return result


def merge_bibliographies(*bibliographies: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Combine the two PDFs' references without duplicate HTML destinations."""
    entries: dict[str, str] = {}
    for bibliography in bibliographies:
        for key, entry in bibliography:
            if key in entries and re.sub(r"\s+", " ", entries[key]) != re.sub(r"\s+", " ", entry):
                raise ConversionError(f"Conflicting compiled bibliography entries: {key}")
            entries.setdefault(key, entry)
    return list(entries.items())


def diagram_clip(page: Any, caption_top: float, all_panels: bool = False) -> Any:
    """Find the last connected diagram above its caption, honoring PDF clips.

    A page can contain several figures. Clipped fills may have off-screen
    control points, and horizontal/vertical axes have zero geometric area.
    Neither should make the crop absorb prose or omit part of the diagram.
    """
    import pymupdf as fitz
    clips: dict[int, Any] = {}
    rectangles = []
    for drawing in page.get_drawings(extended=True):
        level = drawing.get("level", 0)
        clips = {depth: rect for depth, rect in clips.items() if depth < level}
        if drawing["type"] == "clip":
            clips[level] = fitz.Rect(drawing["scissor"])
            continue
        if "rect" not in drawing:
            continue
        rect = fitz.Rect(drawing["rect"])
        if max(rect.width, rect.height) <= 10:
            continue
        rect += (-0.5, -0.5, 0.5, 0.5)
        for mask in clips.values():
            rect &= mask
        if not rect.is_empty and rect.y1 < caption_top:
            rectangles.append(rect)
    clusters = []
    for rect in sorted(rectangles, key=lambda r: r.y0):
        if clusters and rect.y0 <= clusters[-1].y1 + 3:
            clusters[-1] |= rect
        else:
            clusters.append(fitz.Rect(rect))
    candidates = [rect for rect in clusters if rect.width >= 80 and rect.height >= 40]
    if not candidates:
        raise ConversionError("No complete vector diagram found above caption")
    clip = fitz.Rect(candidates[-1])
    if all_panels:
        for candidate in candidates[:-1]:
            clip |= candidate
    if caption_top - clip.y1 > 60:
        raise ConversionError("Nearest diagram is too far from its caption")
    initial = fitz.Rect(clip)
    for block in page.get_text("blocks"):
        rect = fitz.Rect(block[:4])
        if (rect.y1 >= initial.y0 - 2 and rect.y0 <= initial.y1 + 24
                and rect.y1 < caption_top - 5 and rect.x1 >= initial.x0 - 25
                and rect.x0 <= initial.x1 + 25):
            clip |= rect
    clip += (-5, -5, 5, 5)
    clip.y1 = min(clip.y1, caption_top - 5)
    clip &= page.rect
    return clip


def extract_figures(source: str, root: Path, pdf: Path, assets: Path,
                    labels: dict[str, dict[str, str]], asset_prefix: str) -> tuple[str, list[dict[str, Any]]]:
    try:
        import pymupdf as fitz
    except ImportError as exc:
        raise ConversionError("PyMuPDF is required: pip install pymupdf") from exc
    assets.mkdir(parents=True, exist_ok=True)
    manuscript = fitz.open(pdf)
    pattern = re.compile(r"\\begin\{figure\}")
    result, figures, pos = [], [], 0
    while match := pattern.search(source, pos):
        body, end = environment_end(source, match.start(), "figure")
        label_matches = re.findall(r"\\label\{([^}]+)\}", body)
        if len(label_matches) != 1 or label_matches[0] not in labels:
            raise ConversionError("Every figure must have exactly one compiled label")
        key = label_matches[0]
        cap = re.search(r"\\caption\s*", body)
        if not cap:
            raise ConversionError(f"Figure without caption: {key}")
        caption, _ = group(body, cap.end())
        number = labels[key]["number"]
        filename = key.replace(":", "-") + ".svg"
        info: dict[str, Any] = {"id": key, "number": number, "asset": f"{asset_prefix}/{filename}"}
        if r"\begin{tikzpicture}" in body:
            page_index = int(labels[key]["page"]) - 1
            page = manuscript[page_index]
            captions = page.search_for(f"Figure {number}:")
            if len(captions) != 1:
                raise ConversionError(f"Cannot locate unique PDF caption for {key}")
            caption_top = captions[0].y0
            clip = diagram_clip(page, caption_top, all_panels=key == 'fig:CDFs')
            if clip.width < 80 or clip.height < 40 or clip.y0 < 0:
                raise ConversionError(f"Implausible diagram crop for {key}: {clip}")
            cropped = fitz.open()
            target = cropped.new_page(width=clip.width, height=clip.height)
            target.show_pdf_page(target.rect, manuscript, page_index, clip=clip)
            svg = target.get_svg_image(text_as_path=True)
            qa_dir = root / "tmp/web-manuscript-qa"
            qa_dir.mkdir(parents=True, exist_ok=True)
            target.get_pixmap(matrix=fitz.Matrix(2, 2)).save(qa_dir / filename.replace(".svg", ".png"))
            info.update({"kind": "tikz-pdf-crop", "pdf_page": page_index + 1, "crop": list(clip)})
            cropped.close()
        else:
            image = re.search(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", body)
            if not image:
                raise ConversionError(f"Unsupported figure content: {key}")
            figure_path = (root / image.group(1)).resolve()
            if not figure_path.is_relative_to(root.resolve()):
                raise ConversionError("Figure path escapes repository")
            document = fitz.open(figure_path)
            if len(document) != 1:
                raise ConversionError(f"Expected one-page simulation figure: {figure_path}")
            svg = document[0].get_svg_image(text_as_path=True)
            info.update({"kind": "pdf-figure", "source": figure_path.relative_to(root).as_posix()})
            document.close()
        (assets / filename).write_text(svg, encoding="utf-8")
        figures.append(info)
        # Let Pandoc retain the mathematical caption, then number it in AST.
        replacement = (r"\begin{figure}\centering\includegraphics{" + info["asset"] + "}"
                       + r"\caption{" + caption + r"}\label{" + key + r"}\end{figure}")
        result.extend([source[pos:match.start()], replacement])
        pos = end
    result.append(source[pos:])
    manuscript.close()
    return "".join(result), figures


def inlines_text(nodes: Any) -> str:
    if isinstance(nodes, list):
        return "".join(inlines_text(node) for node in nodes)
    if not isinstance(nodes, dict):
        return ""
    kind, value = nodes.get("t"), nodes.get("c")
    if kind == "Str":
        return value
    if kind in ("Space", "SoftBreak", "LineBreak"):
        return " "
    if kind == "Math":
        return value[1]
    if kind in ("Span", "Link", "Image"):
        return inlines_text(value[1])
    return inlines_text(value)


def transform_ast(document: dict[str, Any], labels: dict[str, dict[str, str]],
                  table_labels: list[str] | None = None,
                  heading_numbers: dict[tuple[int, str], str] | None = None) -> list[dict[str, Any]]:
    sections = []
    pending_tables = iter(table_labels or [])
    table_keys = set(table_labels or [])
    unsupported: set[str] = set()
    # Literal source paths are code, not URLs or executable TeX. Support the
    # brace form used in the manuscript; leave other constructs fail-closed.
    literal_path = re.compile(r"\\path\{([^{}\r\n]*)\}")

    def inspect_raw(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("t") in ("RawInline", "RawBlock") and value["c"][0] in ("latex", "tex"):
                raw = value["c"][1]
                if not (re.fullmatch(r"\\(?:label|ref|eqref)\*?\{[^}]+\}", raw)
                        or literal_path.fullmatch(raw) or raw in (r"\quad", r"\textbar")):
                    unsupported.add(raw)
            for child in value.values():
                inspect_raw(child)
        elif isinstance(value, list):
            for child in value:
                inspect_raw(child)

    inspect_raw(document)
    if unsupported:
        raise ConversionError("Unsupported raw TeX retained by Pandoc:\n" + "\n".join(sorted(unsupported)))

    def visit(node: Any) -> Any:
        if isinstance(node, list):
            return [visit(item) for item in node]
        if not isinstance(node, dict):
            return node
        kind, content = node.get("t"), node.get("c")
        if kind in ("RawInline", "RawBlock") and content[0] in ("latex", "tex"):
            if content[1] in (r"\quad", r"\textbar"):
                inline = {"t": "Space"} if content[1] == r"\quad" else {"t": "Str", "c": "|"}
                return {"t": "Plain", "c": [inline]} if kind == "RawBlock" else inline
            path = literal_path.fullmatch(content[1])
            if path:
                inline = {"t": "Code", "c": [["", [], []], path.group(1)]}
                return {"t": "Plain", "c": [inline]} if kind == "RawBlock" else inline
            raw = re.fullmatch(r"\\(label|ref|eqref)\*?\{([^}]+)\}", content[1])
            if not raw or raw.group(2) not in labels:
                raise ConversionError(f"Unsupported raw TeX or absent label: {content[1][:180]}")
            command, key = raw.groups()
            if command == "label":
                if key in table_keys:
                    return {"t": "Plain", "c": []} if kind == "RawBlock" else {"t": "Str", "c": ""}
                inline = {"t": "Span", "c": [[key, ["source-anchor"], []], []]}
            else:
                number = labels[key]["number"]
                if command == "eqref":
                    number = "(" + number + ")"
                target = labels[key].get("html_target", key)
                inline = {"t": "Link", "c": [["", [], []], [{"t": "Str", "c": number}], ["#" + target, ""]]}
            return {"t": "Plain", "c": [inline]} if kind == "RawBlock" else inline
        if kind == "Header":
            level, attrs, title = content
            key = attrs[0]
            number = labels.get(key, {}).get("number", "")
            unnumbered_paragraph = (level >= 4 and
                labels.get(key, {}).get("destination", "").startswith("section*."))
            if unnumbered_paragraph:
                number = ""
            if not number and heading_numbers:
                number = heading_numbers.get((level, inlines_text(title)), "")
            if key in labels and not unnumbered_paragraph and not labels[key]["destination"].startswith(("section.", "subsection.", "subsubsection.", "appendix.")):
                raise ConversionError(f"Header label has unexpected target: {key}")
            sections.append({"id": key, "title": inlines_text(title), "level": level, "number": number})
            if number:
                content[2] = [{"t": "Span", "c": [["", ["section-number"], []], [{"t": "Str", "c": number}]]},
                              {"t": "Space"}] + title
        elif kind == "Link":
            attrs, _, target = content
            data = dict(attrs[2])
            if "reference" in data:
                key = data["reference"]
                if key not in labels:
                    raise ConversionError(f"Reference missing from AUX: {key}")
                number = labels[key]["number"]
                if data.get("reference-type") == "eqref":
                    number = "(" + number + ")"
                content[1] = [{"t": "Str", "c": number}]
                content[2] = ["#" + labels[key].get("html_target", key), target[1]]
            elif target[0].startswith("https://oliverpardo1979.github.io/ai-growth-and-labor/#"):
                content[2][0] = "#" + target[0].split("#", 1)[1]
        elif kind == "Math":
            math_type, value = content
            math_labels = re.findall(r"\\label\{([^}]+)\}", value)
            content[1] = re.sub(r"\\label\{[^}]+\}", "", value)
            if math_labels:
                anchors = [{"t": "Span", "c": [[label, ["equation-anchor"], []], []]} for label in math_labels]
                return {"t": "Span", "c": [["", ["manuscript-equation"], []], anchors + [node]]}
        elif kind in ("Span", "Div") and content[0][0] in table_keys:
            content[0][0] = ""
        elif kind == "BlockQuote" and content and content[0].get("t") == "Para":
            first = content[0]["c"]
            heading = inlines_text(first[0]) if first and first[0].get("t") == "Strong" else ""
            theorem = re.match(r"(Proposition|Corollary|Lemma|Definition|Assumption|Remark|Example|Theorem) S?\d+", heading)
            if theorem:
                return {"t": "Div", "c": [["", ["theorem", theorem.group(1).lower()], []], visit(content)]}
        elif kind == "Figure":
            attrs, caption, _ = content
            key = attrs[0]
            if key not in labels:
                raise ConversionError(f"Figure missing compiled number: {key}")
            for block in caption[1]:
                if block["t"] in ("Plain", "Para"):
                    block["c"] = [{"t": "Strong", "c": [{"t": "Str", "c": "Figure " + labels[key]["number"] + ":"}]}, {"t": "Space"}] + block["c"]
                    break
        elif kind == "Table":
            attrs, caption = content[:2]
            key = next(pending_tables, "")
            if not key or key not in labels:
                raise ConversionError(f"Table missing compiled label: {key}")
            attrs[0] = key
            for block in caption[1]:
                if block["t"] in ("Plain", "Para"):
                    block["c"] = [{"t": "Strong", "c": [{"t": "Str", "c": "Table " + labels[key]["number"] + ":"}]}, {"t": "Space"}] + block["c"]
                    break
        if "c" in node:
            node["c"] = visit(node["c"])
        return node

    document["blocks"] = visit(document["blocks"])
    return sections


def clean_layout(source: str) -> str:
    # Layout has no counterpart in a reflowable article. Explicitly consume
    # known arguments so a generic parser cannot swallow following prose.
    for command in ("Needspace", "setstretch", "setcounter", "setlength", "addcontentsline", "vspace"):
        count = {"setcounter": 2, "setlength": 2, "addcontentsline": 3}.get(command, 1)
        for _ in range(count):
            if _ == 0:
                source = command_rewrite(source, command, lambda value: r"\WEBREMOVE" if count > 1 else "")
            else:
                source = command_rewrite(source, "WEBREMOVE", lambda value: r"\WEBREMOVE" if _ < count - 1 else "")
    source = command_rewrite(source, "tikzset", lambda value: "")
    source = re.sub(r"\\(?:clearpage|newpage|onehalfspacing|singlespacing|phantomsection|tableofcontents|maketitle|begingroup|endgroup|normalfont|appendix|small|footnotesize|centering|medskip|smallskip|noindent|hfill)\b", "", source)
    source = re.sub(r"\\bibliographystyle\{[^}]+\}|\\bibliography\{[^}]+\}", "", source)
    # minipage is layout only; keep all its contents.
    source = re.sub(r"\\begin\{minipage\}(?:\[[^]]*\])?\{[^}]+\}", "", source)
    source = source.replace(r"\end{minipage}", "")
    # The manuscript's P columns differ from p only in ragged-right layout.
    source = re.sub(r"P(?=\{[\d.]+\\textwidth\})", "p", source)
    return source


def compiled_headings(aux: Path, pandoc: Pandoc) -> dict[tuple[int, str], str]:
    """Recover numbering even for section headings without explicit labels."""
    headings = {}
    for line in aux.read_text(encoding="utf-8").splitlines():
        if not line.startswith(r"\@writefile{toc}"):
            continue
        match = re.search(r"\\contentsline\s*", line)
        if not match:
            continue
        kind, pos = group(line, match.end())
        if kind not in ("section", "subsection", "subsubsection"):
            continue
        content, _ = group(line, pos)
        numberline = re.match(r"\\numberline\s*", content)
        if not numberline:
            continue
        number, pos = group(content, numberline.end())
        title = pandoc.plain(content[pos:])
        key = (("section", "subsection", "subsubsection").index(kind) + 1, title)
        if key in headings:
            raise ConversionError(f"Ambiguous compiled heading title: {title}")
        headings[key] = number
    return headings
