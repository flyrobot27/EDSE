import os
from SPARQLWrapper import SPARQLWrapper, JSON
from neo4j import GraphDatabase
import time

# Neo4j connection setup
uri = "bolt://localhost:7687"
username = "neo4j"
password = "ssrgssrg"
driver = GraphDatabase.driver(uri, auth=(username, password))

def run_query(query, parameters=None):
    with driver.session() as session:
        with session.begin_transaction() as tx:
            result = tx.run(query, parameters)
            records = [record.data() for record in result]
    return records

def fetch_players(club_wikidata_id):
    print(f"Fetching players for club {club_wikidata_id}...")
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    SELECT ?player ?playerLabel WHERE {{
        ?player wdt:P54 wd:{club_wikidata_id}.
        SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)

    try:
        results = sparql.query().convert()
    except Exception as e:
        print(f"Error fetching data for club {club_wikidata_id}: {e}")
        time.sleep(10)  # Wait 10 seconds before retrying
        return fetch_players(club_wikidata_id)  # Retry fetching players after waiting

    players = []
    for result in results["results"]["bindings"]:
        player = {
            'wikidata_id': result['player']['value'].split('/')[-1],
            'name': result['playerLabel']['value']
        }
        players.append(player)
        print(f"Found player {player['name']} for club {club_wikidata_id}")

    time.sleep(1)  # Wait for 1 second before making another request
    return players

def create_player_and_relationship(player_wikidata_id, player_name, club_wikidata_id):
    print(f"Creating player {player_name} and relationship with club {club_wikidata_id}...")
    query = """
    MERGE (p:Player {wikidata_id: $player_wikidata_id, name: $player_name})
    MERGE (c:Club {wikidata_id: $club_wikidata_id})
    MERGE (p)-[:PLAYED_FOR]->(c)
    RETURN p, c
    """
    parameters = {'player_wikidata_id': player_wikidata_id, 'player_name': player_name, 'club_wikidata_id': club_wikidata_id}
    records = run_query(query, parameters)
    return records

def process_files(directory_path):
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            print(f"Processing file {file_name}...")
            file_path = os.path.join(root, file_name)

            with open(file_path, 'r') as file:
                for line in file:
                    club_wikidata_id = line.strip()
                    players = fetch_players(club_wikidata_id)

                    for player in players:
                        create_player_and_relationship(player['wikidata_id'], player['name'], club_wikidata_id)

            print(f"Finished processing {file_name}. Waiting for 1 minute before proceeding to the next file.")
            time.sleep(60)  # Wait for 1 minute before processing the next file

def close_neo4j_connection():
    driver.close()

def main():
    directory_path = './clubs'
    print("Starting to process files in the directory...")
    process_files(directory_path)
    close_neo4j_connection()
    print("All files processed, connection closed.")

if __name__ == "__main__":
    main()
