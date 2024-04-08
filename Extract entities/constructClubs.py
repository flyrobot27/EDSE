import os
from SPARQLWrapper import SPARQLWrapper, JSON
from neo4j import GraphDatabase

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


def fetch_club_and_league(club_wikidata_id):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    query = f"""
    SELECT ?clubLabel ?leagueLabel WHERE {{
        wd:{club_wikidata_id} rdfs:label ?clubLabel;
                                   wdt:P118 ?league.
        ?league rdfs:label ?leagueLabel.
        FILTER(LANG(?clubLabel) = "en" && LANG(?leagueLabel) = "en")
    }}
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()

    if results["results"]["bindings"]:
        result = results["results"]["bindings"][0]
        return {
            'club_name': result['clubLabel']['value'],
            'league_name': result['leagueLabel']['value']
        }
    else:
        return None


def create_club_and_league(club_wikidata_id, club_name, league_name):
    query = """
    MERGE (c:Club {wikidata_id: $wikidata_id, name: $name})
    MERGE (l:League {name: $league_name})
    MERGE (c)-[:IS_IN]->(l)
    RETURN c, l
    """
    parameters = {'wikidata_id': club_wikidata_id, 'name': club_name, 'league_name': league_name}
    records = run_query(query, parameters)
    return records


def process_files(directory_path):
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)

            with open(file_path, 'r') as file:
                for line in file:
                    club_wikidata_id = line.strip()
                    club_and_league = fetch_club_and_league(club_wikidata_id)

                    if club_and_league:
                        records = create_club_and_league(club_wikidata_id, club_and_league['club_name'],
                                                         club_and_league['league_name'])
                        print(records)


def close_neo4j_connection():
    driver.close()


def main():
    directory_path = './clubs'
    process_files(directory_path)
    close_neo4j_connection()


if __name__ == "__main__":
    main()
