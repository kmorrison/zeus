import argparse
import gzip
import json
import os
import re
import time

import cloudant
import dateparser
import more_itertools

import couchdb
import matchlib
import opendota

# Each match, fully parsed, is about 250KB, so 4 is 1MB and 4k is 1GB. So we'll
# limit files to about 4k so we can comfortably load the whole thing into
# memory.
MATCHES_PER_FILE = 4000

DB_DIR = "localmatches/"


def populate_db(
    name, num_matches=10000, start_time=None, matches_per_file=MATCHES_PER_FILE
):
    _populate_db(
        name,
        num_matches=num_matches,
        start_time=start_time,
        matches_per_file=matches_per_file,
        start_idx=0,
    )


def _populate_db(
    name,
    num_matches=10000,
    start_time=None,
    matches_per_file=MATCHES_PER_FILE,
    start_idx=0,
):
    matches_to_save = []
    total_matches = 0
    for i, match_group in enumerate(
        more_itertools.chunked(
            matchlib.iterate_matches(start_time, limit=num_matches),
            matches_per_file,
        )
    ):
        for match_info in match_group:
            # TODO: Handle ratelimit
            match_data = opendota.get_match_by_id(match_info["match_id"])
            # TODO: Double check that the match is parsed.
            matches_to_save.append(match_data)
            total_matches += 1

        with gzip.open(
            os.path.join(DB_DIR, f"{name}{i + start_idx}.json.gz"), "wb"
        ) as f:
            f.write(json.dumps(matches_to_save).encode())
            print(f"Wrote chunk, size {len(matches_to_save)}, total {total_matches}")
        matches_to_save = []
        time.sleep(1)

    print(f"Done, wrote total {total_matches}")


def _extract_filenumber(filename, dbname):
    # TODO: test
    name_template = fr"{dbname}(\w+).json.gz"
    template_match = re.match(name_template, filename)
    return int(template_match.group(1))


def _find_highwater_file_number(filenames, dbname):
    # TODO: test
    highwater_file = sorted(filenames, key=lambda x: _extract_filenumber(x, dbname))[-1]
    return _extract_filenumber(highwater_file, dbname)


def extend_existing_match_db(
    name, num_matches=10000, matches_per_file=MATCHES_PER_FILE
):
    dirlist = [fname for fname in os.listdir(DB_DIR) if fname.startswith(name)]
    highwater_file_number = _find_highwater_file_number(dirlist, name)
    highwater_file = os.path.join(DB_DIR, f"{name}{highwater_file_number}.json.gz")
    with gzip.open(highwater_file, "rb") as f:
        matches = json.loads(f.read().decode())
    last_start_time = matches[-1]["start_time"]

    _populate_db(
        name,
        num_matches=num_matches,
        start_time=last_start_time,
        matches_per_file=matches_per_file,
        start_idx=highwater_file_number + 1,
    )


def all_matches_from_db(name):
    dirlist = [fname for fname in os.listdir(DB_DIR) if fname.startswith(name)]
    dirlist = sorted(dirlist, key=lambda x: _extract_filenumber(x, name))
    for filename in dirlist:
        fullpath = os.path.join(DB_DIR, filename)
        with gzip.open(fullpath, "rb") as f:
            matches = json.loads(f.read().decode())
        for match in matches:
            yield match


def get_all_parsed_matches(dbname):
    # TODO: test for parsedness
    parsed_matches = [
        m for m in all_matches_from_db(dbname) if matchlib.is_fully_parsed(m)
    ]
    return parsed_matches


def get_all_unparsed_matches(dbname):
    # TODO: test for unparsedness
    unparsed_matches = [
        m for m in all_matches_from_db(dbname) if not matchlib.is_fully_parsed(m)
    ]
    return unparsed_matches


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--num-matches", type=int, default=1000)
    parser.add_argument("--matches-per-file", type=int, default=200)
    parser.add_argument("--dbname", type=str, default="moneydb")

    parser.add_argument("--populate-local", action="store_true")
    parser.add_argument("--extend-local", action="store_true")
    parser.add_argument("--display-stats-local", action="store_true")
    parser.add_argument("--migrate-local", action="store_true")

    parser.add_argument("--migrate-dbname", type=str, default=couchdb.MATCHES_DBNAME)
    parser.add_argument("--display-stats", action="store_true")

    args = parser.parse_args()

    with open("tests/fixtures/stomp_match.json") as f:
        match = json.loads(f.read())

    if args.populate_local:
        populate_db(
            args.dbname,
            num_matches=args.num_matches,
            start_time=match["start_time"],
            matches_per_file=args.matches_per_file,
        )

    if args.extend_local:
        extend_existing_match_db(
            args.dbname,
            num_matches=args.num_matches,
            matches_per_file=args.matches_per_file,
        )

    if args.display_stats_local:
        start_times = [m["start_time"] for m in all_matches_from_db(args.dbname)]
        parsed_matches = [
            m for m in all_matches_from_db(args.dbname) if matchlib.is_fully_parsed(m)
        ]
        sorted_parsed_matches = sorted(parsed_matches, key=lambda x: x["start_time"])
        print(
            dateparser.parse(str(sorted_parsed_matches[0]["start_time"])),
            dateparser.parse(str(sorted_parsed_matches[-1]["start_time"])),
        )
        print(f"Num fully parsed matches: {len(parsed_matches)}")

    if args.migrate_local:
        matches_db = couchdb.get_matches_db(args.migrate_dbname)

        for match in all_matches_from_db(args.dbname):
            if matchlib.is_fully_parsed(match):
                couchdb.store_match_to_db(matches_db, match)

    if args.display_stats:
        matches_db = couchdb.get_matches_db(args.migrate_dbname)
        all_docs = matches_db.all_docs()

        print(f"Num fully parsed matches: {all_docs['total_rows']}")

        print(
            f"Last match start_time {couchdb.get_last_match_by_start_time(matches_db)['start_time']}"
        )
