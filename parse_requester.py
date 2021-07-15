import argparse
import datetime
import random
import time

import couchdb
import local_match_db
import matchlib
import opendota
import redis_queue


def request_parse_for_match(match, redis_client):
    match_id = match['match_id']
    print(f'Queueing {match_id} for parsing')
    job_id = opendota.request_parse(match_id)['job']['jobId']
    redis_queue.push_unparsed_match_to_queue(redis_client, match, job_id)


def request_parsing_for_unparsed_matches(unparsed_matches):
    redis_client = redis_queue.make_redis_client()
    for match in unparsed_matches:
        request_parse_for_match(match, redis_client)


def process_unparsed_match_queue():
    redis_client = redis_queue.make_redis_client()
    empty_count = 0
    while True:
        match_payload = redis_queue.pop_match_json_from_queue(redis_client)
        if match_payload is None:
            print("Sleeping because pulled nothing")
            time.sleep(10)
            empty_count += 1
            continue

        print(match_payload)
        empty_count = 0

        if (
            datetime.datetime.now() - datetime.datetime.fromtimestamp(match_payload['last_checked_time'])
            < datetime.timedelta(minutes=1)
        ):
            redis_queue.requeue_payload(redis_client, match_payload)
            continue

        match_json = opendota.get_match_by_id(match_payload['match_id'])
        if matchlib.is_fully_parsed(match_json):
            couchdb.store_match_to_db(couchdb.get_matches_db(), match_json)
        else:
            queue_time = datetime.datetime.fromtimestamp(match_payload['queued_time'])
            if datetime.datetime.now() - queue_time > datetime.timedelta(minutes=5):
                continue
            if match_payload['num_retries'] > 4:
                continue
            redis_queue.push_payload_for_retry(redis_client, match_payload)

        if redis_queue.is_queue_empty(redis_client):
            print("Sleeping because queue is empty")
            time.sleep(10)
            empty_count += 1
        
        if empty_count > 10:
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('--process-queue', action="store_true")
    parser.add_argument('--populate-queue', action="store_true")
    parser.add_argument('--max-matches-to-queue', type=int, default=5)

    args = parser.parse_args()
    if args.process_queue:
        process_unparsed_match_queue()

    if args.populate_queue:
        db = couchdb.get_matches_db()
        unparsed_matches = local_match_db.get_all_unparsed_matches('moneydb')
        actually_unparsed_matches = [
            match
            for match in unparsed_matches
            if not couchdb.match_exists_in_db(db, match['match_id'])
        ]
        matches_to_parse = actually_unparsed_matches[:args.max_matches_to_queue]

        #request_parsing_for_unparsed_matches(matches_to_parse)