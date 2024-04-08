import re
from neo4j import GraphDatabase

# Define the queries in a dictionary
queries = {
    "which_clubs_played": {
        "pattern": r"which clubs? has player (.+?) played",
        "query": "MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) WHERE p.name =~ '(?i).*{0}.*' RETURN c.name"
    },
    "players_in_club": {
        "pattern": r"who are the players that have played for club (.+)",
        "query": "MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) WHERE c.name =~ '(?i).*{0}.*' RETURN p.name"
    },
    "club_league": {
        "pattern": r"what league does club (.+) belong to",
        "query": "MATCH (c:Club)-[:IS_IN]->(l:League) WHERE c.name =~ '(?i).*{0}.*' RETURN l.name"
    },
    "players_in_league": {
        "pattern": r"list all players who have played in league (.+)",
        "query": "MATCH (p:Player)-[:PLAYED_FOR]->(:Club)-[:IS_IN]->(l:League) WHERE l.name =~ '(?i).*{0}.*' RETURN DISTINCT p.name"
    },
    "played_both_clubs": {
        "pattern": r"which players have played for both club (.+) and club (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), (p)-[:PLAYED_FOR]->(c2:Club) 
        WHERE c1.name =~ '(?i).*{0}.*' AND c2.name =~ '(?i).*{1}.*' 
        RETURN DISTINCT p.name
        """
    },
    "played_in_clubs": {
        "pattern": r"identify players who have played for clubs (.+), (.+), and (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), (p)-[:PLAYED_FOR]->(c2:Club), (p)-[:PLAYED_FOR]->(c3:Club) 
        WHERE c1.name =~ '(?i).*{0}.*' AND c2.name =~ '(?i).*{1}.*' AND c3.name =~ '(?i).*{2}.*' 
        RETURN DISTINCT p.name
        """
    },
    "most_clubs_in_league": {
        "pattern": r"who has played in the most number of clubs in league (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)-[:IS_IN]->(l:League) 
        WHERE l.name =~ '(?i).*{0}.*' 
        RETURN p.name, COUNT(c) AS clubs_count 
        ORDER BY clubs_count DESC LIMIT 1
        """
    },
    "teammates_of_player": {
        "pattern": r"who were the teammates of player (.+) in club (.+)",
        "query": """
        MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club), (p2:Player)-[:PLAYED_FOR]->(c) 
        WHERE p1.name =~ '(?i).*{0}.*' AND c.name =~ '(?i).*{1}.*' AND p1 <> p2 
        RETURN DISTINCT p2.name
        """
    },
    "players_with_player": {
        "pattern": r"which players have played with player (.+) in any club",
        "query": """
        MATCH (p1:Player)-[:PLAYED_FOR]->(c:Club), (p2:Player)-[:PLAYED_FOR]->(c) 
        WHERE p1.name =~ '(?i).*{0}.*' AND p1 <> p2 
        RETURN DISTINCT p2.name
        """
    },
    "moved_from_X_to_Y": {
        "pattern": r"which players have moved from club (.+) to club (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), (p)-[:PLAYED_FOR]->(c2:Club) 
        WHERE c1.name =~ '(?i).*{0}.*' AND c2.name =~ '(?i).*{1}.*' 
        RETURN DISTINCT p.name
        """
    },
    "played_in_leagues": {
        "pattern": r"who has played in both the (.+) and (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(:Club)-[:IS_IN]->(l1:League), 
              (p)-[:PLAYED_FOR]->(:Club)-[:IS_IN]->(l2:League) 
        WHERE l1.name =~ '(?i).*{0}.*' AND l2.name =~ '(?i).*{1}.*' 
        RETURN DISTINCT p.name
        """
    },
    "PLAYED_FOR_rival_clubs": {
        "pattern": r"identify players who have played for rival clubs (.+) and (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), (p)-[:PLAYED_FOR]->(c2:Club) 
        WHERE c1.name =~ '(?i).*{0}.*' AND c2.name =~ '(?i).*{1}.*' 
        RETURN DISTINCT p.name
        """
    },
    "played_in_1_club": {
        "pattern": r"who played for (.+)",
        "query": "MATCH (p:Player)-[:PLAYED_FOR]->(c:Club) WHERE c.name =~ '(?i).*{0}.*' RETURN p.name"
    },
     "played_in_2_clubs": {
        "pattern": r"who played for (.+) and (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), 
              (p)-[:PLAYED_FOR]->(c2:Club) 
        WHERE c1.name =~ '(?i).*{0}.*' 
          AND c2.name =~ '(?i).*{1}.*' 
        RETURN DISTINCT p.name
        """
    },
    "played_in_3_clubs": {
        "pattern": r"who played for (.+), (.+), and (.+)",
        "query": """
        MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), 
              (p)-[:PLAYED_FOR]->(c2:Club), 
              (p)-[:PLAYED_FOR]->(c3:Club) 
        WHERE c1.name =~ '(?i).*{0}.*' 
          AND c2.name =~ '(?i).*{1}.*' 
          AND c3.name =~ '(?i).*{2}.*' 
        RETURN DISTINCT p.name
        """
    },
    "played_in_4_clubs": {
    "pattern": r"who played for (.+?),\s*(.+?),\s*(.+?),\s*and\s+(.+)",
    "query": """
    MATCH (p:Player)-[:PLAYED_FOR]->(c1:Club), 
          (p)-[:PLAYED_FOR]->(c2:Club), 
          (p)-[:PLAYED_FOR]->(c3:Club), 
          (p)-[:PLAYED_FOR]->(c4:Club) 
    WHERE c1.name =~ '(?i).*{0}.*' 
      AND c2.name =~ '(?i).*{1}.*' 
      AND c3.name =~ '(?i).*{2}.*' 
      AND c4.name =~ '(?i).*{3}.*' 
    RETURN DISTINCT p.name
    """
}
}


def convert_natural_language_to_cypher(input_text):
    # First, remove common leading phrases to isolate club names
    club_list_string = re.sub(r'^who played for ', '', input_text, flags=re.IGNORECASE)

    # Split the club names by 'and' or ',' to support both delimiters
    club_names = re.split(r'\s+and\s+|,\s*', club_list_string.strip())

    # Build the MATCH and WHERE parts of the Cypher query dynamically
    match_clauses = []
    where_clauses = []
    for i, club_name in enumerate(club_names):
        club_var = f"c{i}"
        match_clauses.append(f"(p)-[:PLAYED_FOR]->({club_var})")
        where_clauses.append(f"{club_var}.name =~ '(?i).*{re.escape(club_name)}.*'")

    # Construct the full Cypher query
    cypher_query = f"""
    MATCH {' , '.join(match_clauses)}
    WHERE {' AND '.join(where_clauses)}
    RETURN DISTINCT p.name
    """
    return cypher_query


# Example usage


uri = "bolt://localhost:7687"
username = "neo4j"
password = "ssrgssrg"

driver = GraphDatabase.driver(uri, auth=(username, password))

def run_query(query):
    with driver.session() as session:
        result = session.run(query)
        return [record["p.name"] for record in result]

# Get user input and generate the Cypher query
input_text = input("Enter your query: ")
cypher_query = convert_natural_language_to_cypher(input_text)
print(cypher_query)

if cypher_query != "No matching query found.":
    players = run_query(cypher_query)
    print(players)
else:
    print("No matching query found.")
