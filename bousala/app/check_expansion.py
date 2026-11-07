"""Live local verification of expanded academic lookups; never rebuilds data."""
import json
import httpx
from app.db import session
from app.academic_queries import catalog_data
from app.config import ROOT

def run():
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=90,trust_env=False) as c:
        c.get('/health').raise_for_status()
        def ask(program,q,history=None):
            r=c.post('/api/chat',json={'message':q,'program':program,'history':history or []})
            r.raise_for_status()
            return r.json()
        for program in ['software','simulation']:
            with session() as db:
                _,terms=catalog_data(db,program,'paradigm')
            for t in terms:
                q=f"Year {t['year']} {t['term']} {t['track']} credits?"
                d=ask(program,q)
                assert not d['refusal'] and d['kind']=='calculation',(q,d)
                assert f": {t['total']} credits" in d['answer'],(q,d)
                sid='simulation_paradigm' if program=='simulation' else 'catalog_paradigm'
                assert d['citations'] and all(s['source_id']==sid for s in d['citations'])
                results.append({'program':program,'question':q,'passed':True})
            for q in ['شو مواد السنة الأولى Regular؟','شو مواد السنة الرابعة Intensive؟','شو الفرق بالساعات بين Regular وIntermediate وIntensive؟','مجموع ساعات MATH141 و SWER141؟','شو مواد الانجليزي Intermediate؟','قديش ساعات متطلبات الجامعة؟','كم معدل التخرج المطلوب؟']:
                d=ask(program,q)
                assert not d['refusal'] and d['citations'],(q,d)
                results.append({'program':program,'question':q,'passed':True})
            d=ask(program,'كم ساعة بخلص في الفصل الاول سنة اولى ؟')
            assert d['kind']=='clarification' and not d['citations']
            first='كم ساعة الفصل الاول سنة اولى Regular؟'
            a=ask(program,first)
            follow=ask(program,'والفصل الثاني؟',[{'role':'user','content':first},{'role':'assistant','content':a['answer'][:3000]}])
            assert not follow['refusal'] and '16 ساعة' in follow['answer'],follow
            for q in ['شو لون الشمس','شو المواد المطروحة هالفصل؟','مجموع ساعات MATH141 و XXXX999؟']:
                d=ask(program,q)
                assert d['refusal'] and not d['citations'],(q,d)
            assert len(c.get('/api/faq',params={'program':program}).json())==11
        d=ask('software','شو بيفتح SWER141؟')
        assert d['citations'] and 'SWER142' in d['answer'],d
        d=ask('simulation','بأي فصل موجود CSSE461 في الخطة Regular؟')
        assert not d['refusal'] and 'الرابعة' in d['answer'],d
    (ROOT/'reports/expanded_questions_checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PASS: {len(results)} positive semester/year/course checks; missing-track clarification, history, reverse prerequisites, location, FAQ and refusal checks passed.')

if __name__=='__main__':
    run()
