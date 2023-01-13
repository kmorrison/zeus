import argparse
import math
import json

import dateparser
import tabulate

import couchdb
import matchlib
import opendota

def fetch_and_store_ability_constants():
    # TODO: Probably should generalize this to refresh all local constants
    abilities = opendota.get_abilities()
    with open('abilities.json', 'w') as f:
        f.write(json.dumps(abilities))

    ability_ids = opendota.get_ability_ids()
    with open('ability_ids.json', 'w') as f:
        f.write(json.dumps(ability_ids))

def load_ability_constants():
    with open('abilities.json') as f:
        abilities = json.loads(f.read())

    with open('ability_ids.json') as f:
        ability_ids = json.loads(f.read())
    return abilities, ability_ids
    

def extract_ability_upgrades_from_player_data(player_data):
    hero = opendota.find_hero_by_id(player_data["hero_id"])

    ability_ids = player_data["ability_upgrades_arr"]

    is_radiant = bool(player_data["player_slot"] < 127)
    radiant_win = bool(player_data["radiant_win"])
    other_team_won = bool(is_radiant ^ radiant_win)

    return dict(
        hero=hero,
        ability_ids=ability_ids,
        is_radiant=is_radiant,
        player_won=not (other_team_won),
    )

# XXX
def _is_talent(ability_info):
    return not bool(ability_info.get('behavior', None))

def calculate_talent_winrates(dbquery, hero_name, max_level=16):
    abilities, ability_ids = load_ability_constants()
    ability_wins_and_games = {}
    hero = opendota.find_hero(hero_name)
    all_games = 0
    for game in dbquery:
        for player_game in game['players']:
            if player_game['hero_id'] != hero['id']:
                continue
            ability_data = extract_ability_upgrades_from_player_data(player_game)
            if ability_data['ability_ids'] is None:
                continue
            all_games += 1
            for i, ability_id in enumerate(ability_data['ability_ids'][:max_level]):
                ability_name = ability_ids.get(str(ability_id), None)
                if ability_name is None:
                    continue

                full_ability_info = abilities[ability_name]
                if not full_ability_info:
                    continue
                if not _is_talent(full_ability_info):
                    continue

                ability_wins_and_games.setdefault(full_ability_info['dname'], {})
                ability_wins_and_games[full_ability_info['dname']].setdefault('earliest_taken', 30)
                if ability_wins_and_games[full_ability_info['dname']]['earliest_taken'] > i + 1:
                    ability_wins_and_games[full_ability_info['dname']]['earliest_taken'] = i + 1

                ability_wins_and_games[full_ability_info['dname']].setdefault('wins', 0)
                ability_wins_and_games[full_ability_info['dname']]['wins'] += ability_data['player_won']
                ability_wins_and_games[full_ability_info['dname']].setdefault('games', 0)
                ability_wins_and_games[full_ability_info['dname']]['games'] += 1

    print(11111111, all_games)
    return ability_wins_and_games



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hero", type=str, default="")
    parser.add_argument("--start-time", type=str, default='Jan 1 2020')
    parser.add_argument("--max-level", type=int, default=16)

    args = parser.parse_args()

    db = couchdb.get_matches_db()
    start_time = dateparser.parse(args.start_time).timestamp()
    dbquery = couchdb.get_all_matches_with_hero_after_start_time(
        db,
        start_time,
        [args.hero],
    )
    talent_winrates = calculate_talent_winrates(dbquery, args.hero, args.max_level)
    talent_winrate_table = []
    for talent_name, game_info in talent_winrates.items():
        winrate = game_info['wins'] / game_info['games']
        standard_deviation = math.sqrt(
            winrate * (1 - winrate) / game_info.get("games", 1)
        )

        talent_winrate_table.append([talent_name, game_info['earliest_taken'], game_info['wins'], game_info['games'], winrate, standard_deviation])
    talent_winrate_table = sorted(talent_winrate_table, key=lambda x: x[1])
    print(
        tabulate.tabulate(talent_winrate_table, headers=["Name", "Level", "Wins", "Games", "Winrate", "StdDev"])
    )
    print("\n")