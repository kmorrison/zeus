#!python
import opendota
import fuzzy_hero_names
import sys

if __name__ == '__main__':
    input = sys.argv[1]

    try:
        input = int(input)
        print(opendota.find_hero_by_id(input))
    except ValueError:
        print(fuzzy_hero_names.match(input))