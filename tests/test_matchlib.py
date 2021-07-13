import json

import pytest

import opendota
import matchlib

@pytest.fixture
def sample_match_data():
    with open('tests/fixtures/sample_match.json') as f:
        return json.loads(f.read())


def test_get_items():
    all_items = opendota.get_item_table()
    assert all_items['blink']
    assert all_items['blades_of_attack']


def test_extract_item_purchases(sample_match_data):
    item_purchase_data = [
        matchlib.extract_item_purchases_from_player_data(player) 
        for player in sample_match_data['players']
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


def test_prune_winmore(sample_match_data):
    item_purchase_data = [
        matchlib.extract_item_purchases_from_player_data(player) 
        for player in sample_match_data['players']
    ]

    immortal_player_item_purchases = item_purchase_data[0]
    original_purchase_data = immortal_player_item_purchases['purchases']
    assert immortal_player_item_purchases['hero']['localized_name'] == 'Windranger'
    pruned_item_purchases = matchlib.prune_winmore_purchases(
        sample_match_data, 
        [immortal_player_item_purchases],
        advantage_threshold=20,
    )
    assert len(pruned_item_purchases[0]['purchases']) < len(original_purchase_data)