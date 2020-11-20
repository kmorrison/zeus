import opendota

herolist = opendota.get_hero_list()

i = 1


def find_hero(heroname):
    i = 1
    for hero in herolist:
        i += 1
        if herolist[i]["localized_name"] == heroname:
            return herolist[i]

    print("Didn't find the hero")
    return


print(find_hero("Juggernaut"))
