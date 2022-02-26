import dota2api
import requests
import json
import time
from dotastats.models import Match, Player
from app_secrets import *


class ProMatchScraper:
    def __init__(self):
        self.client = dota2api.Initialise(api_key=STEAM_API_KEY)

    def get_pro_matches(self):
        return self.client.get_top_live_games()
    
    def parse_and_persist_match(self, match): 
        match_obj = Match.objects.get_or_create(steam_match_id=match['match_id'], average_mmr=match['average_mmr'])
        for player in match['players']: 
            player_ids = player['account_id']
            player = Player.objects.get_or_create(steam_player_id=player['account_id']) 
            player.matches.add(match_obj)
            
                                          