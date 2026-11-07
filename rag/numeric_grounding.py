"""Conservative numeric equivalence with claim-local citations and evidence windows."""
import re
import unicodedata
from fractions import Fraction

EN = dict(zip('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(), range(20)))
EN.update(dict(zip('twenty thirty forty fifty sixty seventy eighty ninety'.split(), range(20, 100, 10))))
AR = {'صفر': 0, 'واحد': 1, 'واحدة': 1, 'اثنان': 2, 'اثنين': 2, 'اثنتان': 2, 'اثنتين': 2,
      'ثلاث': 3, 'ثلاثة': 3, 'أربع': 4, 'أربعة': 4, 'خمس': 5, 'خمسة': 5,
      'ست': 6, 'ستة': 6, 'سبع': 7, 'سبعة': 7, 'ثمان': 8, 'ثمانية': 8,
      'تسع': 9, 'تسعة': 9, 'عشر': 10, 'عشرة': 10,
      'عشرون': 20, 'عشرين': 20, 'ثلاثون': 30, 'ثلاثين': 30, 'أربعون': 40, 'أربعين': 40,
      'خمسون': 50, 'خمسين': 50, 'ستون': 60, 'ستين': 60, 'سبعون': 70, 'سبعين': 70,
      'ثمانون': 80, 'ثمانين': 80, 'تسعون': 90, 'تسعين': 90}
WORDS = {**EN, **AR}
WORDS.update({'hundred': 100, 'مئة': 100, 'مائة': 100})
WORD_PATTERN = '|'.join(sorted(map(re.escape, WORDS), key=len, reverse=True))


def normalize(text):
    text = unicodedata.normalize('NFKC', text).lower().replace('٫', '.').replace('٬', ',').replace('٪', '%').replace('−', '-')
    text = ''.join(str(unicodedata.decimal(c)) if c.isdecimal() else c for c in text)
    text = re.sub(r'[\u064b-\u065f\u0640]', '', text)
    for pattern, value in [(r'\b(?:one |a )?half\b|\b(?:ال)?نصف\b', '1/2'),
                           (r'\b(?:one |a )?quarter\b|\b(?:ال)?ربع\b', '1/4')]:
        text = re.sub(pattern, value, text)
    # Split conjunction waw only when it prefixes a recognized numeric word.
    text = re.sub(r'\bو(?=(' + WORD_PATTERN + r')\b)', 'و ', text)
    pattern = r'(?<!\w)(?:' + WORD_PATTERN + r')(?:[ -]+(?:(?:and|و)[ -]+)?(?:' + WORD_PATTERN + r'))*(?!\w)'
    def words(match):
        value = match.group()
        # "one can" is a pronoun, not a confidently numeric claim.
        if value in ('one', 'واحد', 'واحدة') and not re.match(r'\s+(?:points?|marks?|conditions?|percent|علامة|درجة|نقطة|شرط)', text[match.end():]):
            return value
        parts = re.findall(r'(?<!\w)(?:' + WORD_PATTERN + r')(?!\w)', value)
        values = [WORDS[p] for p in parts]
        if len(parts) > 1 and 'hundred' not in parts:
            english_pair = len(parts) == 2 and parts[0] in EN and 20 <= values[0] <= 90 and 0 < values[1] < 10 and 'and' not in value
            arabic_pair = len(parts) == 2 and parts[0] in AR and ((0 < values[0] < 10 and values[1] == 10) or (0 < values[0] < 10 and values[1] >= 20 and 'و' in value))
            if not english_pair and not arabic_pair:
                return ' '.join(str(v) for v in values)
        number = 0
        for part in parts:
            number = max(number, 1)*100 if WORDS[part] == 100 else number + WORDS[part]
        return str(number)
    return re.sub(pattern, words, text)


N = r'[+-]?\d+(?:,\d{3})*(?:\.\d+)?'
PAIR = re.compile(r'(' + N + r')\s*(?:/|out\s+of|من(?:\s+أصل)?|(?:points?|marks?|علامة|درجة|نقطة)\s+(?:على الأقل\s+|at least\s+)?(?:من|out of))\s*(' + N + r')')
PERCENT = re.compile(r'(' + N + r')\s*(?:%|percent\b|per cent\b|بالمئة|بالمائة|في المئة|في المائة)')
SCALAR = re.compile(r'(?<!\w)(' + N + r')(?!\w)')


def quantities(text):
    text = normalize(text)
    result, covered = [], []
    for pattern, kind in ((PAIR, 'proportion'), (PERCENT, 'proportion'), (SCALAR, 'scalar')):
        for match in pattern.finditer(text):
            if any(match.start() < end and match.end() > start for start, end in covered):
                continue
            a = Fraction(match[1].replace(',', ''))
            b = Fraction(match[2].replace(',', '')) if pattern is PAIR else Fraction(100)
            if kind == 'proportion' and not b:
                result.append(('invalid', Fraction(0), match.group(), ()))
            else:
                result.append((kind, a / b if kind == 'proportion' else a, match.group(), (a, b) if pattern is PAIR else ()))
            covered.append(match.span())
    return result


# Small bilingual vocabulary for evidence alignment, never expected numeric answers.
GROUPS = [('bonus', 'بونص', 'مكافأة', 'إضافية'), ('technical', 'تقني', 'تقنية'),
          ('quality', 'جودة'), ('rag',), ('revenue', 'إيرادات'), ('cost', 'تكلفة', 'تكاليف'),
          ('minimum', 'least', 'الأقل', 'أدنى'), ('maximum', 'most', 'الأقصى'),
          ('score', 'points', 'marks', 'علامة', 'علامات', 'نقطة', 'درجة'),
          ('conditions', 'condition', 'شرط', 'شروط', 'استحقاق'),
          ('product', 'منتج'), ('working', 'يعمل'), ('complete', 'متكامل'),
          ('interface', 'واجهة'), ('production', 'إنتاجية'), ('features', 'feature', 'ميزات'),
          ('arabic', 'عربية', 'العربية'), ('rtl',)]
STOP = set('the a an of to in for is are be must at least out from and or with on have has achieve team teams can it this that earning earn required requires requirement minimum maximum score points marks شرط شروط علامة علامات نقطة درجة على الأقل من في إلى أن الذي التي هو هي يجب حصل الفريق'.split())
STOP.update('how many what كم ما هي مخصصة مخصص allocated worth'.split())


def anchors(text):
    tokens = set(re.findall(r'[a-z\u0621-\u064a]+', normalize(text)))
    tokens |= {t[2:] for t in tokens if t.startswith('ال')}
    for i, group in enumerate(GROUPS):
        if tokens.intersection(group):
            tokens -= set(group)
            tokens.add(f'concept{i}')
    return tokens - STOP - {'concept6', 'concept7', 'concept8', 'concept9'}


def evidence_windows(text):
    # Keep each sentence/table row local; never flatten every number in a chunk.
    return [s.strip() for s in re.split(r'\n+|(?<=[.!?؟;؛])\s+', text) if s.strip()]


def unit(text, literal):
    text = normalize(text)
    index = text.find(literal)
    if index < 0:
        return None
    after = text[index+len(literal):]
    for name, pattern in [('score', r'points?|marks?|علامة|علامات|نقطة|نقاط|درجة'),
                          ('time', r'days?|months?|years?|يوم|أيام|شهر|شهرًا|سنة'),
                          ('money', r'dollars?|usd|دولار')]:
        if re.match(r'\s*(?:' + pattern + r')\b', after):
            return name
    return None


def relation(text):
    text = normalize(text)
    lower = bool(re.search(r'at least|minimum|على الأقل|أدنى', text))
    upper = bool(re.search(r'at most|maximum|up to|الأقصى|حتى', text))
    return 'minimum' if lower and not upper else 'maximum' if upper and not lower else None


def numeric_failures(content, sources, question=None):
    content = re.sub(r'(?m)^\s*(?:[-*•]\s+|[\d]+[.)]\s+)', '', content)
    content = re.sub(r'\n\s*((?:\[\d+\]\s*)+)', r' \1', content)
    claims = re.split(r'\n+|(?<=[.!?؟;؛])\s+(?![\s\[])', content)
    failures = []
    for claim in claims:
        refs = {int(n) for n in re.findall(r'\[(\d+)\]', claim)}
        clean = re.sub(r'\[\d+\]', '', claim)
        # Reject recognized but unsupported compound-number words, rather than
        # silently ignoring them as nonnumeric prose.
        unparsed = re.search(r'\b(?:thousand|million|billion|ألف|ألفين|مليون|مليار)\b', clean, flags=re.I)
        if unparsed:
            failures.append({'claim': claim.strip(), 'numeric_expression': unparsed.group(),
                             'canonical': 'unparsed', 'kind': 'unsupported_format', 'citation_ids': sorted(refs)})
            continue
        topics = anchors(clean) or anchors(question or '')
        for kind, value, literal, components in quantities(clean):
            supported = False
            if kind == 'invalid':
                failures.append({'claim': claim.strip(), 'numeric_expression': literal,
                                 'canonical': 'invalid', 'kind': kind, 'citation_ids': sorted(refs)})
                continue
            windows = []
            for ref in refs:
                if not 1 <= ref <= len(sources):
                    continue
                for window in evidence_windows(sources[ref-1]['text']):
                    overlap = len(topics.intersection(anchors(window)))
                    if overlap or not topics:
                        windows.append((overlap, window))
            best_overlap = max((score for score, _ in windows), default=-1)
            for score, window in windows:
                if score != best_overlap:
                    continue
                if relation(clean) and relation(window) and relation(clean) != relation(window):
                    continue
                for e_kind, e_value, e_literal, e_components in quantities(window):
                    if unit(clean, literal) and unit(window, e_literal) and unit(clean, literal) != unit(window, e_literal):
                        continue
                    if (kind == e_kind and value == e_value) or (kind == 'scalar' and value in e_components):
                        supported = True
                        break
                if supported:
                    break
            if not supported:
                failures.append({'claim': claim.strip(), 'numeric_expression': literal,
                                 'canonical': str(value), 'kind': kind, 'citation_ids': sorted(refs)})
    return failures
