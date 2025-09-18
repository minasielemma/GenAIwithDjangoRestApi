import os
import re
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OllamaEmbeddings
import pandas as pd
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", "faiss_indexes")

class LocalPDFVectorizer:

    def __init__(self, doc_id: int):
        self.doc_id = doc_id
        self.embeddings = OllamaEmbeddings(model="artifish/llama3.2-uncensored")
        self.index_path = os.path.join(FAISS_INDEX_DIR, f"doc_{doc_id}")

    def load_and_split_pdf(self, file_path: str, chunk_size: int = 1000, chunk_overlap: int = 100):
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        chunks = text_splitter.split_documents(docs)
        return chunks

    def create_faiss_index(self, chunks):
        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        os.makedirs(FAISS_INDEX_DIR, exist_ok=True)
        vectorstore.save_local(self.index_path)
        return vectorstore

    def load_index(self):
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"FAISS index not found for doc {self.doc_id}")
        return FAISS.load_local(self.index_path, self.embeddings, allow_dangerous_deserialization=True)

    def query(self, query_text: str, k: int = 3):
        vectorstore = self.load_index()
        docs = vectorstore.similarity_search(query_text, k=k)
        return "\n".join([doc.page_content for doc in docs])

    def get_all_chunks(self, k: int = 1000):  
        vectorstore = self.load_index()
        docs = vectorstore.similarity_search(" ", k=k)
        return docs

    def extract_data(self, text: str, pattern: str = r"(\w+):\s*(\d+(?:\.\d+)?)"): 
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            df = pd.DataFrame(matches, columns=['Label', 'Value'])
            df['Value'] = pd.to_numeric(df['Value'])
            return df
        return pd.DataFrame()  