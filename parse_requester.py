import argparse
import datetime
import json
import random
import time

import couchdb
import matchlib
import opendota
import redis_queue


def request_parse_for_match(match, redis_client, delay=60):
    match_id = match["match_id"]
    print(f"Queueing {match_id} for parsing")
    job_id = opendota.request_parse(match_id)["job"]["jobId"]
    redis_queue.push_unparsed_match_to_queue(
        redis_client,
        match,
        job_id,
        delay=delay,
    )


def request_parsing_for_unparsed_matches(unparsed_matches, delay=60):
    redis_client = redis_queue.make_redis_client()
    for match in unparsed_matches:
        request_parse_for_match(match, redis_client, delay=delay)


def process_unparsed_match_queue():
    redis_client = redis_queue.make_redis_client()
    while True:
        redis_queue.enqueue_delayed(redis_client)
        match_payload = redis_queue.pop_match_json_from_queue(redis_client)
        if match_payload is None:
            print("Sleeping because pulled nothing")
            time.sleep(10)
            continue

        print(match_payload)

        if datetime.datetime.now() - datetime.datetime.fromtimestamp(
            match_payload["last_checked_time"]
        ) < datetime.timedelta(minutes=1):
            redis_queue.requeue_payload(redis_client, match_payload)
            continue

        match_json = opendota.get_match_by_id(match_payload["match_id"])
        if matchlib.is_fully_parsed(match_json):
            couchdb.store_match_to_db(couchdb.get_matches_db(), match_json)
        else:
            queue_time = datetime.datetime.fromtimestamp(match_payload["queued_time"])
            if datetime.datetime.now() - queue_time > datetime.timedelta(minutes=5):
                continue
            if match_payload["num_retries"] > 4:
                continue
            redis_queue.delay_queue(
                redis_client,
                "zeus:parsed_queue",
                json.dumps(match_payload),
                delay=120,
            )
            time.sleep(0.01)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("--process-queue", action="store_true")
    parser.add_argument("--populate-queue", action="store_true")
    parser.add_argument("--max-matches-to-queue", type=int, default=5)

    args = parser.parse_args()
    if args.process_queue:
        process_unparsed_match_queue()
