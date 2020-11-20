
import requests

import secret

#API_ROOT = 'https://api.opendota.com/api/matches/271145478?api_key=YOUR-API-KEY'
API_ROOT = 'https://api.opendota.com/api'

def make_example_call():
    response = requests.get(
        f'{API_ROOT}/matches/5705824607',
        params=dict(api_key=secret.OPENDOTA_API_KEY),
    )
    return response.json()

if __name__ == '__main__':
    make_example_call()

