from string import Template

import dateparser

import opendota

comeback_match_id = 6084764514
stomp_match_id = 6081301206
MAX_GPM_ADV = 500
DEFAULT_QUERY_PAGE_SIZE = 100

HEROES = opendota.load_hero_list()

towers_we_care_about = {
    "npc_dota_goodguys_tower1_bot": 0,
    "npc_dota_goodguys_tower1_mid": 1,
    "npc_dota_goodguys_tower1_top": 2,
    "npc_dota_badguys_tower1_bot": 3,
    "npc_dota_badguys_tower1_mid": 4,
    "npc_dota_badguys_tower1_top": 5,
    "npc_dota_goodguys_tower2_bot": 0,
    "npc_dota_goodguys_tower2_mid": 1,
    "npc_dota_goodguys_tower2_top": 2,
    "npc_dota_badguys_tower2_bot": 3,
    "npc_dota_badguys_tower2_mid": 4,
    "npc_dota_badguys_tower2_top": 5,
    "npc_dota_goodguys_tower3_bot": 0,
    "npc_dota_goodguys_tower3_mid": 1,
    "npc_dota_goodguys_tower3_top": 2,
    "npc_dota_badguys_tower3_bot": 3,
    "npc_dota_badguys_tower3_mid": 4,
    "npc_dota_badguys_tower3_top": 5,
}

roshan = ["CHAT_MESSAGE_ROSHAN_KILL", "CHAT_MESSAGE_AEGIS"]


def extract_objectives_dict_from_match(match_data):
    objectives_dict = match_data["objectives"]

    return [
        objective
        for objective in objectives_dict
        if objective["type"] in roshan
        or objective.get("key", "") in towers_we_care_about
    ]


def extract_item_purchases_from_player_data(player_data):
    hero = opendota.find_hero_by_id(player_data["hero_id"])

    purchases = player_data["purchase_log"]

    is_radiant = bool(player_data["player_slot"] < 127)
    radiant_win = bool(player_data["radiant_win"])
    other_team_won = bool(is_radiant ^ radiant_win)

    return dict(
        hero=hero,
        purchases=purchases,
        is_radiant=is_radiant,
        player_won=not (other_team_won),
    )


def prune_winmore_purchases(
    full_match_data, item_purchases, advantage_threshold=MAX_GPM_ADV
):
    # Pretty sure this is just [i * 60 for i in range(<duration>)]
    times = full_match_data["players"][0]["times"]

    gold_adv_per_min = []
    for i, radiant_adv in enumerate(full_match_data["radiant_gold_adv"]):
        if i == 0:
            gold_adv_per_min.append(radiant_adv / 1)
        else:
            gold_adv_per_min.append(radiant_adv / i)

    for item_purchase_data in item_purchases:
        pruned_purchase_log = []
        current_time_idx = 0
        for item_purchase in item_purchase_data["purchases"]:
            item_purchase_time = item_purchase["time"]
            # Advance current time to just before the item is purchased
            try:
                while item_purchase_time > times[current_time_idx + 1]:
                    current_time_idx += 1
            except IndexError:
                # Item was purchased in last minute of game
                assert times[current_time_idx] == times[-1]
            gold_advantage_at_that_time = gold_adv_per_min[current_time_idx]
            if not item_purchase_data["is_radiant"]:
                gold_advantage_at_that_time *= -1
            # TODO: Maybe also prune by benchmark key
            # TODO: Make pruner a strategy somehow
            if times[current_time_idx] > 600:
                if bool(
                    gold_advantage_at_that_time >= advantage_threshold
                    and item_purchase_data["player_won"]
                ):
                    # print(
                    #     f"Excluding {item_purchase} for {item_purchase_data['hero']['localized_name']} because of winmore"
                    # )
                    continue
                if bool(
                    gold_advantage_at_that_time < -advantage_threshold
                    and not item_purchase_data["player_won"]
                ):
                    # print(f"Excluding {item_purchase} for {item_purchase_data['hero']['localized_name']} because of losemore")
                    continue

            pruned_purchase_log.append(item_purchase)
        item_purchase_data["purchases"] = pruned_purchase_log
    return item_purchases


def parse_match(full_match_data):
    players = full_match_data["players"]

    item_purchases = [
        extract_item_purchases_from_player_data(player) for player in players
    ]
    revised_item_purchases = prune_winmore_purchases(full_match_data, item_purchases)
    return revised_item_purchases


MATCHFINDER_QUERY = Template(
    """
SELECT
    public_matches.match_id,
    public_matches.avg_mmr,
    public_matches.start_time,
    public_matches.game_mode
FROM
    public_matches
WHERE
    public_matches.avg_mmr > 4000
    AND public_matches.game_mode IN (1, 2, 3, 4, 5, 22)
    AND public_matches.start_time > $start_time
ORDER BY public_matches.start_time ASC
LIMIT $query_limit
"""
)


def iterate_matches(date_string, limit=200, page_size=DEFAULT_QUERY_PAGE_SIZE):
    start = int(dateparser.parse(str(date_string)).timestamp())
    count = 0
    while count < limit:
        query = MATCHFINDER_QUERY.substitute(
            start_time=start,
            query_limit=page_size,
        )
        # TODO: Handle rate limit
        result = opendota.query_explorer(query)
        for row in result["rows"]:
            yield row
            count += 1
            if count >= limit:
                return
        time_of_last_match_in_query = result["rows"][-1]["start_time"]
        start = int(dateparser.parse(str(time_of_last_match_in_query)).timestamp())


def is_fully_parsed(match):
    return bool(match["players"][0].get("purchase_log", None))


if __name__ == "__main__":
    match = opendota.get_match_by_id(stomp_match_id)
    print(list(iterate_matches(match["start_time"])))
