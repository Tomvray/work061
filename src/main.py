from torch import embedding

from database import Database
from applications import *
from embedding import Embedder
from time import time

# Global variable
TEST = False
TEST_SIZE = 10000
BATCH_SIZE = 10000

def check_claims(claims):
    """Check if the claims are complete and not empty."""
    if claims is None or len(claims) == 0:
        return False
    else:
        return True

def embed_patents(db, embedder, use_embedding=True):
    """Embed all the patents using the embedding model."""

    patent_ids = db.get_claims_ids()

    if TEST:
        patent_ids = patent_ids[:TEST_SIZE]

    print(f"Total patents to embed: {len(patent_ids)}, starting embedding...")


    start_time = time()
    for batch in range(0, len(patent_ids), BATCH_SIZE):
        print(f"Embedding patents {batch//BATCH_SIZE + 1}/ {len(patent_ids)//BATCH_SIZE}...")
        patents = []
        embedding_ids =[]
        max_length = 0
        batch_ids = patent_ids[batch:batch + BATCH_SIZE]
        for patent_id in batch_ids:
            claims = db.get_claims_str(patent_id)

            #check if claims are complete and not empty
            if check_claims(claims) is False:
                print(f"Patent {patent_id} has no claims, skipping...")
                continue
            
            length = len(claims.split())
            if length > 8000:
                print(f"Patent {patent_id} has claims longer than 8000 words, skipping...")
                continue
            else:     
                if length > max_length:
                    max_length = length
                patents.append(claims)
                embedding_ids.append(patent_id)
        if use_embedding:
            print(f"Max length of claims in this batch: {max_length}")
            embedder.embed_documents(patents, embedding_ids)


    nb_patents = len(embedder.document_embeddings.keys())
    print(f"Total patents to embed after filtering: {nb_patents}/{len(patent_ids)}")
    print(f"Number of patents removed: {len(patent_ids) - nb_patents}/{len(patent_ids)}")

    end_time = time()
    print(f"Finished embedding {len(embedding_ids)} patents in {end_time - start_time} seconds")


def score_applications(db, citations, use_embedding=True):
    """Embed all the applications using the embedding model."""
    app_ids = citations.keys()
    emb = Embedder()
    scoring = {}

    if TEST:
        app_ids = app_ids[:TEST_SIZE]

    start_time = time()
    for app_id in app_ids:
        patents_cited = citations[app_id]

        if len(patents_cited) == 0:
            print(f"Application {app_id} has no cited patents, skipping...")
            continue
        
        elif len(patents_cited) > 10:
            print(f"Application {app_id} has more than 10 cited patents, skipping...")
            continue

        claims = db.get_application_claims_str(app_id)
        #check if claims are complete and not empty
        if check_claims(claims) is False:
            print(f"Application {app_id} has no claims, skipping...")
            continue

        emb.embed_documents([claims], [app_id])

        #score the application against the cited patents
        scores = emb.score_documents([claims], patents_cited)
        scoring[app_id] = scores

    end_time = time()

def main():
    db = Database(
        host="db",
        port=5432,
        database="patents_db",
        user="postgres",
        password="postgres"
    )
    embedder = Embedder()
    embed_patents(db, embedder)
    db.close()
    
if __name__ == "__main__":
    main()
