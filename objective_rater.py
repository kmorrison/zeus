import argparse
import math
import tabulate
import couchdb
import matchlib
import opendota
import more_itertools


def is_valid_tower_configuration(tower_configuration):
    pass


def calculate_gpm_advantage_for_all_tower_configurations(
    full_match_data, tower_configuration, db
):
    """Calculate the GPM advantage for each tower configuration"""

    matches = couchdb.get_all_parsed_matches_more_recent_than(db, 0)

    for match in matches:
        # for each match, get the tower configurations with times
        tower_configurations_with_times = []
        match_tower_configuration = [3, 3, 3, 3, 3, 3]
        tower_configurations_with_times.append((match_tower_configuration, 0))
        for objective in matchlib.extract_objectives_dict_from_match(match):
            if objective["key"] in matchlib.towers_we_care_about:
                match_tower_configuration[
                    matchlib.towers_we_care_about[objective["key"]]
                ] -= 1
                tower_configurations_with_times.append(
                    (list(match_tower_configuration), objective["time"])
                )

        for conf1, conf2 in more_itertools.pairwise(tower_configurations_with_times):
            # for each pair of tower configurations, calculate the time bucket
            minute_begin = conf1["time"]
            minute_end = conf2["time"]

            """for each pair of tower configurations, 
            calculate the gpm advantage from minute_begin to minute_end"""
            gpm_advantage = 0
            gpm_advantages = []
            for i in range(minute_begin, minute_end):
                if i == 0:
                    gpm_advantage += match["radiant_gold_adv"] / 1
                else:
                    gpm_advantage += match["radiant_gold_adv"] / i
            gpm_advantages.append(gpm_advantage)
            
            """TODO: return the gpm advantages in some way that makes sense, 
            probably sticking them onto the match's tower_configurations_with_times 
            list maybe could make sense idk"""
            """TODO: probably collapse all of the tower_configurations_with_times
            into some sort of master list of all the tower configurations with the global
            average gpm appended onto them"""


def calculate_tower_winrate(db_query):
    """Iterate through all matches and calculate the
    marginal winrate of each tower taken"""
    for match in db_query:
        if not matchlib.is_fully_parsed(match):
            continue
