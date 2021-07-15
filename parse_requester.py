import redis_queue
import redis
import local_match_db
import matchlib
import opendota
import couchdb
import dateparser

def request_parses_for_matches():
    pass
    
def request_parse_for_match(match, redis_client):
    match_id = match['match_id']
    job_id = opendota.request_parse(match_id)['job_id']
    redis_queue.push_unparsed_match_to_queue(redis_client, match, job_id)

def check_if_match_is_parsed(match_payload, redis_client, matches_db):
    match_json = opendota.get_match_by_id(match_payload['match_id'])
    if matchlib.is_fully_parsed(match_json):
        couchdb.store_match_to_db(matches_db, match_json)
        return True

    else:
        redis_queue.push_payload_for_retry(redis_client, match_payload)
        return False

def request_parsing_for_unparsed_matches(unparsed_matches):
    redis_client = redis_queue.make_redis_client()
    for match in unparsed_matches:
        request_parse_for_match(match, redis_client)
    redis_client.disconnect()


def process_unparsed_match_queue():
    redis_client = redis_queue.make_redis_client()
    unparsed_matches = redis_queue.get_unparsed_matches(redis_client)
    while True:
        match_payload = redis_queue.pop_match_json_from_queue(redis_client)
        match_json = opendota.get_match_by_id(match_payload['match_id'])
        if matchlib.is_fully_parsed(match_json):
            couchdb.store_match_to_db(matches_db, match_json)
        else:
            queue_time = dateparser.parse(match_payload['queued_time'])
            if datetime.datetime.now() - queue_time > datetime.timedelta(minutes=5):
                continue
            if match_payload['num_retries'] > 4:
                continue
            redis_queue.push_payload_for_retry(redis_client, match_payload)

    redis_client.disconnect()

