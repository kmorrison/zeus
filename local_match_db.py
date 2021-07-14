import gzip
import json
import os
import time

import dateparser
import more_itertools

import matchlib
import opendota

# Each match, fully parsed, is about 250KB, so 4 is 1MB and 4k is 1GB. So we'll
# limit files to about 4k so we can comfortably load the whole thing into
# memory.
MATCHES_PER_FILE = 4000

DB_DIR = "localmatches/"

def populate_db(name, num_matches=10000, start_time=None, matches_per_file=MATCHES_PER_FILE):
    matches_to_save = []
    total_matches = 0
    for i, match_group in enumerate(more_itertools.chunked(
        matchlib.iterate_matches(start_time, limit=num_matches),
        matches_per_file,
    )):
        for match_info in match_group:
            # TODO: Handle ratelimit
            match_data = opendota.get_match_by_id(match_info['match_id'])
            # TODO: Double check that the match is parsed.
            matches_to_save.append(match_data)
            total_matches += 1

        with gzip.open(os.path.join(DB_DIR, f"{name}{i}.json.gz"), 'wb') as f:
            f.write(json.dumps(matches_to_save).encode())
            print(f"Wrote chunk, size {len(matches_to_save)}, total {total_matches}")
        matches_to_save = []
        time.sleep(1)
        
    print(f"Done, wrote total {total_matches}")
    

def all_matches_from_db(name):
    dirlist = [fname for fname in os.listdir(DB_DIR) if fname.startswith(name)]
    dirlist.sort()
    for filename in dirlist:
        fullpath = os.path.join(DB_DIR, filename)
        with gzip.open(fullpath, 'rb') as f:
            matches = json.loads(f.read().decode())
        for match in matches:
            yield match

if __name__ == '__main__':
    match = opendota.get_match_by_id(matchlib.stomp_match_id)
    # populate_db(
    #     'moneydb',
    #     num_matches=1000,
    #     start_time=match['start_time'],
    #     matches_per_file=200,
    # )
    start_times = [m['start_time'] for m in all_matches_from_db('moneydb')]
    parsed_matches = [
        m
        for m in all_matches_from_db('moneydb')
        if bool(m['players'][0].get('purchase_log', None))
    ]
    sorted_parsed_matches = sorted(parsed_matches, key=lambda x: x['start_time'])
    print(
        dateparser.parse(str(sorted_parsed_matches[0]['start_time'])), 
        dateparser.parse(str(sorted_parsed_matches[-1]['start_time'])), 
    )
    from pprint import pprint
    pprint([
        f"https://www.opendota.com/matches/{m['match_id']}/overview" 
        for m in sorted_parsed_matches
    ])
    print([m['match_id'] for m in sorted_parsed_matches][:50])
