import spacy
import spacy.cli
from neo4j import GraphDatabase, Driver
import difflib
import argparse
import numpy as np
from pathlib import Path
import json
import re
from sentence_transformers import SentenceTransformer, util
import contextlib
import warnings
import readline #IMPORTANT, DO NOT REMOVE

warnings.filterwarnings("ignore", category=UserWarning)

class EntityType:
    PLAYER = "Player"
    CLUB = "Club"
    LEAGUE = "League"


def extract_tag(sentence: str):
    pattern = r'(<\w+_\w+>)'
    return re.findall(pattern, sentence)

def dequeue_entity(entity_type: str, entities_copy: dict):
    for e_name, e_type in entities_copy.items():
        if str(e_type).lower().strip() == entity_type.lower().strip():
            entities_copy.pop(e_name)
            return e_name
    else:
        print(entity_type)
        raise ValueError(f"No entity found for the given entity type {entity_type}")
    
def get_items(name: str, driver: Driver):
    with driver.session() as session:
        items = list()
        result = driver.execute_query(f"match (n:{name}) return n.name")
        for r in result.records:
            if r.get("n.name") is not None:
                items.append(r.get("n.name"))
    
    return items

def get_most_similar_item(item: str, items: list):
    most_similar = difflib.get_close_matches(item, items, n=1, cutoff=0)
    if len(most_similar) == 0:
        return None
    return most_similar[0]

def rank_similarity(item: str, club_match: str | None, league_match: str | None):
    club_score = difflib.SequenceMatcher(None, item, club_match).ratio() if club_match is not None else 0
    league_score = difflib.SequenceMatcher(None, item, league_match).ratio() if league_match is not None else 0
    max_type = np.argmax([club_score, league_score])
    if max_type == 0:
        return EntityType.CLUB, club_match
    else:
        return EntityType.LEAGUE, league_match

def named_entity_recognize(document: str, processor: spacy.language.Language, player_list: list, club_list: list, league_list: list):
    return_dict = dict()
    text_db_mapping = dict()
    for ent in processor(document).ents:
        entity_text = ent.text
        entity_type = ent.label_

        if entity_type == "PERSON":
            entity_type = EntityType.PLAYER
            entity_db = get_most_similar_item(entity_text, player_list)
        else:
            club = get_most_similar_item(entity_text, club_list)
            league = get_most_similar_item(entity_text, league_list)
            entity_type, entity_db = rank_similarity(entity_text, club, league)
        
        return_dict[entity_db] = entity_type
        text_db_mapping[entity_text] = entity_db

    # replace the entity in the document with the entity_db
    for entity_orig, entity_db in text_db_mapping.items():
        if entity_db is not None:
            document = document.replace(entity_orig, entity_db)
    return return_dict, document


def input_loop(processor: spacy.language.Language, player_list: list, club_list: list, league_list: list, driver: Driver, args: argparse.Namespace):
    input_sentence = input("Enter a question: ").strip()
    print("Querying...")
    # identify all the name entity
    entities, replaced_input_sentence = named_entity_recognize(input_sentence, processor, player_list, club_list, league_list)

    # count the number of entities for each type
    entity_count = {
        EntityType.PLAYER: 0,
        EntityType.CLUB: 0,
        EntityType.LEAGUE: 0
    }
    for key, entity in entities.items():
        if entity is not None:
            entity_count[entity] += 1
        else:
            # returns that the entity is currently not in database
            raise KeyError(f"Entity {key} not found in database", key)

    found_clubs = [key for key, value in entities.items() if value == EntityType.CLUB]
    found_players = [key for key, value in entities.items() if value == EntityType.PLAYER]
    found_leagues = [key for key, value in entities.items() if value == EntityType.LEAGUE]

    if args.debug:
        print("Entities found: ")
        print(f"Clubs: {found_clubs}")
        print(f"Players: {found_players}")
        print(f"Leagues: {found_leagues}")
        print("Query: ", replaced_input_sentence)

    # load the templates
    entity_count_template_path: Path = args.entity_count_file
    cypher_query_template_path: Path = args.cypher_query_file
    sentence_template_path: Path = args.sentence_template_file

    entity_count_template = json.load(entity_count_template_path.open("r"))
    cypher_template = json.load(cypher_query_template_path.open("r"))
    sentence_template = json.load(sentence_template_path.open("r"))

    if not (len(entity_count_template) == len(cypher_template) == len(sentence_template)):
        raise KeyError("Entity Template definition mismatch. Exiting...")
    
    # find the template that matches the entity count
    template_ids = list()
    for key, value in entity_count_template.items():
        if value == entity_count:
            template_ids.append(key)

    if len(template_ids) == 0:
        # fall back to chatgpt or something
        raise ValueError("No template found for the given entity count", {"Player": found_players, "Club": found_clubs, "League": found_leagues})
    
    if args.debug:
        print("Template IDs: ", template_ids)

    # generate the sentences for the given template id
    potential_sentences = dict()
    sentence_tag_values = dict()

    for tid in template_ids:
        sentences: list = sentence_template[tid]
        if not isinstance(sentences, list) or len(sentences) == 0:
            raise ValueError("No sentence found for the given template id")
        
        for s in sentences:
            tags = extract_tag(s)
            inserted_sentence = s
            entities_copy = entities.copy()
            tag_values = dict()
            for tag in tags:
                entity_type, _ = tag[1:-1].split("_")
                entity = dequeue_entity(entity_type, entities_copy)
                inserted_sentence = inserted_sentence.replace(tag, entity)
                tag_values[tag] = entity
            
            sentence_tag_values[inserted_sentence] = tag_values
            potential_sentences[inserted_sentence] = tid

    if args.debug:
        print("loading model...")
    with contextlib.redirect_stdout(None):
        model = SentenceTransformer("all-MiniLM-L6-v2")
    
    # now find the most similar sentence
    s = list(potential_sentences.keys())

    embeddings = model.encode(s, convert_to_tensor=True)
    input_embedding = model.encode([replaced_input_sentence], convert_to_tensor=True)

    cosine_scores = util.pytorch_cos_sim(input_embedding, embeddings)[0].cpu()

    # find the index of the highest scored sentence
    highest_score_index = np.argmax(cosine_scores)
    # find the highest score, and see if it exceed threadhold
    highest_score = cosine_scores[highest_score_index]
    if highest_score < 0.5:
        raise ValueError("No template exists for the given input sentence")
    elif args.debug:
        print(f"Similarity Score: {highest_score}")

    # find the template id and tags
    template_id = potential_sentences[s[highest_score_index]]
    tags = sentence_tag_values[s[highest_score_index]]
    if args.debug:
        print(f"Query sentence: {s[highest_score_index]}")
        print(f"Template id: {template_id}")

    # obtain the cypher query with appropriate entities
    cypher_query = cypher_template[str(template_id)]
    for tag, entity in tags.items():
        cypher_query = cypher_query.replace(tag, entity)

    if args.debug:
        print("Cypher Query: ", cypher_query)

    # obtain result and print
    result = driver.execute_query(cypher_query)
    print("Results:")

    # count number of digits in the length of the result
    justify_length = len(str(len(result.records)))

    for number, record in enumerate(result.records):
        name = record.values()[0]
        print(f"{(number + 1):>{justify_length}}: {name}")
    print()
    return


def main():
    parser = argparse.ArgumentParser(description="Cypher query generator")
    parser.add_argument("-H", "--host", type=str, default="192.168.0.40", metavar="", help="The host of the Neo4j database")
    parser.add_argument("-p", "--port", type=int, default="7687", metavar="", help="The port of the Neo4j database")
    parser.add_argument("-u", "--username", type=str, default="neo4j", metavar="", help="The username of the Neo4j database")
    parser.add_argument("-P", "--password", type=str, default="neo4j", metavar="", help="The password of the Neo4j database")

    parser.add_argument("-e", "--entity-count-file", type=Path, default=Path("templates/entity_count.json"), metavar="", help="The file to entity count definition")
    parser.add_argument("-c", "--cypher-query-file", type=Path, default=Path("templates/cypher_template.json"), metavar="", help="The file to cypher query template definition")
    parser.add_argument("-s", "--sentence-template-file", type=Path, default=Path("templates/sentence_template.json"), metavar="", help="The file to sentence template definition")

    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    Path(args.entity_count_file).resolve(strict=True)
    Path(args.cypher_query_file).resolve(strict=True)
    Path(args.sentence_template_file).resolve(strict=True)

    print("Connecting to neo4j...")
    with GraphDatabase.driver(f"bolt://{args.host}:{args.port}", auth=(args.username, args.password)) as driver:
        driver.verify_connectivity()

        player_list = get_items(EntityType.PLAYER, driver)
        club_list = get_items(EntityType.CLUB, driver)
        league_list = get_items(EntityType.LEAGUE, driver)

        print("Trying to load model...")
        try:
            processor = spacy.load("en_core_web_trf")
        except:
            print("Downloading the model...")
            spacy.cli.download("en_core_web_trf")
            processor = spacy.load("en_core_web_trf")
        
        print("Complete!")

        while True:
            try:
                input_loop(processor, player_list, club_list, league_list, driver, args)
            except Exception as e:
                print(e)

if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(e)
        exit(1)
    except KeyboardInterrupt:
        print("Exiting....")
        exit(0)