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

for app_id in citations.keys():
    print(f"Application ID: {app_id}")
    claims = get_app_claims(app_id)
    print(claims[:100])
    for patent_id in citations[app_id]:
        print(f"  Cited Patent ID: {patent_id}")
        claims = db.get_claims_str(patent_id)
        print(patent_id, claims[:100])

    