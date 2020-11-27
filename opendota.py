import requests
import json
import secret


# API_ROOT = 'https://api.opendota.com/api/matches/271145478?api_key=YOUR-API-KEY'
API_ROOT = "https://api.opendota.com/api"

# get/find matches


# def find_matches_by_hero():

def make_query(hero1, hero2): 
    query = f"""SELECT player_matches.hero_id AS hero1,
         player_matches1.hero_id AS hero2,
         player_matches.player_slot AS ps1,
         player_matches1.player_slot AS ps2,
         matches.match_id,
         leagues.name leaguename
    FROM player_matches
    JOIN player_matches AS player_matches1
    ON player_matches.match_id = player_matches1.match_id
    JOIN matches
    ON player_matches.match_id = matches.match_id
    JOIN leagues using(leagueid)    
    WHERE player_matches.hero_id = {get_hero_id(hero1)}
        AND player_matches1.hero_id = {get_hero_id(hero2)}
        AND matches.start_time >= extract(epoch
    FROM timestamp '2020-10-23T06:53:44.537Z')
        AND abs(player_matches.player_slot - player_matches1.player_slot) > 123
    ORDER BY  matches.match_id NULLS LAST LIMIT 200"""

    response = requests.get(
        f"{API_ROOT}/explorer", params=dict(api_key=secret.OPENDOTA_API_KEY, sql = query)
    )
    return response.json()
    
##returns list of pro match ids played between two opposing heroes
def get_matches(hero1, hero2): 
    query_response = make_query(hero1, hero2)
    match_list = query_response['rows'] ##list of dictionaries for some reason
    result = []

    for match in match_list: 
        result.append(match['match_id'])

    return result


def find_hero(heroname):
    for hero in load_hero_list():
        if hero["localized_name"] == heroname:
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
    main()



