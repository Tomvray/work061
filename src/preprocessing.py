from database import Database

def generate_patent_citation_pairs(db):
    """Generate pairs of patents where one cites the other. Returns a list of tuples (citing_patent_id, cited_patent_id)"""
    citations = {}
    app_ids_with_citations = db.get_app_citations()
    app_ids = db.get_application_ids()
    

    print(app_ids_with_citations[:10])
    print(app_ids[:10])
    print(f"Number of application IDs with citations: {len(app_ids_with_citations)}")
    print(f"Number of application IDs in database: {len(app_ids)}")
    

    app_ids_to_process = set(app_ids).intersection(set(app_ids_with_citations))
    print(f"Number of application IDs to process: {len(app_ids_to_process)}")

    #generate citation pairs that are in the claims database and application database
    claims_ids = db.get_claims_ids()
    print(f"Number of claims IDs: {len(claims_ids)}")
    for app_id in app_ids_to_process:
        cited_patents = db.get_patents_cited(app_id)
        cited_patents_to_process = []
        print(f"Processing app_id {app_id} with cited patents: {cited_patents}")
        for cited in cited_patents:
            if cited in claims_ids:
                cited_patents_to_process.append(cited)
        if len(cited_patents_to_process) > 0:
            citations[app_id] = cited_patents_to_process
        print(f"App ID {app_id} cites {len(cited_patents_to_process)} patents that are in the claims database.")
    return citations


def split_data_set(db):
    val_year = 2018
    test_year = 2017
    train_years = list(range(2008, 2017))

if __name__=="__main__":
    from database import Database

    db = Database(
        host="db",
        port=5432,
        database="patents_db",
        user="postgres",
        password="postgres"
    )
    citation_pairs = generate_patent_citation_pairs(db)
    print(len(citation_pairs))
    print(citation_pairs)

    #save citation pairs to a json file
    import json
    with open("citation_pairs.json", "w") as f:
        json.dump(citation_pairs, f)


    db.close()
