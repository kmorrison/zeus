import argparse
import datetime
import pprint

import dateparser

import couchdb
import matchlib
import opendota
import parse_requester
import redis_queue


def populate_matches_from_start_time(start_time, num_matches=1000):
    matches_db = couchdb.get_matches_db()
    redis_client = redis_queue.make_redis_client()
    stats = dict(
        total_matches=0,
        fully_parsed_stored=0,
        parse_requested=0,
        already_stored=0,
        highwater_mark=datetime.datetime.fromtimestamp(start_time),
    )
    for match_info in matchlib.iterate_matches(start_time, limit=num_matches):
        match_data = opendota.get_match_by_id(match_info["match_id"])
        stats["total_matches"] += 1

        if str(match_data["match_id"]) in matches_db:
            stats["already_stored"] += 1
            continue

        stats["highwater_mark"] = datetime.datetime.fromtimestamp(
            match_data["start_time"]
        )

        if matchlib.is_fully_parsed(match_data):
            couchdb.store_match_to_db(matches_db, match_data)
            stats["fully_parsed_stored"] += 1
        else:
            parse_requester.request_parse_for_match(
                match_data,
                redis_client,
                delay=60,
            )
            stats["parse_requested"] += 1

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=str, default="3 hours ago")
    parser.add_argument("--use-highwater-db-time", action="store_true")
    parser.add_argument("--check-highwater-db-time", action="store_true")
    parser.add_argument("--num-matches", type=int, default=50)
    args = parser.parse_args()

    start_time = dateparser.parse(args.start).timestamp()
    with couchdb.dbcontext() as db:
        highwater_start_time = couchdb.get_last_match_by_start_time(db)["start_time"]
    
    if args.check_highwater_db_time:
        print(datetime.datetime.fromtimestamp(highwater_start_time))
        exit(0)

    if args.use_highwater_db_time:
        start_time = highwater_start_time

    stats = populate_matches_from_start_time(
        start_time,
        num_matches=args.num_matches,
    )
    pprint.pprint(stats)
