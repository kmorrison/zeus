import pytest
import opendota


def test_find_juggernaut():
    juggernaut = opendota.find_hero("Juggernaut")
    assert juggernaut["localized_name"] == "Juggernaut"


def test_hero_id():
    juggernaut_id = opendota.get_hero_id("Juggernaut")
    assert juggernaut_id == 8


def test_query():
    print(opendota.make_query("Bloodseeker", "Crystal Maiden"))
    assert type(opendota.make_query("Bloodseeker", "Crystal Maiden")) is dict


def test_get_matches():
    assert type(opendota.get_matches("Bloodseeker", "Crystal Maiden")) is list


def test_generate_query(): 
    print(opendota.generate_query("Bloodseeker", "Crystal Maiden", "Juggernaut", "Oracle"))