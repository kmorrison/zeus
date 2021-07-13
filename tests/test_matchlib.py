import json

import pytest

import opendota
import matchlib

@pytest.fixture
def comeback_match_data():
    with open('tests/fixtures/comeback_match.json') as f:
        return json.loads(f.read())


@pytest.fixture
def stomp_match_data():
    with open('tests/fixtures/stomp_match.json') as f:
        return json.loads(f.read())


def test_get_items():
    all_items = opendota.get_item_table()
    assert all_items['blink']
    assert all_items['blades_of_attack']


def test_extract_item_purchases(comeback_match_data):
    item_purchase_data = [
        matchlib.extract_item_purchases_from_player_data(player) 
        for player in comeback_match_data['players']
    ]

    assert len(item_purchase_data) == 10
    first_player_item_purchases = item_purchase_data[0]
    assert first_player_item_purchases['hero']['localized_name'] == 'Windranger'
    assert first_player_item_purchases['is_radiant']
    assert first_player_item_purchases['player_won']

    last_player_item_purchases = item_purchase_data[-1]
    assert last_player_item_purchases['hero']['localized_name'] == 'Invoker'
    assert not last_player_item_purchases['is_radiant']
    assert not last_player_item_purchases['player_won']


def test_prune_winmore(comeback_match_data):
    item_purchase_data = [
        matchlib.extract_item_purchases_from_player_data(player) 
        for player in comeback_match_data['players']
    ]

    immortal_player_item_purchases = item_purchase_data[0]
    original_purchase_data = immortal_player_item_purchases['purchases']
    assert immortal_player_item_purchases['hero']['localized_name'] == 'Windranger'
    pruned_item_purchases = matchlib.prune_winmore_purchases(
        comeback_match_data, 
        [immortal_player_item_purchases],
        advantage_threshold=20,
    )
    assert len(pruned_item_purchases[0]['purchases']) < len(original_purchase_data)

def test_prune_winmore_stomp(stomp_match_data):
    item_purchase_data = [
        matchlib.extract_item_purchases_from_player_data(player) 
        for player in stomp_match_data['players']
    ]

    immortal_player_item_purchases = item_purchase_data[-2]
    original_purchase_data = immortal_player_item_purchases['purchases']
    assert immortal_player_item_purchases['hero']['localized_name'] == 'Storm Spirit'
    pruned_item_purchases = matchlib.prune_winmore_purchases(
        stomp_match_data, 
        [immortal_player_item_purchases],
        advantage_threshold=500,
    )
    assert len(pruned_item_purchases[0]['purchases']) < len(original_purchase_data)