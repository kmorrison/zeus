import requests
import json
import json.decoder
import secret
import time
import functools


API_ROOT = "https://api.opendota.com/api"

# get/find matches


def opendota_retry(func):
    @functools.wraps(func)
    def with_retry(*args, **kwargs):
        for _ in range(3):
            try:
                resp = func(*args, **kwargs)
                return resp
            except json.decoder.JSONDecodeError:
                time.sleep(10)
    return with_retry


@opendota_retry
def request_parse(match_id):
    response = requests.post(
        f"{API_ROOT}/request/{match_id}",
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    return response.json()

def check_job(job_id):
    response = requests.get(
        f"{API_ROOT}/request/{job_id}",
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    return response

def all_heroes():
    return load_hero_list().values()


def find_hero(heroname):
    for hero in load_hero_list().values():
        if hero["localized_name"] == heroname:
            return hero
    print("Didn't find the hero")
    return


def find_hero_by_id(hero_id):
    return load_hero_list().get(str(hero_id))


def find_hero_name_by_id(hero_id):
    return load_hero_list().get(str(hero_id))["localized_name"]


def get_hero_id(heroname):
    return find_hero(heroname)["id"]


def get_hero_list():
    response = requests.get(
        f"{API_ROOT}/heroes", params=dict(api_key=secret.OPENDOTA_API_KEY)
    )
    return response.json()


@opendota_retry
def get_match_by_id(match_id):
    response = requests.get(
        f"{API_ROOT}/matches/{match_id}",
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    return response.json()


def get_item_table():
    response = requests.get(
        f"{API_ROOT}/constants/items",
        params=dict(
            api_key=secret.OPENDOTA_API_KEY,
        ),
    )
    return response.json()


@opendota_retry
def get_heroes_table():
    response = requests.get(
        f"{API_ROOT}/constants/heroes",
        params=dict(
            api_key=secret.OPENDOTA_API_KEY,
        ),
    )
    return response.json()

@opendota_retry
def get_abilities():
    response = requests.get(
        f"{API_ROOT}/constants/abilities",
        params=dict(
            api_key=secret.OPENDOTA_API_KEY,
        ),
    )
    return response.json()

@opendota_retry
def get_ability_ids():
    response = requests.get(
        f"{API_ROOT}/constants/ability_ids",
        params=dict(
            api_key=secret.OPENDOTA_API_KEY,
        ),
    )
    return response.json()

@opendota_retry
def get_matchups(hero_id):
    response = requests.get(
        f"{API_ROOT}/heroes/{hero_id}/matchups",
        params=dict(
            api_key=secret.OPENDOTA_API_KEY,
        ),
    )
    return response.json()


@opendota_retry
def query_explorer(query):
    response = requests.get(
        f"{API_ROOT}/explorer",
        params=dict(
            api_key=secret.OPENDOTA_API_KEY,
            sql=query,
        ),
    )
    return response.json()


@opendota_retry
def parsed_matches(last_match_id=None):
    params = dict(
        api_key=secret.OPENDOTA_API_KEY,
    )
    if last_match_id is not None:
        params["less_than_match_id"] = last_match_id
    response = requests.get(
        f"{API_ROOT}/parsedMatches",
        params=params,
    )
    return response.json()


def make_example_call():
    response = requests.get(
        f"{API_ROOT}/matches/5705824607",
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    return response.json()


def load_hero_list():
    with open("hero_dict.json") as f:
        return json.loads(f.read())


if __name__ == "__main__":
    pass
