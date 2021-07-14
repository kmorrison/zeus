import cloudant
import cloudant.database
from cloudant.query import Query

MATCHES_DBNAME = "zeus_matches"

def _ensure_db(client, dbname):
    if dbname not in client.all_dbs():
        db = client.create_database(dbname)
        print(f"Create new database {dbname}")
        assert db.exists()
        return db
    
    return client[dbname]


def get_client() -> cloudant.Cloudant:
    return cloudant.Cloudant(
        "admin", 
        "password", 
        url="http://127.0.0.1:5984", 
        connect=True,
    )

def get_matches_db(dbname=MATCHES_DBNAME) -> cloudant.database.CloudantDatabase:
    client = get_client()
    return _ensure_db(client, dbname)


def store_match_to_db(db: cloudant.database.CloudantDatabase, match: dict):
    match['_id'] = str(match['match_id'])
    document = db.create_document(match)
    assert document.exists()
    return document


def get_last_match_by_start_time(db):
    query = Query(
        db, 
        limit=1, 
        sort=[{'start_time': 'desc'}], 
        selector={'start_time': {'$gt': 0}},
    )
    result = query.result.all()
    assert len(result) == 1
    return result[0]

