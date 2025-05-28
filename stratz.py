import json
import copy
import itertools
import time
import pickle
import hashlib
import os
import functools
from pprint import pprint

import more_itertools
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate

import opendota
import secret
from ad2l import scrape_team
from fuzzy_hero_names import match


url = "https://api.stratz.com/graphql"
hero_stats_query = """    {}: matchUp(heroId: {}, bracketBasicIds: DIVINE_IMMORTAL, take: 137, matchLimit: 200){{
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

def cached(func):
    """
    Decorator to cache function output to a JSON file based on function name and md5 of input args.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Build cache key
        key_str = func.__name__ + repr((args, kwargs))
        key_hash = hashlib.md5(key_str.encode('utf-8')).hexdigest()
        filename = f"query_cache/{func.__name__}_{key_hash}.json"

        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        result = func(*args, **kwargs)
        with open(filename, 'w') as f:
            json.dump(result, f)
        return result
    return wrapper

HERO_MATHCUPS_FILENAME = "hero_matchups.json"

def weeks_since_jan_1_1970(weeks_ago=0):
    # Calculate the number of weeks since January 1, 1970
    epoch = time.mktime(time.strptime("1970-01-01", "%Y-%m-%d"))
    now = time.time()
    now = now - (weeks_ago * 7 * 24 * 60 * 60)  # Subtract weeks_ago in seconds
    return int((now - epoch) / (7 * 24 * 60 * 60))  # Convert seconds to weeks

def now_minus_weeks(weeks_ago=0):
    # Calculate the current time minus a number of weeks
    now = time.time()
    return int(now - (weeks_ago * 7 * 24 * 60 * 60))


def do_query(query):
    headers = {"Authorization": f"Bearer {secret.STRATZ_API_KEY}", "User-Agent": "STRATZ_API"}
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
            raise Exception(f"Query failed to run by returning code of {resp.status_code}: {resp.text}")

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

def get_versus_values_for_heroes(hero_list):
    """
    Queries the Stratz API for the 'versus' values of a specified list of heroes.

    Args:
        hero_list (list): A list of hero dictionaries, each containing at least the 'id' key.

    Returns:
        dict: A dictionary containing the 'versus' data for the specified heroes.
    """
    versus_matrix = {}
    for some_heroes in more_itertools.chunked(hero_list, 20):  # Chunk to avoid API limits
        query = build_query(some_heroes)
        resp = do_query(query)
        if resp.status_code != 200:
            raise Exception(f"Query failed with status code {resp.status_code}: {resp.text}")

        response_body = resp.json()
        hero_stats = response_body["data"]["heroStats"]

        for hero_id, hero_data in hero_stats.items():
            versus_matrix[hero_id] = hero_data[0]["vs"]

        time.sleep(0.1)  # Be nice to the API

    return versus_matrix

def get_versus_matrix(hero_list):
    """
    Queries the Stratz API for the 'versus' values of a specified list of heroes
    and builds a nested dictionary where dict[i][j] contains matchup information
    for hero_id i versus hero_id j.

    Args:
        hero_list (list): A list of hero dictionaries, each containing at least the 'id' key.

    Returns:
        dict: A nested dictionary where dict[i][j] contains matchup data for hero_id i versus hero_id j.
    """
    versus_matrix = {}
    for some_heroes in more_itertools.chunked(hero_list, 20):  # Chunk to avoid API limits
        query = build_query(some_heroes)
        resp = do_query(query)
        if resp.status_code != 200:
            raise Exception(f"Query failed with status code {resp.status_code}: {resp.text}")

        response_body = resp.json()
        hero_stats = response_body["data"]["heroStats"]

        for hero_data in hero_stats.values():
            for matchup in hero_data[0]["vs"]:
                hero_id = int(matchup["heroId1"])  # Ensure hero_id is an integer
                versus_matrix.setdefault(hero_id, {})
                opponent_id = matchup["heroId2"]
                versus_matrix[hero_id][opponent_id] = matchup

        time.sleep(0.1)  # Be nice to the API

    return versus_matrix

def get_draft_prep_matrix(hero_list):
    """
    Builds a draft preparation matrix (NxN) where the only values of i and j are
    those present in the input hero list.

    Args:
        hero_list (list): A list of hero dictionaries, each containing at least the 'id' key.

    Returns:
        dict: A nested dictionary where dict[i][j] contains matchup data for hero_id i versus hero_id j,
              limited to the heroes in the input list.
    """
    # Get the full versus matrix for the input heroes
    full_versus_matrix = get_versus_matrix(hero_list)
    
    # Extract only the heroes in the input list to form an NxN matrix
    hero_ids = [hero['id'] for hero in hero_list]
    draft_prep_matrix = {
        i: {j: full_versus_matrix[i][j] for j in hero_ids if j in full_versus_matrix.get(i, {})}
        for i in hero_ids
    }
    
    return draft_prep_matrix

def get_draft_prep_matrix_nxm(our_heroes, enemy_heroes):
    """
    Builds a draft preparation matrix (NxM) where the rows are our heroes and the columns are enemy heroes.

    Args:
        our_heroes (list): A list of hero dictionaries for our team, each containing at least the 'id' key.
        enemy_heroes (list): A list of hero dictionaries for the enemy team, each containing at least the 'id' key.

    Returns:
        dict: A nested dictionary where dict[i][j] contains matchup data for hero_id i versus hero_id j.
    """
    # Get the full versus matrix for all heroes in both lists
    all_heroes = our_heroes + enemy_heroes
    full_versus_matrix = get_versus_matrix(all_heroes)

    # Extract only the matchups between our heroes and enemy heroes
    our_hero_ids = [hero['id'] for hero in our_heroes]
    enemy_hero_ids = [hero['id'] for hero in enemy_heroes]
    draft_prep_matrix = {
        i: {j: full_versus_matrix[i][j] for j in enemy_hero_ids if j in full_versus_matrix.get(i, {})}
        for i in our_hero_ids
    }

    return draft_prep_matrix

def print_draft_prep_matrix(row_heroes, col_heroes, draft_prep_matrix):
    """
    Prints the draft preparation matrix in a tabular format using the tabulate library.

    Args:
        row_heroes (list): A list of hero dictionaries for the rows, each containing at least the 'id' and 'localized_name' keys.
        col_heroes (list): A list of hero dictionaries for the columns, each containing at least the 'id' and 'localized_name' keys.
        draft_prep_matrix (dict): The NxM draft preparation matrix.
    """
    # Extract hero names for headers and rows
    row_hero_names = {hero['id']: hero['localized_name'] for hero in row_heroes}
    col_hero_names = {hero['id']: hero['localized_name'] for hero in col_heroes}
    headers = ["Hero"] + [col_hero_names[hero_id] for hero_id in col_hero_names]

    # Build rows for the table
    rows = []
    for hero_id, matchups in draft_prep_matrix.items():
        row = [row_hero_names[hero_id]]  # Start with the hero name
        for opponent_id in col_hero_names:
            if opponent_id in matchups:
                row.append(matchups[opponent_id].get("synergy", "N/A"))  # Example: Display synergy
            else:
                row.append("N/A")
        rows.append(row)

    # Print the table
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def print_draft_prep_matrix_with_winrates(row_heroes, col_heroes, draft_prep_matrix, global_winrates):
    """
    Prints the draft preparation matrix in a tabular format using the tabulate library,
    displaying the winrate in the matchup and how it differs from the global winrate.

    Args:
        row_heroes (list): A list of hero dictionaries for the rows, each containing at least the 'id' and 'localized_name' keys.
        col_heroes (list): A list of hero dictionaries for the columns, each containing at least the 'id' and 'localized_name' keys.
        draft_prep_matrix (dict): The NxM draft preparation matrix.
        global_winrates (dict): A dictionary mapping hero IDs to their global winrate.
    """
    # Extract hero names for headers and rows
    row_hero_names = {hero['id']: hero['localized_name'] for hero in row_heroes}
    col_hero_names = {hero['id']: hero['localized_name'] for hero in col_heroes}
    headers = ["Hero"] + [col_hero_names[hero_id] for hero_id in col_hero_names]

    # Build rows for the table
    rows = []
    for hero_id, matchups in draft_prep_matrix.items():
        row = [row_hero_names[hero_id]]  # Start with the hero name
        for opponent_id in col_hero_names:
            if opponent_id in matchups:
                matchup_data = matchups[opponent_id]
                winrate = (matchup_data['winCount'] / matchup_data['matchCount']) * 100 if matchup_data['matchCount'] > 0 else 0
                global_winrate = global_winrates.get(hero_id, 0)
                diff = winrate - global_winrate
                row.append(f"{winrate:.1f}% ({diff:+.1f}%)")
            else:
                row.append("N/A")
        rows.append(row)

    # Print the table
    print(tabulate(rows, headers=headers, tablefmt="grid"))

def calculate_global_winrates(full_versus_matrix):
    """
    Calculates the global winrate for each hero based on the full versus matrix.

    Args:
        full_versus_matrix (dict): The full versus matrix containing matchup data for all heroes.

    Returns:
        dict: A dictionary mapping hero IDs to their global winrate.
    """
    global_winrates = {}
    for hero_id, matchups in full_versus_matrix.items():
        total_matches = sum([data['matchCount'] for data in matchups.values()])
        print(f"Total matches for hero {hero_id}: {total_matches}")
        total_wins = sum([data['winCount'] for data in matchups.values()])
        global_winrates[hero_id] = (total_wins / total_matches) * 100 if total_matches > 0 else 0
    return global_winrates

@cached
def query_players(player_ids):
    """
    Queries the Stratz API for player information based on a list of player IDs.

    Args:
        player_ids (list): A list of Stratz player IDs.

    Returns:
        list: A list of dictionaries containing player information.
    """
    # Define the GraphQL query
    player_query = """
query ($playerId: Long!) {
  player(steamAccountId: $playerId) {
    steamAccountId
    matchCount
    winCount
    lastMatchDate
    activity {
      activity
    }
    simpleSummary {
      matchCount
      heroes {
        heroId
        winCount
        lossCount
      }
    }
    matches(request: {take: 25, playerList: SINGLE}){
      statsDateTime
      players {
        steamAccountId
        matchId
        heroId
        hero {
          id
          name
          shortName
          gameVersionId
        }
        lane
        imp
      }
    }
  }
}
    """

    results = []

    for player_id in player_ids:
        # Prepare the variables for the query
        variables = {"playerId": player_id}

        # Make the request to the Stratz API
        headers = {"Authorization": f"Bearer {secret.STRATZ_API_KEY}", "User-Agent": "STRATZ_API"}
        response = requests.post(url, json={"query": player_query, "variables": variables}, headers=headers)

        if response.status_code != 200:
            raise Exception(f"Query failed with status code {response.status_code}: {response.text}")

        # Parse the response JSON
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL query returned errors: {data['errors']}")

        results.append(data["data"]["player"])
        time.sleep(0.2)

    return results

def print_report(heroes, their_heroes):
    # Build the full versus matrix
    full_versus_matrix = get_versus_matrix(heroes)

    # Calculate global winrates
    global_winrates = calculate_global_winrates(full_versus_matrix)

    # If, for certain heroes, the number of matches is below a threshold, let's go back to stratz and add the previous week's matches
    supplemental_heroes = [hero for hero in heroes if sum(hero2["matchCount"] for hero2 in full_versus_matrix[hero['id']].values()) < 5000]

    # Build the draft preparation matrix
    draft_prep_matrix = get_draft_prep_matrix_nxm(heroes, their_heroes)

    # Print the matrix in tabular format with winrates
    print_draft_prep_matrix_with_winrates(heroes, their_heroes, draft_prep_matrix, global_winrates)

def count_recent_heroes_per_player(player_infos, months=3):
    """
    Counts the number of times each hero appears in recent games per player.

    Args:
        player_infos (list): List of player info dicts as returned by query_players.
        months (int): Number of months to look back for games (default: 3).

    Returns:
        dict: {player_id: {hero_name: count, ...}, ...}
    """
    from datetime import datetime, timedelta

    now = datetime.now()
    cutoff = now - timedelta(days=30 * months)
    result = {}

    for player in player_infos:
        player_id = player.get("steamAccountId")
        hero_counts = {}
        matches = player.get("matches", [])
        for match in matches:
            # Parse match date if available, otherwise skip
            match_time = match.get("match", {}).get("statsDateTime")
            if match_time:
                # Assume match_time is in ISO format or epoch seconds
                try:
                    # Try ISO format first
                    match_dt = datetime.fromisoformat(match_time)
                except Exception:
                    # Try epoch seconds
                    try:
                        match_dt = datetime.utcfromtimestamp(int(match_time))
                    except Exception:
                        continue
                if match_dt < cutoff:
                    continue
            # If no date, include (or skip if you want strictness)
            player_match_info = match.get("players", [])
            if not player_match_info:
                continue
            player_match_info = player_match_info[0]

            hero = player_match_info.get("hero", {})
            hero_id = int(hero.get("heroId"))
            if hero_id:
                hero_counts[hero_id] = hero_counts.get(hero_id, 0) + 1
        result[player_id] = hero_counts

    return result

if __name__ == '__main__':
    heroes = [
        match("Beast"),
        match("Ring"),
        match("pango"),
        match("AA"),
        match("Kunkka"),

        match("Jakiro"),
        match("Bristle"),
        match("DK"),
        match("TA"),
        match("Silencer"),

        match("MK"),
        match("Shadow Shaman"),
        match("Medusa"),
        match("Disruptor"),
    ]

    their_heroes = [
        match("Omniknight"),
        match("Bristleback"),
        match("AA"),
        match("Tiny"),
        match("Ember Spirit"),

        match("Templar Assassin"),
        match("Terrorblade"),
        match("Shadow Shaman"),
        match("Beastmaster"),
        match("Timbersaw"),

        match("Drow Ranger"),
        match("Morphling"),

    ]

    """
    player_ids = []

    player_mappings = scrape_team(14783)
    for player_name, stratz_ids in player_mappings.items():
        player_ids.extend(stratz_ids)

    # TODO: Use the stratz teams API to also find regular standins

    player_ids = [int(player_id) for player_id in player_ids]

    print(player_ids, type(player_ids[0]))
    player_infos = query_players(player_ids[:2])
    pprint(count_recent_heroes_per_player(player_infos, months=3))
    """

    print_report(heroes, their_heroes)