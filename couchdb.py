import contextlib
import cloudant
import cloudant.database
from cloudant import couchdb as couch
from cloudant.query import Query
import argparse
import datetime
import dateparser

import opendota

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


def get_matches_db(dbname=MATCHES_DBNAME) -> cloudant.database.CouchDatabase:
    client = get_client()
    return _ensure_db(client, dbname)


def match_exists_in_db(db, match_id):
    return str(match_id) in db


def get_all_parsed_matches_more_recent_than(
    db: cloudant.database.CouchDatabase, start_time
):
    query = db.get_query_result(
        selector={"start_time": {"$gt": start_time}},
        sort=["start_time"],
    )
    # This is a paging query so just return it whole instead of loading it
    return query


def get_all_matches_with_hero_after_start_time(
    db: cloudant.database.CouchDatabase, start_time, hero_names=None
):

    if hero_names is None:
        hero_names = []

    hero_names = [name for name in hero_names if name]
    heroes = [opendota.find_hero(name) for name in hero_names]
    query_dict = {
        "selector": {
            "start_time": {"$gt": start_time},
        },
        "sort": ["start_time"],
    }
    if heroes:
        if len(heroes) == 1:
            query_dict["selector"]["players"] = {
                "$elemMatch": {"hero_id": heroes[0]["id"]},
            }
        else:
            selector = [
                {"players": {"$elemMatch": {"hero_id": hero["id"]}}} for hero in heroes
            ]
            query_dict["selector"]["$and"] = selector
    query = db.get_query_result(**query_dict)
    return query


def store_match_to_db(db: cloudant.database.CouchDatabase, match: dict):
    match["_id"] = str(match["match_id"])
    document = db.create_document(match)
    assert document.exists()
    return document


def get_last_match_by_start_time(db):
    query = Query(
        db,
        limit=1,
        sort=[{"start_time": "desc"}],
        selector={"start_time": {"$gt": 0}},
    )
    result = query.result.all()
    assert len(result) == 1
    return result[0]

def get_num_matches_since_time(db, time):
    selector={"start_time": {"$gt": time}}
    res = db.get_query_result(selector)
    print(time)

    return len([_ for _ in res])


@contextlib.contextmanager
def dbcontext(dbname=MATCHES_DBNAME):
    with couch(
        "admin",
        "password",
        url="http://127.0.0.1:5984",
    ) as couch_client:
        yield couch_client[dbname]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--display-stats", action="store_true")
    parser.add_argument("--start", type=str, default="")
    args = parser.parse_args()
    start_time = dateparser.parse(args.start).timestamp()

    if args.display_stats:
        matches_db = get_matches_db()
        if not args.start:
            all_docs = matches_db.all_docs()
            print(f"Num fully parsed matches: {all_docs['total_rows']}")
        else:
            print(f"Num matches since input-time: {get_num_matches_since_time(matches_db, start_time)}")
        print(
            f"Last match start_time {datetime.datetime.fromtimestamp(get_last_match_by_start_time(matches_db)['start_time'])}"
        )
