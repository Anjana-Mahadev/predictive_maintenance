import os
from glob import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../docs/rag'))
VECTOR_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../storage/rag_faiss_index'))

# 1. Load all PDFs
pdf_files = glob(os.path.join(DOCS_DIR, '*.pdf'))
all_docs = []
for pdf in pdf_files:
    loader = PyPDFLoader(pdf)
    docs = loader.load()
    all_docs.extend(docs)
print(f"Loaded {len(all_docs)} documents from {len(pdf_files)} PDFs.")

# 2. Embed documents
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 3. Build FAISS vector store
vector_db = FAISS.from_documents(all_docs, embeddings)
vector_db.save_local(VECTOR_DB_PATH)
print(f"FAISS vector DB saved to {VECTOR_DB_PATH}")
