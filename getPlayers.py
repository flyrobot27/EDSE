import os
import requests
from tqdm import tqdm
from SPARQLWrapper import SPARQLWrapper, JSON


def fetch_players(club_wikidata_id):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    SELECT ?player ?playerLabel WHERE {{
        ?player wdt:P54 wd:{club_wikidata_id}.
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    players = []
    for result in results["results"]["bindings"]:
        player_data = {
            'wikidata_id': result['player']['value'].split('/')[-1],  # Extract the Wikidata ID
            'name': result['playerLabel']['value']
        }
        players.append(player_data)

    return players


def process_files(directory_path):
    for root, dirs, files in os.walk(directory_path):
        for file_name in tqdm(files, desc="Processing files"):
            file_path = os.path.join(root, file_name)
            output_file_path = os.path.join(root, f"{os.path.splitext(file_name)[0]}_wikidataID.txt")

            with open(file_path, 'r') as file, open(output_file_path, 'w') as output_file:
                for line in tqdm(file, desc="Processing clubs"):
                    club_wikidata_id = line.strip()
                    players = fetch_players(club_wikidata_id)

                    for player in players:
                        output_file.write(f"{player['wikidata_id']}\t{player['name']}\n")


directory_path = './clubs'
process_files(directory_path)
