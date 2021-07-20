import argparse
import math

import tabulate

import couchdb
import matchlib
import opendota


def calculate_item_winrates_for_every_hero():
    item_info = opendota.get_item_info()
    heroes = calculate_item_winrates(item_info, start_time=None)

    for hero_name, hero_info in heroes.items():
        (
            hero_info["games"],
            hero_info["winrate"],
            marginal_winrate,
            marginal_cost_winrate,
        ) = normalize_item_winrates_by_cost_and_hero_winrate(hero_info, item_info)
        hero_info["marginal_winrate"] = marginal_winrate
        hero_info["marginal_cost_winrate"] = marginal_cost_winrate
        yield hero_name, hero_info


def calculate_item_winrates(item_info, start_time, db_query):
    heroes = {}

    for match in db_query:
        if not matchlib.is_fully_parsed(match):
            continue
        filtered_item_purchases = matchlib.parse_match(match)
        for hero_purchases in filtered_item_purchases:
            hero_name = hero_purchases["hero"]["localized_name"]
            counted_already = set()
            heroes.setdefault(hero_name, {})

            heroes[hero_name].setdefault("wins", 0)
            heroes[hero_name].setdefault("games", 0)
            heroes[hero_name].setdefault("items", {})

            heroes[hero_name]["games"] += 1
            if hero_purchases["player_won"]:
                heroes[hero_name]["wins"] += 1

            for purchase in hero_purchases["purchases"]:
                if purchase["key"] in counted_already:
                    # TODO: Handle consumables, probably via buckets, ie. 1 sentry, 2-4 sentries, 4-8, etc
                    continue
                counted_already.add(purchase["key"])

                heroes[hero_name]["items"].setdefault(
                    purchase["key"], {"wins": 0, "games": 0}
                )
                heroes[hero_name]["items"][purchase["key"]]["games"] += 1
                heroes[hero_name]["items"][purchase["key"]]["wins"] += int(
                    hero_purchases["player_won"]
                )

                components = item_info[purchase["key"]]["components"]
                if not components:
                    continue
                for component in components:
                    if not component in heroes[hero_name]["items"]:
                        continue
                    heroes[hero_name]["items"][component]["games"] -= 1
                    heroes[hero_name]["items"][component]["wins"] -= int(
                        hero_purchases["player_won"]
                    )

    return heroes


def normalize_item_winrates_by_cost_and_hero_winrate(hero_table, item_info, min_num_games = 30):
    hero_winrate = hero_table.get("wins", 0) / hero_table.get("games", 1)
    marginal_winrate = []
    marginal_cost_winrate = []
    for key, game_info in hero_table["items"].items():
        if game_info.get("games", 0) < min_num_games:
            continue
        if item_info[key]["cost"] == 0:
            continue

        winrate = (game_info.get("wins", 0) / game_info.get("games", 1)) - hero_winrate

        marginal_winrate.append(
            (
                winrate,
                game_info.get("games"),
                item_info[key]["dname"],
            )
        )

        cost_winrate = winrate / math.log(item_info[key]["cost"])
        marginal_cost_winrate.append(
            (
                cost_winrate,
                game_info.get("games"),
                item_info[key]["dname"],
            )
        )
    marginal_winrate.sort(reverse=True)
    marginal_cost_winrate.sort(reverse=True)
    return hero_table["games"], hero_winrate, marginal_winrate, marginal_cost_winrate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--hero", type=str, default="")
    parser.add_argument("--start-time", type=int, default=0)
    parser.add_argument("--all-heroes", action="store_true")
    parser.add_argument("--min-num-games", type=int, default=30)
    args = parser.parse_args()

    db = couchdb.get_matches_db()
    dbquery = couchdb.get_all_matches_with_hero_after_start_time(
        db, args.start_time, args.hero,
    )

    item_info = opendota.get_item_table()
    item_winrates = calculate_item_winrates(
        item_info,
        args.start_time,
        dbquery,
    )
    hero_winrates = [
        (hero_name, iw["wins"], iw["games"], (iw["wins"] / iw["games"]) * 100)
        for (hero_name, iw) in item_winrates.items()
    ]
    hero_winrates = sorted(hero_winrates, key=lambda x: x[3], reverse=True)
    print(
        tabulate.tabulate(hero_winrates, headers=["Name", "Wins", "Games", "Winrate"])
    )
    print("\n")

    if args.hero:
        games, winrate, a, b = normalize_item_winrates_by_cost_and_hero_winrate(
            item_winrates[args.hero],
            item_info,
            args.min_num_games,
        )

        print(f"Hero: {args.hero}")
        print(f"Overall Winrate: {winrate * 100} over {games} games")
        print("\n")
        print(tabulate.tabulate(a, headers=["Marginal Winrate", "Total Games", "Item"]))
        print("\n")
        print(
            tabulate.tabulate(
                b, headers=["Marginal Cost Winrate", "Total Games", "Item"]
            )
        )

    if args.all_heroes:
        a_list = []
        for hero_name in item_winrates:
            games, winrate, a, b = normalize_item_winrates_by_cost_and_hero_winrate(
                item_winrates[hero_name], item_info, args.min_num_games
            )
            a_with_hero_name = [(*item, hero_name) for item in a ]
            a_list.extend(a_with_hero_name)

        a_list.sort(key=lambda x: x[0], reverse=True)
        print(
            tabulate.tabulate(
                a_list[:100], headers=["Marginal Winrate", "Total Games", "Item", "Hero"]
            )
        )