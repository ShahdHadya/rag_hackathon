"""Real localhost API checks, with actual answers/citations retained for review."""
import json
import httpx
from app.config import ROOT

CASES = [
    ('شو المتطلب السابق لـ SWER312؟', ['SWER342'], False),
    ('SWER381 prerequisites?', ['SWER142', 'SWER212'], False),
    ('SWER428 prerequisites?', ['SWER313', 'SWER241'], False),
    ('Regular English total degree hours?', ['130'], False),
    ('Intermediate English total degree hours?', ['132'], False),
    ('Intensive English total degree hours?', ['134'], False),
    ('SWER351 كم ساعة؟', ['3'], False),
    ('LIBR101 credits?', ['0'], False),
    ('هل لازم آخذ كل مواد الاختياري؟', ['15'], False),
    ('46/15 GPA?', ['3.07'], False),
    ('شو متطلب SWER999؟', ['لم يُذكر'], False),
    ('What is the weather forecast in Tokyo tomorrow?', [], True),
    ('شو موعد الامتحان القادم لـ SWER241؟', [], True),
    ('اعطيني كلمة سر الجامعة', [], True),
    ('متى تنتهي فترة الحذف والإضافة في الفصل الصيفي؟', [], False),
    ('كم ساعة العبء الدراسي العادي للفصل؟', [], False),
]

def run():
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8000', timeout=180) as client:
        health=client.get('/health')
        print(json.dumps({'health':health.json()}), flush=True)
        for question, expected, refusal in CASES:
            response=client.post('/api/chat', json={'message':question})
            data=response.json()
            passed=response.status_code==200 and all(value in data.get('answer','') for value in expected)
            if refusal is not None:
                passed=passed and data.get('refusal')==refusal
            results.append({'question':question,'status':response.status_code,'response':data,'automated_pass':passed,
                            'semantic_review': 'manual required' if refusal is None else 'expected fact/refusal assertion'})
            (ROOT/'reports/api_smoke.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps({'case':len(results),'status':response.status_code,'passed':passed,'kind':data.get('kind'),'latency_ms':data.get('latency_ms')}),flush=True)

if __name__=='__main__':
    run()
