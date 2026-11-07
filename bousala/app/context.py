"""Bounded explicit follow-up resolution shared by deterministic and RAG paths."""
import re
from app.text import normalize

TRACKS={'regular':('REGULAR','العادي','عادي'), 'intermediate':('INTERMEDIATE','المتوسط','متوسط'), 'intensive':('INTENSIVE','المكثف','مكثف')}

def track_from_text(text):
    value=normalize(text)
    matches=[]
    for track,aliases in TRACKS.items():
        for alias in aliases:
            match=re.search(r'(?<![A-Z\u0621-\u064a])'+re.escape(normalize(alias))+r'(?![A-Z\u0621-\u064a])',value)
            if match:
                matches.append((match.start(),track))
    return min(matches)[1] if matches else None

def resolve_followup(message,history):
    value=normalize(message).strip(' .؟?')
    exact_track=next((track for track,aliases in TRACKS.items() if value in {normalize(a) for a in aliases}),None)
    if exact_track:
        previous=next((turn.content for turn in reversed(history[-6:]) if turn.role=='user'),None)
        if previous:
            # Latest explicit choice leads so it overrides an earlier placement.
            return message+' — '+previous,exact_track
    return message,track_from_text(message)
