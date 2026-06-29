from database import Database
from applications import *
from embedding import Embedder
from time import time

# Global variable
TEST = False
BATCH_SIZE = 100000

def check_claims(claims):
    """Check if the claims are complete and not empty."""
    if claims is None or len(claims) == 0:
        return False
    else:
        return True

def embed_patents(db, use_embedding=False):
    """Embed all the patents using the embedding model."""

    patent_ids = db.get_claims_ids()

    if TEST:
        patent_ids = patent_ids[:1000]

    print(f"Total patents to embed: {len(patent_ids)}, starting embedding...")

    start_time = time()
    patents = []
    embedding_ids =[]
    for patent_id in patent_ids:
        claims = db.get_claims_str(patent_id)

        #check if claims are complete and not empty
        if check_claims(claims) is False:
            print(f"Patent {patent_id} has no claims, skipping...")
            continue
        else:
            patents.append(claims)
            embedding_ids.append(patent_id)

    print(f"Total patents to embed after filtering: {len(embedding_ids)}")
    print(f"Number of patents removed: {len(patent_ids) - len(embedding_ids)}/{len(patent_ids)}")

    if use_embedding:
        emb = Embedder()
        emb.embed_documents(patents, embedding_ids)

    end_time = time()
    print(f"Finished embedding {len(embedding_ids)} patents in {end_time - start_time} seconds")

def get_app_score(app_id, app_text, embedder, citations):
    """Get the similarity score between the application claims and the patent claims."""
    if citations is None or len(citations) == 0:
        return None
    app_embedding = embedder.embed_claims([app_text])
    ranking = embedder.get_patent_ranking(app_embedding)
    score ={}
    for patent_id in citations:
        score[patent_id] = score[patent_id]

def main():
    db = Database(
        host="db",
        port=5432,
        database="patents_db",
        user="postgres",
        password="postgres"
    )  
    embed_patents(db)
    db.close()
    
if __name__ == "__main__":
    main()
