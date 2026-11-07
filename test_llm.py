
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen3:1.7b",
    temperature=0
)

response = llm.invoke(
    "What is RAG? Answer in one sentence."
)

print(response.content)
