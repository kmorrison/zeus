import requests 

import secret


#API_ROOT = 'https://api.opendota.com/api/matches/271145478?api_key=YOUR-API-KEY'
API_ROOT = 'https://api.opendota.com/api'

#get/find matches


# def find_matches_by_hero():

def find_hero(heroname):
  for hero in get_hero_list():
    if hero['localized_name'] == heroname:
        return hero
  print("Didn't find the hero")
  return

def get_hero_id(heroname): 
  return find_hero(heroname)['id']

def get_hero_list(): 
  response = requests.get(
    f'{API_ROOT}/heroes',
    params = dict(api_key = secret.OPENDOTA_API_KEY)
  )
  return response.json()

def make_example_call():
    response = requests.get(
        f'{API_ROOT}/matches/271145478',
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    print(response.json())


def main():
  heroname = input("Enter hero name: ")
  print(find_hero(heroname))
  print("ID = ", get_hero_id(heroname))


if __name__ == '__main__':
    main()

