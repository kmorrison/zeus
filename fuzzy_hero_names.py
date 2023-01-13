import opendota

def _score_hero_name(hero_name, input):
    normalized_hero_name = hero_name.lower()
    normalized_input = input.strip().lower()
    if normalized_input == normalized_hero_name:
        return 100
    if normalized_hero_name.startswith(normalized_input):
        return 10 * len(normalized_input)
    
    # Try to do acronym matching, ie. AM -> Anti-Mage
    parts = normalized_hero_name.split()
    if len(parts) == 2 and len(normalized_input) == 2:
        return 25 * (normalized_input[0] == parts[0][0]) + 25 * (normalized_input[1] == parts[1][0])
    if len(parts) == 2 and len(normalized_input) > 3 and parts[1].startswith(normalized_input):
        return 5 * len(normalized_input)

    parts = normalized_hero_name.split('-')
    if len(parts) == 2 and len(normalized_input) == 2:
        return 25 * (normalized_input[0] == parts[0][0]) + 25 * (normalized_input[1] == parts[1][0])
    if len(parts) == 2 and len(normalized_input) > 3 and parts[1].startswith(normalized_input):
        return 5 * len(normalized_input)

    return 0

def match(input):
    heroes = opendota.load_hero_list().values()
    best_score = 0
    best_match = None
    for hero in heroes:
        score = _score_hero_name(hero['localized_name'], input)
        if score > best_score:
            best_score = score
            best_match = hero
    return best_match

if __name__ == '__main__':
    print(match('AM'))
    print(match('grim'))
    print(match('jugg'))
    print(match('CM'))
    print(match('maiden'))
    print(match('primal'))
    print(match('OD'))
    print(match('Pango'))