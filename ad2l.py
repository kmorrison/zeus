import requests
from bs4 import BeautifulSoup

def scrape_team(team_id):
    """
    Scrapes the team page for the given team ID and extracts player information.

    Args:
        team_id (int): The ID of the team to scrape.

    Returns:
        dict: A dictionary where the key is the player name and the value is a list of their Stratz player IDs.
    """
    url = f"https://dota.playon.gg/teams/{team_id}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch the page. Status code: {response.status_code}")

    soup = BeautifulSoup(response.text, 'html.parser')
    roster_holder = soup.find('div', class_='rosterholder')
    if not roster_holder:
        raise Exception("Could not find the rosterholder div on the page.")

    players = {}
    current_player_name = None

    for container in roster_holder.find_all('li', class_='rosterNameContainer'):
        # Check if this is an alternate name pointing to the last non-alt player
        if 'rosterNameContainer-alt' in container.get('class', []):
            # Skip alternate names
            continue

        # Extract the player name
        player_name = container.find('div', class_='name').text.strip()
        current_player_name = player_name

        # Extract the links
        links = container.find_all('a')
        stratz_ids = [
            link['href'].split('/')[-1]  # Extract the player ID from the Stratz link
            for link in links if 'stratz.com/players/' in link['href']
        ]

        # Add to the dictionary
        players[current_player_name] = stratz_ids

    return players


if __name__ == "__main__":
    team_id = 14783  # Replace with the desired team ID
    player_data = scrape_team(team_id)
    print(player_data)