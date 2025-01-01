# this file fetches the data from the json files
import json


def parse_json(path):
    with open(path, 'r') as f:
        jeson = json.load(f)

    return jeson


if __name__ == "__main__":
    # make sure you run this script from utils/ dir
    path = "../data/config.json"
    jeson = parse_json(path)
    # print(jeson["BOT_TOKEN"])


