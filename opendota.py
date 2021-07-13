import requests
import json
import secret


API_ROOT = "https://api.opendota.com/api"

# get/find matches

def find_hero(heroname):
    for hero in load_hero_list():
        if hero["localized_name"] == heroname:
            return hero
    print("Didn't find the hero")
    return


def find_hero_by_id(hero_id):
    for hero in load_hero_list():
        if hero["id"] == hero_id:
            return hero
    print("Didn't find the hero")
    return


def get_hero_id(heroname):
    return find_hero(heroname)["id"]


def get_hero_list():
    response = requests.get(
        f"{API_ROOT}/heroes", params=dict(api_key=secret.OPENDOTA_API_KEY)
    )
    return response.json()


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


def make_example_call():
    response = requests.get(
        f"{API_ROOT}/matches/5705824607",
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    return response.json()


def load_hero_list():
    with open("hero_dict.json") as f:
        return json.loads(f.read())