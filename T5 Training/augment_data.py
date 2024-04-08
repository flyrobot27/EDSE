from neo4j import GraphDatabase
from pathlib import Path
import json
import random
import re
from tqdm import tqdm
import multiprocessing
import json
import itertools
import os
import argparse


def get_items(name: str):
    with DRIVER.session() as _:
        items = list()
        result = DRIVER.execute_query(f"match (n:{name}) return n.name")
        for r in result.records:
            if r.get("n.name") is not None:
                items.append(r.get("n.name"))
    
    return items

def validate_query(query: str):
    with DRIVER.session() as _:
        query = "PROFILE " + query
        try:
            DRIVER.execute_query(query)
            return True
        except Exception as e:
            return False


class Sampler:
    def __init__(self, player_list = list(), clubs_list = list(), league_list = list()) -> None:
        self.sampled_player_sentence = dict()
        self.player_set: set = set(player_list).copy()
        self.club_set: set = set(clubs_list).copy()
        self.league_set: set = set(league_list).copy()
    
    def sample(self, tag: str, sentence_id: int, sentence_hash: str):
        extract_pattern = r'<(\w+)_(\w+)>'
        tag = re.match(extract_pattern, tag)
        
        tag_type = tag.group(1).lower()

        if tag_type == "player":
            return self.__sample_from_list(self.player_set, sentence_id, sentence_hash, tag_type)
        elif tag_type == "club":
            return self.__sample_from_list(self.club_set, sentence_id, sentence_hash, tag_type)
        elif tag_type == "league":
            return self.__sample_from_list(self.league_set, sentence_id, sentence_hash, tag_type)
        else:
            raise ValueError("Invalid tag type")
    
    def __sample_from_list(self, sample_set: set, sentence_id: int, sentence_hash: str, tag_type: str):
        already_sampled_item_dict: dict = self.sampled_player_sentence.get(sentence_id, dict())
        dict_hash = hash(sentence_hash) ^ hash(tag_type)


        already_sampled_item: dict = already_sampled_item_dict.get(dict_hash, set())

        valid_samples = sample_set.difference(already_sampled_item)
        try:
            sampled_item = random.choice(tuple(valid_samples)).strip()
        except:
            sampled_item = random.choice(tuple(sample_set)).strip()
 

        already_sampled_item.add(sampled_item)
        already_sampled_item_dict[dict_hash] = already_sampled_item
        self.sampled_player_sentence[sentence_id] = already_sampled_item_dict

        return sampled_item

def extract_tag(sentence: str):
    pattern = r'(<\w+_\w+>)'
    return re.findall(pattern, sentence)

def generate_sentence(sentence_list: list, sentence_id: int, iter_count: int = 5000):
    sampler = Sampler(PLAYER_LIST, CLUB_LIST, LEAGUE_LIST)
    sentence_cypher = list()
    cypher_query = CYPHER_TEMPLATE.get(str(sentence_id))
    for _ in range(iter_count):
        sentence: str = random.choice(sentence_list)
        tags = extract_tag(sentence)

        # make a copy of the cypher query
        sentence_query = cypher_query
        for tag in tags:
            sample_name = sampler.sample(tag, sentence_id, str(hash(sentence)))
            sentence = sentence.replace(tag, sample_name)
            sentence_query = sentence_query.replace(tag, sample_name)

        sentence_cypher.append({
            "query": sentence,
            "cypher": sentence_query
        })
    return sentence_cypher

# Define a function to generate sentences for a given sentence template
def generate_sentence_pool_helper(template_id):
    return generate_sentence(SENTENCE_TEMPLATE[str(template_id)], int(template_id), ITER_COUNT)

def main():
    parser = argparse.ArgumentParser(description="Augment data for T5")
    parser.add_argument("--database_url", type=str, default="bolt://192.168.0.40:7687", help="URL of the Neo4j database")
    parser.add_argument("--data_count", type=int, default=5000, help="Number of data to generate")
    parser.add_argument("--no_validation", action="store_true", help="Skip validation of generated data")

    args = parser.parse_args()

    # Create a connection to the Neo4j database
    global DRIVER
    global ITER_COUNT

    ITER_COUNT = args.data_count
    with GraphDatabase.driver(args.database_url, auth=("neo4j", "neo4j")) as DRIVER:
        DRIVER.verify_connectivity()

        global PLAYER_LIST, CLUB_LIST, LEAGUE_LIST
        PLAYER_LIST = get_items("Player")
        CLUB_LIST = get_items("Club")
        LEAGUE_LIST = get_items("League")

        print("Length of player list:", len(PLAYER_LIST))
        print("Length of club list:",len(CLUB_LIST))
        print("Length of League list:", len(LEAGUE_LIST))

        sentence_template_path = Path("./templates/sentence_template.json")
        cypher_template_path = Path("./templates/cypher_template.json")

        # Load sentence and cypher templates
        global SENTENCE_TEMPLATE, CYPHER_TEMPLATE
        SENTENCE_TEMPLATE = json.load(open(sentence_template_path))
        CYPHER_TEMPLATE = json.load(open(cypher_template_path))

        # Create a multiprocessing pool
        print("Generating augmented data...")
        with multiprocessing.Pool(processes=max((os.cpu_count() - 1), 1)) as pool:
            # Iterate over all sentence templates and call generate_sentence function using multiprocessing
            results = pool.map(generate_sentence_pool_helper, SENTENCE_TEMPLATE.keys())


        combined_result = list(itertools.chain.from_iterable(results))

        # validate result
        # check for duplicate
        if not args.no_validation:
            print("Validating augmentation result")
            known_query = set()
            filtered_result = list()
            for result in tqdm(combined_result):
                cypher = result.get("cypher")
                query = result.get("query")
                if query in known_query:
                    continue
                else:
                    known_query.add(cypher)

                if validate_query(cypher):
                    filtered_result.append(result)
        else:
            filtered_result = combined_result.copy()

    json.dump(filtered_result[:len(filtered_result) // 2], open("generated_sentences_1.json", "w", encoding="utf8"), indent=4, ensure_ascii=False)
    json.dump(filtered_result[len(filtered_result) // 2:], open("generated_sentences_2.json", "w", encoding="utf8"), indent=4, ensure_ascii=False)
    print("Augmented data generated successfully")
    print("Data count:", len(filtered_result))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
