import os
import gradio as gr
import pandas as pd

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_community.document_loaders import (
    PyPDFLoader,
    CSVLoader,
    UnstructuredWordDocumentLoader
)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


# ==============================
# 1️⃣ SET API KEY
# ==============================
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found. Set it in Hugging Face Secrets.")


# ==============================
# 2️⃣ INITIALIZE LLM
# ==============================
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    api_key=GROQ_API_KEY
)


# ==============================
# 3️⃣ SYSTEM PROMPT
# ==============================
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert AI assistant.\n"
     "Answer ONLY using the provided context.\n"
     "If answer not found, say document does not contain it.\n"
     "Use structured bullet points when appropriate."),
    ("human",
     "Context:\n{context}\n\nQuestion: {question}")
])

rag_chain = prompt | llm | StrOutputParser()


# ==============================
# 4️⃣ DOCUMENT LOADER
# ==============================
def load_document(file_path):

    if file_path.endswith(".pdf"):
        loader = PyPDFLoader(file_path)

    elif file_path.endswith(".docx"):
        loader = UnstructuredWordDocumentLoader(file_path)

    elif file_path.endswith(".csv"):
        loader = CSVLoader(file_path)

    elif file_path.endswith(".xlsx"):
        df = pd.read_excel(file_path)
        temp_csv = "converted_temp.csv"
        df.to_csv(temp_csv, index=False)
        loader = CSVLoader(temp_csv)

    else:
        raise ValueError("Unsupported file type.")

    return loader.load()


# ==============================
# 5️⃣ RAG PIPELINE FUNCTION
# ==============================
def rag_pipeline(files, question):

    all_docs = []

    for file in files:
        docs = load_document(file.name)
        all_docs.extend(docs)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100
    )

    chunks = splitter.split_documents(all_docs)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = FAISS.from_documents(chunks, embeddings)

    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    retrieved_docs = retriever.invoke(question)

    context = "\n\n".join(doc.page_content for doc in retrieved_docs)

    response = rag_chain.invoke({
        "context": context,
        "question": question
    })

    return response

# ==============================
# 6️⃣ GRADIO UI
# ==============================
interface = gr.Interface(
    fn=rag_pipeline,
    inputs=[
        gr.File(label="Upload Documents", file_count="multiple"),
        gr.Textbox(label="Ask your question")
    ],
    outputs="text",
    title="Rabia`s Multi-Document RAG Application",
    description="Upload multiple documents and ask grounded questions."
)

if __name__ == "__main__":
    interface.launch()
