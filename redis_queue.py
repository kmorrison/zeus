import local_match_db
import redis
import matchlib
import datetime
import json

QUEUE_NAME = "zeus:parsed_queue"


def make_redis_client():
    return redis.Redis(host="localhost", port=6379, db=0)


def push_unparsed_match_to_queue(r, match, job_id):
    queue_payload = make_queue_payload(match, job_id)
    payload_json = json.dumps(queue_payload)
    r.lpush("zeus:parsed_queue", payload_json)


def make_queue_payload(match, job_id):
    queue_payload = {
        "match_id": match["match_id"],
        "job_id": job_id,
        "start_time": match["start_time"],
        "queued_time": datetime.datetime.now().timestamp(),
        "last_checked_time": 0,
        "num_retries": 0,
    }
    return queue_payload


def is_queue_empty(r):
    payload = r.llen(QUEUE_NAME)
    return payload == 0


def pop_match_json_from_queue(r):
    payload = r.rpop(QUEUE_NAME)
    if not payload:
        return None
    return json.loads(payload.decode())


def push_payload_for_retry(r, payload):
    payload["num_retries"] += 1
    payload["last_checked_time"] = datetime.datetime.now().timestamp()
    payload_json = json.dumps(payload)
    r.lpush(QUEUE_NAME, payload_json)


def requeue_payload(r, payload):
    payload_json = json.dumps(payload)
    r.lpush(QUEUE_NAME, payload_json)
