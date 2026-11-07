import json
from time import perf_counter
from app.config import ROOT
from app.db import session
from app.retrieval import retrieve
from app.main import compose

reports=[]
for question in ['متى تنتهي فترة الحذف والإضافة في الفصل الصيفي؟','كم ساعة العبء الدراسي العادي للفصل؟']:
    with session() as db:
        hits=retrieve(db,question)
        audit={}
        start=perf_counter()
        answer,citations,refusal=compose(question,hits,audit)
        reports.append({'question':question,'hits':hits,'audit':audit,'answer':answer,'citations':citations,'refusal':refusal,'generation_seconds':perf_counter()-start})
        (ROOT/'reports/policy_diagnostics.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'case':len(reports),'pages':[h['page'] for h in hits],'refusal':refusal,'reason':audit.get('reason'),'seconds':reports[-1]['generation_seconds']}),flush=True)
