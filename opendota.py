import requests 

import secret


#API_ROOT = 'https://api.opendota.com/api/matches/271145478?api_key=YOUR-API-KEY'
API_ROOT = 'https://api.opendota.com/api'

#get/find matches


def find_hero(heroname): 
  i=1
  herolist = get_hero_list()
  for hero in herolist: 
    i+=1
    if (herolist[i]['localized_name'] == heroname):
      return(herolist[i])
  print("Didn't find the hero")
  return

  
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

if __name__ == '__main__':
    make_example_call()

