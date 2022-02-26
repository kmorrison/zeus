from pyexpat import model
from typing_extensions import Required
from django.db import models
from django.forms import JSONField

# Create your models here.
class Match(models.Model):
    id = models.AutoField(primary_key=True)
    steam_match_id = models.IntegerField()
    radiant_win = models.BooleanField()
    duration = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    steam_api_digest = JSONField()
    average_mmr = models.IntegerField()


class Player(models.Model):
    id = models.AutoField(primary_key=True)
    steam_player_id = models.IntegerField()
    matches = models.ManyToManyField(Match)
    mmr = models.IntegerField(null=True)
