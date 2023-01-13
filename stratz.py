import secret
import json
import copy
import math
import requests
import itertools
import opendota
import time
import more_itertools
import pickle

url = "https://api.stratz.com/graphql"
hero_stats_query = """    {}: matchUp(heroId: {}, take: 137, matchLimit: 200){{
      with {{
        heroId1
        heroId2
        week
        bracketBasicIds
        matchCount
        synergy
        winCount
        winRateHeroId1
        winRateHeroId2
        winsAverage
      }},
      vs {{
        heroId1
        heroId2
        week
        bracketBasicIds
        matchCount
        synergy
        winCount
        winRateHeroId1
        winRateHeroId2
        winsAverage
      }},
    }},"""

query = """
query {{
  heroStats{{
    {}
  }}
}}
"""

HERO_MATHCUPS_FILENAME = "hero_matchups.json"

def do_query(query):
    headers = {"Authorization": f"Bearer {secret.STRATZ_API_KEY}"}
    resp = requests.post(url, json={'query': query}, headers=headers)
    return resp

def build_query(heroes):
    hero_query_strings = [hero_stats_query.format("hero" + str(hero["id"]), str(hero["id"])) for hero in heroes]
    all_heroes_query = '\n'.join(hero_query_strings)
    return query.format(all_heroes_query)

def build_hero_matchups():
    heroes = opendota.load_hero_list().values()
    matchup_by_heroes = {}
    
    for some_heroes in more_itertools.chunked(heroes, 20):
        query = build_query(some_heroes)
        resp = do_query(query)
        if resp.status_code != 200:
            raise Exception("Query failed to run by returning code of {}".format(resp.status_code))

        response_body = resp.json()

        matchup_by_heroes.update(response_body["data"]["heroStats"])

        time.sleep(0.1) # Be nice to stratz API, rate limiting is a little aggressive


    return matchup_by_heroes

def save_hero_matchups(filename=HERO_MATHCUPS_FILENAME):
    response_body = build_hero_matchups()
    with open(filename, 'w') as f:
        f.write(json.dumps(response_body))

def load_hero_matchups(filename=HERO_MATHCUPS_FILENAME):
    with open(filename, 'r') as f:
        return json.loads(f.read())

def make_and_save_fixed_matchups():
    with_mtx, vs_mtx = fix_winrates(*make_with_vs_matrix())

    with open('fixed_hero_matchups.pkl', 'wb') as f:
        pickle.dump({'with': with_mtx, 'vs': vs_mtx}, f)

def load_fixed_matchups(filename='fixed_hero_matchups.pkl'):
    with open(filename, 'rb') as f:
        data = pickle.load(f)
        return data['with'], data['vs']


def make_with_vs_matrix():
    raw_query_data = load_hero_matchups()
    ally_matrix = {}
    enemy_matrix = {}
    for hero in opendota.load_hero_list().values():
        hero_id = hero['id']

        specific_ally_matrix = raw_query_data[f'hero{hero_id}'][0]['with']
        for hero_pair_info in specific_ally_matrix:
            ally_matrix.setdefault(hero_id, {})
            ally_matrix[hero_id][hero_pair_info['heroId2']] = hero_pair_info

        specific_enemy_matrix = raw_query_data[f'hero{hero_id}'][0]['vs']
        for hero_pair_info in specific_enemy_matrix:
            enemy_matrix.setdefault(hero_id, {})
            enemy_matrix[hero_id][hero_pair_info['heroId2']] = hero_pair_info

    return ally_matrix, enemy_matrix

def check_mtx(mtx, hero_ids, flip_synergy=False):
    missing_one_way = []
    missing_two_way = []
    inconsistent = []
    multiplier = 1
    if flip_synergy:
        multiplier = -1
    for (id1, id2) in itertools.combinations(hero_ids, 2):
        with_row = mtx[id1]
        with2_row = mtx[id2]
        if id2 not in with_row and id1 not in with2_row:
            missing_two_way.append((id1, id2))
        elif id2 not in with_row:
            missing_one_way.append((id1, id2))
        elif id1 not in with2_row:
            missing_one_way.append((id2, id1))
        elif with_row[id2]['synergy'] != (multiplier * with2_row[id1]['synergy']):
            inconsistent.append((id1, id2))
    return missing_one_way, missing_two_way, inconsistent

def check_winrate_matrix_integrity(with_mtx, vs_mtx):
    hero_ids = set([h['id'] for h in opendota.load_hero_list().values()])
    with_one_way, with_two_way, with_inconsistent = check_mtx(with_mtx, hero_ids)
    vs_one_way, vs_two_way, vs_inconsistent = check_mtx(vs_mtx, hero_ids, flip_synergy=True)
    print(f'Total heroes {len(hero_ids) ** 2}')
    print('Missing with_mtx one way', len(with_one_way))
    print('Missing with_mtx two way', len(with_two_way))
    print('Inconsistent with_mtx pairs', len(with_inconsistent))
    print('Missing vs_mtx one way', len(vs_one_way))
    print('Missing vs_mtx two way', len(vs_two_way))
    print('Inconsistent vs_mtx pairs', len(vs_inconsistent))

def synergy(winrate1, winrate2, observed_winrate):
    return round((observed_winrate - (-.48 + (.98 * winrate1) + (.98 * winrate2))) * 100, 3)

def counters(winrate1, winrate2, observed_winrate):
    return round((observed_winrate - (.5 + winrate1 - winrate2)) * 100, 3)

def fix_mtx(with_mtx, hero_winrates, synergy_func):
    new_mtx = {}
    for hero in opendota.all_heroes():
        with_row = with_mtx[hero['id']]
        winrate = hero_winrates[hero['id']]
        hero_id = int(hero['id'])
        new_mtx.setdefault(hero_id, {})
        for other_hero in with_row.values():
            other_hero_id = int(other_hero['heroId2'])
            other_hero_winrate = hero_winrates[other_hero_id]
            synergy = synergy_func(winrate, other_hero_winrate, other_hero['winsAverage'])
            new_mtx[hero_id][other_hero_id] = copy.deepcopy(other_hero)
            new_mtx[hero_id][other_hero_id]['synergy'] = synergy
            new_mtx[hero_id][other_hero_id]['winRateHeroId1'] = winrate
            new_mtx[hero_id][other_hero_id]['winRateHeroId2'] = other_hero_winrate

    return new_mtx


def fix_winrates(with_mtx, vs_mtx):
    hero_winrates = {}
    for hero in opendota.all_heroes():
        with_row = with_mtx[hero['id']]
        matches = sum([row['matchCount'] for row in with_row.values()])
        wins = sum([row['winCount'] for row in with_row.values()])
        overall_winrate = wins / matches
        hero_winrates[hero['id']] = overall_winrate
    
    fixed_with_mtx = fix_mtx(with_mtx, hero_winrates, synergy)
    fixed_vs_mtx = fix_mtx(vs_mtx, hero_winrates, counters)
    return fixed_with_mtx, fixed_vs_mtx


def check_hero(hero_id, with_mtx, vs_mtx):
    vs_row = vs_mtx[hero_id]
    matches = sum([row['matchCount'] for row in vs_row.values()])
    wins = sum([row['winCount'] for row in vs_row.values()])
    overall_winrate = wins / matches
    reported_winrates = [row['winRateHeroId1'] for row in vs_row.values()]
    assert len(list(set(reported_winrates))) == 1
    print(overall_winrate, reported_winrates[0])
    for other_hero in vs_row.values():
        observed_synergy = counters(
            reported_winrates[0], 
            other_hero['winRateHeroId2'], 
            other_hero['winCount'] / other_hero['matchCount'],
        )
        print(
            other_hero['heroId2'], 
            other_hero['synergy'], 
            observed_synergy,
            other_hero['synergy'] - observed_synergy,
        )


if __name__ == '__main__':
    print(f'saving hero matchups to {HERO_MATHCUPS_FILENAME}')
    #save_hero_matchups(HERO_MATHCUPS_FILENAME)
    print(f'saved hero matchups to {HERO_MATHCUPS_FILENAME}')

    with_mtx, vs_mtx = make_with_vs_matrix()
    #check_winrate_matrix_integrity(with_mtx, vs_mtx)
    #make_and_save_fixed_matchups()
    with_mtx, vs_mtx = load_fixed_matchups()
    check_winrate_matrix_integrity(with_mtx, vs_mtx)
    #check_hero(61, with_mtx, vs_mtx)