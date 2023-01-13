import argparse
import math
import itertools
import json
import collections
import fuzzy_hero_names
import tabulate

import dateparser
import tabulate

import couchdb
import matchlib
import pprint
import opendota
import stratz

def team_of_interest(game, hero_ids, potential_hero_ids):
    heroes_on_radiant = [player['player_slot'] < 127 for player in game['players'] if player['hero_id'] in hero_ids]
    potential_heroes_on_radiant = [player['player_slot'] < 127 for player in game['players'] if player['hero_id'] in potential_hero_ids]
    heroes_all_on_radiant = all(heroes_on_radiant) and any(potential_heroes_on_radiant)
    heroes_all_on_dire = bool(not any(heroes_on_radiant)) and bool(not all(potential_heroes_on_radiant))
    return heroes_all_on_radiant, heroes_all_on_dire


def games_with_heroes_on_same_team(dbquery, hero_ids, potential_hero_ids):
    for game in dbquery:
        heroes_all_on_radiant, heroes_all_on_dire = team_of_interest(game, hero_ids, potential_hero_ids)
        heroes_on_same_team = heroes_all_on_radiant or heroes_all_on_dire
        if heroes_on_same_team:
            yield game
            
def calculate_winrate_for_opposing_heroes(game, heroes, potential_heroes):
    heroes_all_on_radiant, heroes_all_on_dire = team_of_interest(game, heroes, potential_heroes)
    wins = collections.Counter()
    games = collections.Counter()
    
    if heroes_all_on_radiant:
        dire_heroes = [player['hero_id'] for player in game['players'] if player['player_slot'] >= 127]
        wins.update([hero_id for hero_id in dire_heroes if not game['radiant_win']])
        games.update(dire_heroes)
    if heroes_all_on_dire:
        radiant_heroes = [player['hero_id'] for player in game['players'] if player['player_slot'] < 127]
        wins.update([hero_id for hero_id in radiant_heroes if game['radiant_win']])
        games.update(radiant_heroes)

    return wins, games

def calculate_winrates_from_localdb(dbquery, hero_ids, potential_hero_ids):
    wins = collections.Counter()
    games = collections.Counter()
    for i, game in enumerate(games_with_heroes_on_same_team(dbquery, hero_ids, potential_hero_ids)):
        hero_wins, hero_games = calculate_winrate_for_opposing_heroes(game, hero_ids, potential_hero_ids)
        wins += hero_wins
        games += hero_games
    print(f'{i} games analyzed')

    hero_winrate_table = []
    for hero_id, game_count in games.items():
        winrate = wins[hero_id] / game_count
        hero = opendota.find_hero_by_id(hero_id)
        standard_deviation = math.sqrt(
            winrate * (1 - winrate) / game_count
        )
        hero_winrate_table.append([
            hero['localized_name'],
            wins['hero_id'],
            game_count,
            winrate,
            standard_deviation,
        ])

    hero_winrate_table.sort(key=lambda row: row[3], reverse=True)
    print(tabulate.tabulate(hero_winrate_table, headers=['Hero', 'Wins', 'Games', 'Winrate', 'Standard deviation']))

def calculate_from_opendota(hero_ids):
    hero_matchups = [opendota.get_matchups(hero_id) for hero_id in hero_ids]
    wins = {}
    games = {}
    for matchup_payload in hero_matchups:
        for hero_matchup in matchup_payload:
            wins.setdefault(hero_matchup['hero_id'], 0)
            wins[hero_matchup['hero_id']] += hero_matchup['wins']
            games.setdefault(hero_matchup['hero_id'], 0)
            games[hero_matchup['hero_id']] += hero_matchup['games_played']

    hero_winrate_table = []
    for hero_id, game_count in games.items():
        hero_winrate_table.append([
            opendota.find_hero_by_id(hero_id)['localized_name'],
            wins[hero_id],
            game_count,
            wins[hero_id] / game_count,
        ])
    hero_winrate_table.sort(key=lambda row: row[3], reverse=True)
    print(tabulate.tabulate(hero_winrate_table, headers=['Hero', 'Wins', 'Games', 'Winrate']))

def suggest_counterpicks(heroes):
    with_mtx, vs_mtx = stratz.load_fixed_matchups()
    counterpick_score = {}
    for hero in heroes:
        counterpicks = vs_mtx[hero['id']]
        for counterpick in counterpicks.values():
            counterpick_score.setdefault(counterpick['heroId2'], {})
            counterpick_score[counterpick['heroId2']][hero['id']] = counterpick['synergy']
            counterpick_score[counterpick['heroId2']].setdefault('total', 0)
            counterpick_score[counterpick['heroId2']]['total'] += counterpick['synergy']
    counterpick_score = sorted(counterpick_score.items(), key=lambda x: x[1]['total'])
    return counterpick_score[:20], counterpick_score[-20:]

def counterpick_report(hero_names):
    heroes = [fuzzy_hero_names.match(hero_name.strip()) for hero_name in hero_names]
    counterpicks, bad_picks = suggest_counterpicks(heroes)
    counterpick_table = []
    for pick in counterpicks:
        synergy_by_hero = [pick[1].get(hero['id']) for hero in heroes]
        counterpick_table.append([
            opendota.find_hero_by_id(pick[0])['localized_name'],
            pick[1]['total'],
            *synergy_by_hero
        ])
    print(tabulate.tabulate(counterpick_table, headers=['Hero', 'Total synergy'] + [hero['localized_name'] for hero in heroes]))

    badpick_table = []
    for pick in bad_picks:
        synergy_by_hero = [pick[1].get(hero['id'], None) for hero in heroes]
        badpick_table.append([
            opendota.find_hero_by_id(pick[0])['localized_name'],
            pick[1]['total'],
            *synergy_by_hero
        ])
    print(tabulate.tabulate(badpick_table, headers=['Hero', 'Total synergy'] + [hero['localized_name'] for hero in heroes]))


if __name__ == "__main__":
    import sys
    # parser = argparse.ArgumentParser()

    # parser.add_argument("--process-queue", action="store_true")
    # parser.add_argument("--populate-queue", action="store_true")
    # parser.add_argument("--max-matches-to-queue", type=int, default=5)

    # args = parser.parse_args()
    # if args.process_queue:
    #     pass
    hero_names = sys.argv[1:]
    counterpick_report(hero_names)
    