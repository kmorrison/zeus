import contextlib
import time
import local_match_db
import redis
import matchlib
import datetime
import json
import uuid

QUEUE_NAME = "zeus:parsed_queue"


def make_redis_client():
    return redis.Redis(host="localhost", port=6379, db=0)


def push_unparsed_match_to_queue(r, match, job_id, delay):
    queue_payload = make_queue_payload(match, job_id)
    payload_json = json.dumps(queue_payload)
    if not delay:
        r.lpush("zeus:parsed_queue", payload_json)
    else:
        delay_queue(r, "zeus:parsed_queue", payload_json, delay=delay)


@contextlib.contextmanager
def redis_lock(redis_client: redis.Redis, lockname, acquire_timeout=0.5):
    identifier = str(uuid.uuid4())
    lock_key = f"lock:{lockname}"
    end = time.time() + acquire_timeout
    acquired_lock = False
    while time.time() < end:
        acquired_lock = redis_client.setnx(lock_key, identifier)
        if acquired_lock:
            yield True
            break
        else:
            time.sleep(0.001)

    if not acquired_lock:
        yield False
        return

    redis_client.delete(lock_key)


def delay_queue(redis_client, queue_name, payload, delay=5):
    identifier = str(uuid.uuid4())
    item = json.dumps([identifier, queue_name, payload])
    redis_client.zadd("delayed:", {item: time.time() + delay})
    return identifier


def enqueue_delayed(redis_client):
    item = redis_client.zrange("delayed:", 0, 0, withscores=True)

    if not item or item[0][1] > time.time():
        time.sleep(0.01)
        return

    item = item[0][0]
    identifier, queue, payload = json.loads(item)

    with redis_lock(redis_client, identifier) as locked:
        if not locked:
            return
        if redis_client.zrem("delayed:", item):
            # TODO: log debug
            print("queueing job for processing")
            redis_client.rpush(queue, payload)


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
