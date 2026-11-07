import streamlit as st
from config import CHUNK_SIZE, CHUNK_OVERLAP, TOP_K
from rag.ingestion import read_pdf
from rag.chunking import split_pages
from rag.vector_store import index_chunks, reset, collection
from rag.retrieval import retrieve
from rag.generation import AnswerStream, prompt_for
from rag.generation import is_arabic, is_abstention
from html import escape
import re
from time import perf_counter
from rag.context_selection import focus_sources

st.set_page_config(page_title='Local RAG', page_icon='📚', layout='wide')
st.markdown('<style>.rag-text[dir="rtl"]{text-align:right}.rag-text[dir="ltr"]{text-align:left}.rag-source{unicode-bidi:plaintext;white-space:pre-wrap}.st-key-live-answer-rtl [data-testid="stMarkdownContainer"]{direction:rtl;text-align:right;unicode-bidi:plaintext}.st-key-live-answer-ltr [data-testid="stMarkdownContainer"]{direction:ltr;text-align:left}</style>', unsafe_allow_html=True)


def display_text(value, language_hint=None):
    direction = 'rtl' if is_arabic(language_hint if language_hint is not None else value) else 'ltr'
    safe = escape(value)
    safe = re.sub(r'\[(\d+)\]', r'<bdi>[\1]</bdi>', safe)
    st.markdown(f'<div class="rag-text" dir="{direction}">{safe}</div>', unsafe_allow_html=True)


def display_sources(sources):
    for number, source in enumerate(sources, 1):
        with st.expander(f"[{source.get('citation_id', number)}] {source['source']} · p. {source['page']} · similarity {source['similarity']:.2f}"):
            st.markdown(f'<div class="rag-source" dir="auto">{escape(source["text"])}</div>', unsafe_allow_html=True)
st.title('📚 Document Q&A | أسئلة المستندات')
st.caption('Local PDF search with Qwen and source pages')
with st.sidebar:
    files = st.file_uploader('Upload PDFs | ارفع ملفات PDF', type='pdf', accept_multiple_files=True)
    if st.button('Index documents | فهرسة', disabled=not files):
        with st.spinner('Extracting and indexing…'):
            for file in files:
                pages, error = read_pdf(file.getvalue(), file.name)
                if error:
                    st.warning(error)
                    continue
                try:
                    count = index_chunks(split_pages(pages, CHUNK_SIZE, CHUNK_OVERLAP))
                    st.success(f'{file.name}: {count} new chunks')
                except Exception as exc:
                    st.error(f'{file.name}: indexing failed: {exc}')
    st.caption(f'Indexed chunks: {collection().count()}')
    if st.button('Reset index | حذف الفهرس'):
        reset()
        st.session_state.messages = []
        st.rerun()
    if st.button('Clear chat | مسح المحادثة'):
        st.session_state.messages = []
        st.rerun()

st.session_state.setdefault('messages', [])
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        if message.get('status') == 'unverified':
            st.warning('Previous draft was unverified and discarded | تم استبعاد المسودة غير المتحقق منها')
        display_text(message['content'], message.get('question'))
        display_sources(message.get('sources', []))
if question := st.chat_input('Ask about your PDFs | اسأل عن الملفات'):
    st.session_state.messages.append({'role': 'user', 'content': question})
    with st.chat_message('user'):
        display_text(question)
    with st.chat_message('assistant'):
        draft = st.empty()
        try:
            with st.spinner('Retrieving and preparing context | استرجاع وتجهيز السياق…'):
                retrieval_started = perf_counter()
                candidates = retrieve(question, TOP_K)
                sources = focus_sources(question, candidates)
                retrieval_seconds = perf_counter() - retrieval_started
                preparation_started = perf_counter()
                prompt = prompt_for(question, sources)
                preparation_seconds = perf_counter() - preparation_started
            stream = AnswerStream(question, sources, prepared_prompt=prompt)
            with draft.container():
                st.caption('Provisional draft — citations have not yet been checked | مسودة قبل التحقق من الاستشهادات')
                direction = 'rtl' if is_arabic(question) else 'ltr'
                with st.container(key=f'live-answer-{direction}'):
                    st.write_stream(stream.ui_chunks())
            draft.empty()
            response = stream.final
            invalid = stream.validation_reason not in ('accepted_citation_ids_and_grounding_checks', 'model_refusal', 'no_retrieved_context')
            if invalid:
                st.warning('Streamed draft was unverified and discarded | تم استبعاد المسودة غير المتحقق منها')
                response = 'تعذر التحقق من استشهادات الإجابة أو تأريضها؛ حاول إعادة السؤال.' if is_arabic(question) else 'The streamed answer failed citation or grounding checks and was discarded. Please retry.'
            elif stream.validation_reason == 'model_refusal':
                st.info('Provisional output replaced by refusal | تم استبدال المسودة برسالة عدم توفر المعلومات')
            display_text(response, question)
            st.caption(f"Retrieval {retrieval_seconds:.2f} s · first raw token {stream.metrics['first_raw_token_seconds']} s · first visible token {stream.metrics['first_visible_token_seconds']} s · generation total {stream.metrics['total_seconds']:.2f} s")
            with st.expander('Generation diagnostics (no document content)'):
                st.json({'validation': stream.validation_reason,
                         'numeric_checks': [{k: v for k, v in detail.items() if k != 'claim'} for detail in stream.validation_details],
                         'retrieval_candidates': len(candidates), 'context_chunks': len(sources),
                         'retrieval_seconds': retrieval_seconds, 'prompt_preparation_seconds': preparation_seconds, **stream.metrics})
            cited_numbers = {int(n) for n in re.findall(r'\[(\d+)\]', response)}
            supporting = [] if is_abstention(response) else [{**source, 'citation_id': i} for i, source in enumerate(sources, 1) if i in cited_numbers]
            if supporting:
                st.caption('Cited source snippets | المقاطع المستشهد بها')
                display_sources(supporting)
            elif sources:
                with st.expander('Retrieval diagnostics (not supporting evidence)'):
                    display_sources(sources)
            st.session_state.messages.append({'role': 'assistant', 'content': response, 'question': question, 'sources': supporting, 'status': 'unverified' if invalid else 'refusal' if is_abstention(response) else 'validated', 'metrics': {'retrieval_seconds': retrieval_seconds, 'prompt_preparation_seconds': preparation_seconds, **stream.metrics}})
        except Exception as exc:
            draft.empty()
            st.error('Stream interrupted or unavailable; provisional text was discarded. / تم استبعاد النص المؤقت.')
            st.error(str(exc))
