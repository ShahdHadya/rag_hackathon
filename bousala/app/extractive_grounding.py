"""Only verbatim cited excerpts may leave the general document-answer path."""
import json
import re

def validate_excerpts(raw,hits):
    try:
        body=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$','',raw.strip()))
        excerpts=body['excerpts']
        if not isinstance(excerpts,list) or not 1<=len(excerpts)<=3:
            return None
        validated=[]
        for item in excerpts:
            source_id=item['source_id']
            quote=item['quote']
            if type(source_id) is not int or not 1<=source_id<=len(hits) or not isinstance(quote,str):
                return None
            # Whitespace differences are extraction/display differences, not a
            # license to change words, digits, punctuation or negation.
            literal=' '.join(quote.split())
            evidence=' '.join(hits[source_id-1]['text'].split())
            if not 20<=len(literal)<=1200 or literal not in evidence:
                return None
            validated.append((source_id,quote.strip()))
        return validated
    except (ValueError,KeyError,TypeError):
        return None
