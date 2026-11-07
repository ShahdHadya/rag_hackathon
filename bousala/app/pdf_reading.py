from io import BytesIO
from pypdf import PdfReader
import unicodedata
import re


def normalize_text(text):
    # NFKC folds Arabic presentation forms; it does not reverse text or reshape glyphs.
    return unicodedata.normalize('NFKC', text).replace('\u00ad', '').strip()


def positioned_text(page):
    """Order logical text runs by PDF geometry; never reverse Arabic characters.

    Suitable for horizontal text with separate positioned words. Multi-column and
    rotated layouts still need review; keep each embedded text run intact.
    """
    runs = []
    def visit(text, cm, tm, font, size):
        text = normalize_text(text)
        if text:
            x = tm[4]*cm[0] + tm[5]*cm[2] + cm[4]
            y = tm[4]*cm[1] + tm[5]*cm[3] + cm[5]
            runs.append((x, y, text))
    fallback = normalize_text(page.extract_text(visitor_text=visit) or '')
    if not re.search(r'[\u0600-\u06ff]', fallback):
        return fallback
    lines = []
    for x, y, text in sorted(runs, key=lambda r: -r[1]):
        if not lines or abs(lines[-1][0] - y) > 2.5:
            lines.append((y, []))
        lines[-1][1].append((x, text))
    output = []
    for _, line in lines:
        rtl = any(re.search(r'[\u0600-\u06ff]', text) for _, text in line)
        ordered = sorted(line, key=lambda r: r[0], reverse=rtl)
        # Adjacent Latin-only runs keep their own left-to-right order.
        if rtl:
            start = 0
            while start < len(ordered):
                if re.search(r'[A-Za-z]', ordered[start][1]) and not re.search(r'[\u0600-\u06ff]', ordered[start][1]):
                    end = start + 1
                    while end < len(ordered) and re.search(r'[A-Za-z]', ordered[end][1]) and not re.search(r'[\u0600-\u06ff]', ordered[end][1]):
                        end += 1
                    ordered[start:end] = sorted(ordered[start:end])
                    start = end
                else:
                    start += 1
        output.append(' '.join(text for _, text in ordered))
    return '\n'.join(output)


def compare_extractors(data: bytes, pages=(0, 1)):
    """Read-only diagnostic for choosing an extractor on a real PDF fixture."""
    import pymupdf as fitz
    reader = PdfReader(BytesIO(data))
    with fitz.open(stream=data, filetype='pdf') as document:
        return [
            {'page': index + 1,
             'pypdf': normalize_text(reader.pages[index].extract_text() or ''),
             'pymupdf': normalize_text(document[index].get_text(sort=True))}
            for index in pages if index < len(reader.pages) and index < len(document)
        ]


def read_pdf(data: bytes, name: str):
    pages = []
    try:
        reader = PdfReader(BytesIO(data))
        for number, page in enumerate(reader.pages, 1):
            text = positioned_text(page)
            if text:
                pages.append({'text': text, 'source': name, 'page': number})
    except Exception as exc:
        return [], f'{name}: could not read PDF ({exc})'
    if not pages:
        return [], f'{name}: no extractable text; scanned pages need OCR.'
    return pages, None
