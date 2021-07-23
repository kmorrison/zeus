import math
import pprint
import sys

import more_itertools

from item_rater import calculate_item_winrates
import couchdb
import matchlib


def is_valid_tower_configuration(tower_configuration):
    """Syntax arg checker for when we eventually wanna pass in tower configurations
    to the script as a user"""
    pass


def calculate_gpm_slope_from_times(
    t1, t2, gpm_advantage_histogram, xpm_advantage_histogram
):
    idx1 = int(math.floor(t1 / 60))
    idx2 = int(math.floor(t2 / 60))
    if idx1 == idx2:
        # If the tower state didn't exist for long, ignore the gpm during that
        # tower state.
        return None, None

    return (
        sum(gpm_advantage_histogram[idx1:idx2]) / (idx2 - idx1),
        sum(xpm_advantage_histogram[idx1:idx2]) / (idx2 - idx1),
    )


def calculate_gpm_advantage_for_all_tower_configurations(db):
    """Calculate the GPM advantage for each tower configuration"""

    matches = couchdb.get_all_parsed_matches_more_recent_than(db, 0)

    configuration_to_gpm_map = {}

    for match in matches:
        # for each match, get the tower configurations with times
        tower_configurations_with_times = []
        match_tower_configuration = [3, 3, 3, 3, 3, 3]
        tower_configurations_with_times.append((tuple(match_tower_configuration), 0))
        for objective in matchlib.extract_objectives_dict_from_match(match):
            if objective.get("key", None) in matchlib.towers_we_care_about:
                match_tower_configuration[
                    matchlib.towers_we_care_about[objective["key"]]
                ] -= 1
                tower_configurations_with_times.append(
                    (tuple(match_tower_configuration), objective["time"])
                )

        gold_adv_per_min = []
        for i, radiant_adv in enumerate(match["radiant_gold_adv"]):
            if i == 0:
                gold_adv_per_min.append(radiant_adv / 1)
            else:
                gold_adv_per_min.append(radiant_adv / i)

        xp_adv_per_min = []
        for i, radiant_adv in enumerate(match["radiant_xp_adv"]):
            if i == 0:
                xp_adv_per_min.append(radiant_adv / 1)
            else:
                xp_adv_per_min.append(radiant_adv / i)

        for conf1, conf2 in more_itertools.pairwise(tower_configurations_with_times):
            gpm_slope, xpm_slope = calculate_gpm_slope_from_times(
                conf1[1],
                conf2[1],
                gold_adv_per_min,
                xp_adv_per_min,
            )
            if gpm_slope is None:
                # We've been told that the configuration didn't last long enough
                # to be relevant, ignore it
                continue

            key = tuple(conf1[0])

            configuration_to_gpm_map.setdefault(key, []).append(
                (
                    gpm_slope,
                    xpm_slope,
                    match["match_id"],
                )
            )

    return configuration_to_gpm_map


def calculate_average_gpm_for_tower_configs(configuration_to_gpm_map):
    final_map = {}
    for configuration, gpms_and_matches in configuration_to_gpm_map.items():
        avg_gpm = sum([gpm[0] for gpm in gpms_and_matches]) / len(gpms_and_matches)
        avg_xpm = sum([gpm[1] for gpm in gpms_and_matches]) / len(gpms_and_matches)

        final_map[configuration] = (avg_gpm, avg_xpm, len(gpms_and_matches))

    return final_map


def calculate_adjacent_states(current_state):
    for i in range(len(current_state)):
        if current_state[i] > 0:
            current_state_copy = list(current_state)
            current_state_copy[i] -= 1

            yield tuple(current_state_copy)


if __name__ == "__main__":
    db = couchdb.get_matches_db()
    configuration_map = calculate_gpm_advantage_for_all_tower_configurations(db)
    final_map = calculate_average_gpm_for_tower_configs(configuration_map)

    if len(sys.argv) == 2:
        current_state_str = sys.argv[1]
        current_state = tuple([int(i) for i in current_state_str])
        print("")
        print(current_state, final_map[current_state])

        for adjacent_state in calculate_adjacent_states(current_state):
            print(adjacent_state, final_map.get(adjacent_state, (0, 0, 0)))
    else:
        final_map_sorted = sorted(
            final_map.items(),
            key=lambda x: x[1][2],
            reverse=True,
        )
        pprint.pprint(final_map_sorted)
