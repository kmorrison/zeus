import requests
import json
import secret


# API_ROOT = 'https://api.opendota.com/api/matches/271145478?api_key=YOUR-API-KEY'
API_ROOT = "https://api.opendota.com/api"

# get/find matches

def generate_query(*heroes):
    """generates an SQL query where hero1+hero2 is vs hero3+hero4"""
    #  won't support 2v3's or 1v3's in the case of trilanes

    def select(*heroes): 
        """generates select statement for certain num of heroes"""
        select = f"SELECT"


        i = 0 #leave me be sir 
        for data in heroes:
            for hero in data: 
                if i == 0: 
                    select = select + f" player_matches.hero_id AS hero1, \n"
                else: 
                    select = select + f"player_matches{i}.hero_id AS hero{i+1}, \n"
                i = i+1
            i = 0
            for hero in data: 
                if i == 0: 
                    select = select + f"player_matches.player_slot AS ps1, \n"
                else: 
                    select = select + f"player_matches{i}.player_slot AS ps{i+1}, \n"
                i = i+1

        select = select + f"matches.match_id,\n"
        select = select + f"leagues.name leaguename\n"
        return select

    def join(*heroes): 
        """generates join statements for certain num of heroes"""
        join = f"FROM player_matches \n"
        i = 0
        for data in heroes: 
            for hero in data:
                if i == 0: 
                    i = i+1
                    continue
                else:
                    join = join + f"JOIN player_matches AS player_matches{i}\n"
                    join = join + f"ON player_matches.match_id = player_matches{i}.match_id\n"
                    i = i+1
        join = join + f"JOIN matches\n"
        join = join + f"ON player_matches.match_id = matches.match_id\n"
        join = join + f"JOIN leagues using(leagueid)\n"
        return join

    def where(*heroes): 
        """generates where statement for certain num of heroes"""
        i = 0
        where = f"WHERE"
        for data in heroes: 
            for hero in data: 
                if i == 0: 
                    where = where + f" player_matches.hero_id = {get_hero_id(hero)}\n"
                    i = i+1
                else: 
                    where = where + f"AND player_matches{i}.hero_id = {get_hero_id(hero)}\n"
                    i = i+1

        #probably need to pass in a timestamp or something at some point for the following
        where = where + f"AND matches.start_time >= extract(epoch FROM timestamp '2018-10-01T06:53:44.537Z')\n"
        return where

    def teams(*heroes): 
        """adds onto where statement and specifies which team each hero is on, hero1+hero2 =teamA, hero3+hero4 = teamB"""
        i = 0
        teams = ""
        for data in heroes: 
            for hero in data: 
                if i == 0: 
                    i = i+1
                    continue
                elif i == 1: 
                    teams = teams + f"AND abs(player_matches.player_slot - player_matches1.player_slot) < 6\n"
                    i = i+1
                elif i == 2: 
                    teams = teams + f"AND abs(player_matches.player_slot - player_matches2.player_slot) > 123\n"
                    i = i+1
                elif i == 3: 
                    teams = teams + f"AND abs(player_matches2.player_slot - player_matches3.player_slot) < 6\n"
                    teams = teams + f"AND abs(player_matches1.player_slot - player_matches3.player_slot) > 123\n"
                    i = i+1
        teams = teams + "ORDER BY matches.match_id NULLS LAST LIMIT 200"
        return teams
        
    return select(heroes) + join(heroes) + where(heroes) + teams(heroes)


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
        f"{API_ROOT}/explorer", params=dict(api_key=secret.OPENDOTA_API_KEY, sql=query)
    )
    return response.json()


def get_matches(hero1, hero2):

    """returns list of pro match ids played between two heroes"""

    query_response = make_query(hero1, hero2)
    match_list = query_response["rows"]  #list of dictionaries for some reason
    result = []

    for match in match_list:
        return [match['match_id'] for match in match_list]

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