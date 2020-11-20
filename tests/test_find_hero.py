import pytest
import opendota


def test_find_juggernaut():
    juggernaut = opendota.find_hero("Juggernaut")
    assert juggernaut["localized_name"] == "Juggernaut"


def test_hero_id():
    juggernaut_id = opendota.get_hero_id("Juggernaut")
    assert juggernaut_id == 8
