# Embedding example using the Qwen3-Embedding-0.6B model from Hugging Face

from database import Database
from sentence_transformers import SentenceTransformer
import numpy as np

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", device="cuda")
        self.document_embeddings = {}

    def save_embedding(self, patent_id, embedding):
        """Save the embedding to the database."""
        self.document_embeddings[patent_id] = embedding[0]
    
    def save_embeddings(self, patent_ids, embeddings):
        """Save the embeddings to the database."""
        for patent_id, embedding in zip(patent_ids, embeddings):
            self.document_embeddings[patent_id] = embedding

    def write_embeddings_to_file(self):
        """Write the embeddings to a file."""
        with open("embeddings.", "w") as f:
            for patent_id, embedding in self.document_embeddings.items():
                f.write(f"{patent_id}\t{embedding.tolist()}\n")

    def embed_claims(self, claims: list[str]):
        """Embed a list of claims using the model. We use a prompt to help the model understand the context of the claims."""
        return self.model.encode(claims, prompt_name="query")

    def embed_documents(self, documents: list[str], patent_ids: list[str]):
        """Embed a list of documents using the model."""
        embeddings = self.model.encode(documents, batch_size=4, show_progress_bar=True)
        #self.save_embeddings(patent_ids, embeddings)
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

    embedder = Embedder()
    text1 ="0.claims: 1. A method for processing data, comprising: receiving input data; analyzing the input data to extract relevant features; applying a machine learning model to the extracted features to generate predictions; and outputting the predictions. 2. The method of claim 1, wherein the machine learning model is a neural network. 3. The method of claim 1, further comprising storing the predictions in a database for future reference."
    text2 = "0.claims: 1. A system for managing inventory, comprising: a database for storing inventory data; a user interface for displaying inventory information; a processing unit for analyzing inventory data and generating reports; and a communication module for transmitting inventory information to external devices. 2. The system of claim 1, wherein the processing unit is configured to generate alerts when inventory levels fall below a predetermined threshold. 3. The system of claim 1, further comprising a mobile application for accessing inventory information remotely."
    embedding1 = embedder.embed_claims([text1])
    embedding2 = embedder.embed_claims([text2])
    print(embedding1.shape)
    print(len(embedding1))
    print(embedding1)
    embedder.save_embedding("test_patent", embedding1)
    embedder.save_embedding("test_patent_2", embedding2)
    print(embedder.document_embeddings)
    print(embedder.get_similar_documents(text2, top_k=5))