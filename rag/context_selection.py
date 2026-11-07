"""Conservative bilingual lexical focus within accepted retrieval candidates."""
import re
from rag.numeric_grounding import normalize

# Extensible query vocabulary; no answers, scores, filenames, or page IDs.
VOCABULARY = [set('bonus بونص مكافأة مكافآت إضافية'.split()),
              set('condition conditions eligibility شرط شروط استحقاق'.split()),
              set('technical تقني تقنية التقني التقنية'.split()),
              set('quality جودة'.split())]


def tokens(text):
    words = set(re.findall(r'[a-z\u0621-\u064a]+', normalize(text)))
    return words | {w[2:] for w in words if w.startswith('ال')}


def focus_sources(question, sources):
    groups = [group for group in VOCABULARY if tokens(question).intersection(group)]
    if len(groups) < 2:
        return sources
    focused = [source for source in sources if all(tokens(source['text']).intersection(group) for group in groups)]
    return focused or sources
