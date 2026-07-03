import json
from pathlib import Path

import faiss
import numpy as np
from FlagEmbedding import BGEM3FlagModel

from database import Database

class Pipeline:
    def __init__(self):
        self.db = Database(
            host="db",
            port=5432,
            database="patents_db",
            user="postgres",
            password="postgres"
        )
        self.model = BGEM3FlagModel('BAAI/bge-m3',  
                       use_fp16=True) # Setting use_fp16 to True speeds up computation with a slight performance degradation
        self.model_dimension = 1024
        self.index = self._create_index()
        self.faiss_id_to_patent_id: dict[int, str] = {}
        self._load_index_if_available()

    def _create_index(self):
        index = faiss.IndexIDMap(faiss.IndexFlatIP(self.model_dimension))
        return index

    def _load_index_if_available(self):
        index_path = Path("faiss_index.bin")
        mapping_path = Path("faiss_id_to_patent_id.json")

        if index_path.exists() and mapping_path.exists():
            print("Loading existing FAISS index and mapping...")
            self.index = faiss.read_index(str(index_path))
            with open(mapping_path, "r") as f:
                self.faiss_id_to_patent_id = json.load(f)
        else:
            print("No existing FAISS index found. A new index will be created.")
    
    def _save_index(self):
        faiss.write_index(self.index, "faiss_index.bin")
        with open("faiss_id_to_patent_id.json", "w") as f:
            json.dump(self.faiss_id_to_patent_id, f)
    
    def embed_claims(self):
        patent_ids = self.db.get_claims_ids()
        self.index = self._create_index()
        self.faiss_id_to_patent_id.clear()

        for patent_id in patent_ids:
            print(f"Processing patent ID: {patent_id}")
            claims_str = self.db.get_claims_str(patent_id)
            if not claims_str.strip():
                print(f"Skipping patent ID {patent_id}: no claims text found.")
                continue

            embedding = self.model.encode([claims_str], batch_size=12, max_length=8192)
            faiss_id = len(self.faiss_id_to_patent_id)
            self.index.add_with_ids(embedding, np.array([faiss_id], dtype=np.int64))
            self.faiss_id_to_patent_id[faiss_id] = patent_id

        self._save_index()

    def embedd_claims(self):
        self.embed_claims()

    def get_similar_claims(self, query, top_k=5):
        if self.index.ntotal == 0:
            return []

        query_embedding = self._encode_text("search_query", query)
        scores, indices = self.index.search(query_embedding, top_k)

        results = []
        for score, faiss_id in zip(scores[0], indices[0]):
            if faiss_id == -1:
                continue
            patent_id = self.faiss_id_to_patent_id.get(int(faiss_id))
            if patent_id is None:
                continue
            results.append({"patent_id": patent_id, "score": float(score)})
        return results

    def close(self):
        self.db.close()


if __name__ == "__main__":
    pipeline = Pipeline()
    try:
        pipeline.embed_claims()
        print(pipeline.get_similar_claims("A method for manufacturing a widget"))
    finally:
        pipeline.close()
