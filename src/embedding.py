# Embedding example using the Qwen3-Embedding-0.6B model from Hugging Face

from database import Database
from sentence_transformers import SentenceTransformer
import numpy as np

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device="cuda")
        self.document_embeddings = {}
        self.document_ids = []

    def save_embedding(self, patent_id, embedding):
        """Save the embedding to the database."""
        self.document_embeddings[patent_id] = embedding
        self.document_ids.append(patent_id)

    def embed_claims(self, claims: list[str]):
        """Embed a list of claims using the model. We use a prompt to help the model understand the context of the claims."""
        return self.model.encode(claims, prompt_name="query")

    def embed_documents(self, documents: list[str], patent_ids: list[str]):
        """Embed a list of documents using the model."""
        embeddings = self.model.encode(documents, batch_size=16, show_progress_bar=True)
        self.document_embeddings.update(zip(patent_ids, embeddings))
        self.document_ids.extend(patent_ids)
        return embeddings

    def similarity(self, query_embeddings, document_embeddings):
        return self.model.similarity(query_embeddings, document_embeddings)

    def get_similar_documents(self, query: str, top_k=5):
        query_embedding = self.model.encode([query], prompt_name="query")
        similarities = self.similarity(query_embedding, list(self.document_embeddings.values()))
        sorted_docs = sorted(zip(list(self.document_embeddings.keys()), similarities))

        print(similarities)
        print(list(self.document_embeddings.keys()))
        return sorted_docs[:top_k]
    
    def get_patent_ranking(self, claims: str):
        """Get the ranking of patents based on the similarity to the given embedding."""
        embedding = self.model.encode([claims], prompt_name="query")
        #compute similarity between the embedding and all the document embeddings using cosine similarity
        # Cosine similarity = dot product if embeddings are normalized
        scores = embedding @ self.document_embeddings.values().T
        scores = scores[0]

        # Ranking
        ranking = np.argsort(scores)[::-1]

        for rank, idx in enumerate(ranking, start=1):
            print(rank, scores[idx], docs[idx])
        
    def rank_documents(self, app_text, patents_text, patent_ids, app_ids):
        query_emb = self.model.encode([app_text], normalize_embeddings=True)
        doc_embs = self.model.encode(patents_text, normalize_embeddings=True, batch_size=16)

        scores = (query_emb @ doc_embs.T)[0]
        top_idx = np.argsort(scores)[::-1]

        return [
            {
                "rank": rank + 1,
                "patent_id": patent_ids[idx],
                "score": float(scores[idx])
            }
            for rank, idx in enumerate(top_idx)
        ]

if __name__ == "__main__":
    embedder = Embedder()
    model = embedder.model

    import json
    from database import *
    from applications import *

    db = Database(
        host="db",
        port=5432,
        database="patents_db",
        user="postgres",
        password="postgres"
    )

    with open("HUPD_sample/valid_citations.json", "r") as f:
        data = json.load(f)
        citations = data["citations"]
        print(citations)

    patents_ids = []
    docs = []
    app_ids = []
    application_claims = []

    for app_id in citations.keys():
        print(f"Application ID: {app_id}")
        claims = get_app_claims(app_id)
        print(claims[:100])
        app_ids.append(app_id)
        application_claims.append(claims)

        for patent_id in citations[app_id]:
            #print(f"  Cited Patent ID: {patent_id}")
            claims = db.get_claims_str(patent_id)
           # print(patent_id, claims[:100])

            patents_ids.append(patent_id)
            docs.append(claims)

    print(f"Total applications: {len(app_ids)}")
    print(f"Total patents: {len(patents_ids)}")
    print(patents_ids[:10])
    for i, app_id in enumerate(app_ids):
        print(f"Application ID: {app_id}")
        score = embedder.rank_documents(application_claims[i], docs, patents_ids, app_ids)
        #print(score)
        for patent_id in citations[app_id]:
            #get the rank where patent_id is located in the score list
            rank = next((s["rank"] for s in score if s["patent_id"] == patent_id), None)
            print(f"  Cited Patent ID: {patent_id}, Rank: {rank}")
