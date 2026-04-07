

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os

class RetrievalAgent:
	def __init__(self, memory, vector_db_path=None):
		self.memory = memory
		if vector_db_path is None:
			vector_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../storage/rag_faiss_index'))
			self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
		self.vector_db = FAISS.load_local(vector_db_path, self.embeddings, allow_dangerous_deserialization=True)

	def retrieve(self, sensor_row, top_k=3):
		# Compose a query from sensor_row (simple stringification for now)
		query = " ".join([f"{k}:{v}" for k, v in sensor_row.items()])
		docs_and_scores = self.vector_db.similarity_search_with_score(query, k=top_k)
		sources = [doc.page_content for doc, _ in docs_and_scores]
		meta = [doc.metadata for doc, _ in docs_and_scores]
		return {"sources": sources, "meta": meta}
