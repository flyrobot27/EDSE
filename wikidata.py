import os
import requests

def get_wikidata_id(page_id):
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageprops&format=json&pageids={page_id}"
    response = requests.get(url)
    data = response.json()
    page = next(iter(data['query']['pages'].values()))  # Get the first (and only) page in the response
    return page.get('pageprops', {}).get('wikibase_item', None)

def process_files_in_directory(directory_path):
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            input_file_path = os.path.join(root, file_name)
            output_file_path = os.path.join(root, f"{file_name}_wikidataID")

            with open(input_file_path, 'r') as input_file, open(output_file_path, 'w') as output_file:
                for line in input_file:
                    page_id = line.strip()
                    wikidata_id = get_wikidata_id(page_id)
                    if wikidata_id:
                        output_file.write(f'{wikidata_id} \n')
                        print(f"Wikipedia Page ID: {page_id}, Wikidata ID: {wikidata_id}")

directory_path = './clubs'
process_files_in_directory(directory_path)
