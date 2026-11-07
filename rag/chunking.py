from langchain_text_splitters import RecursiveCharacterTextSplitter


def split_pages(pages, size: int, overlap: int):
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError('Chunk size must be positive and overlap smaller than size.')
    splitter = RecursiveCharacterTextSplitter(chunk_size=size, chunk_overlap=overlap)
    return [{**page, 'text': chunk} for page in pages for chunk in splitter.split_text(page['text'])]
