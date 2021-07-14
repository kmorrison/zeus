import matchlib
import opendota
import local_match_db
from collections import defaultdict

def calculate_item_winrates():
    heroes = {}

    for match in local_match_db.all_matches_from_db('moneydb'):
        if not matchlib.is_fully_parsed(match):
            continue
        filtered_item_purchases = matchlib.parse_match(match)
        for hero_purchases in filtered_item_purchases:
            hero_name = hero_purchases['hero']['localized_name']
            counted_already = set()
            heroes.setdefault(hero_name, {})

            heroes[hero_name].setdefault('wins', 0)
            heroes[hero_name].setdefault('games', 0)
            heroes[hero_name].setdefault('items', {})

            heroes[hero_name]['games'] += 1
            if hero_purchases['player_won']:
                heroes[hero_name]['wins'] += 1

            for purchase in hero_purchases['purchases']:
                if purchase['key'] in counted_already:
                    # TODO: Handle consumables, probably via buckets, ie. 1 sentry, 2-4 sentries, 4-8, etc
                    continue
                counted_already.add(purchase['key'])

                heroes[hero_name]['items'].setdefault(purchase['key'], {'wins': 0, 'games': 0})
                heroes[hero_name]['items'][purchase['key']]['games'] += 1
                heroes[hero_name]['items'][purchase['key']]['wins'] += int(hero_purchases['player_won'])
    return heroes

def normalize_item_winrates_by_cost_and_hero_winrate(hero_table, item_info=None):
    if item_info is None:
        item_info = opendota.get_item_table()
    hero_winrate = hero_table.get('wins', 0) / hero_table.get('games', 1)
    print(hero_table['games'], hero_winrate)
    marginal_winrate = []
    marginal_cost_winrate = []
    for key, game_info in hero_table['items'].items():
        if game_info.get('games', 0) < 5:
            continue
        if item_info[key]['cost'] == 0:
            continue
        winrate = (game_info.get('wins', 0) / game_info.get('games', 1)) - hero_winrate
        marginal_winrate.append((winrate, key))
        cost_winrate = winrate / item_info[key]['cost']
        marginal_cost_winrate.append((cost_winrate, key))
    marginal_winrate.sort(reverse=True)
    marginal_cost_winrate.sort(reverse=True)
    return marginal_winrate, marginal_cost_winrate

if __name__ == '__main__':
    item_winrates = calculate_item_winrates()
    item_info = opendota.get_item_table()
    a, b = normalize_item_winrates_by_cost_and_hero_winrate(item_winrates['Phantom Lancer'], item_info)
    from pprint import pprint
    pprint(a)
    pprint(b)
    

