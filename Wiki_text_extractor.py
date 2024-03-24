from pathlib import Path
import os
import re
from sortedcontainers import SortedSet
import html

wiki_text_dir = Path("text/")


def process_wikitext(wikitext: Path) -> dict:
    indexed_contents = dict()
    with open(wikitext, 'r', encoding='utf-8') as file:
        doc_pattern = re.compile(r'<doc id="(\d+)" url="([^"]+)" title="([^"]+)">(.+?)</doc>', re.DOTALL)
        for m in doc_pattern.finditer(file.read()):
            try:
                doc_id = m.group(1).strip()
                content_with_tag = html.unescape(m.group(0).strip())

                indexed_contents[doc_id] = content_with_tag
            except:
                continue

    return indexed_contents


def find_player_content(player_id_file: Path, indexed_contents: dict) -> list:
    with open(player_id_file, "r") as f:
        ids = SortedSet(f.readlines())
        total_players_count = len(ids)

    output_list = list()
    for player_id in ids:
        content = indexed_contents.get(player_id.strip(), "")
        if content:
            output_list.append(content)
        else:
            print("Warning: Cannot find Wikipedia article for player with article id: " + str(player_id))
        
        if len(output_list) % 100 == 0:
            print(f"Processed {len(output_list)} out of {total_players_count} players for club: {player_id_file.stem}")

    return output_list

file_processed = 0
indexed_contents = dict()

for wikitext in wiki_text_dir.rglob("*"):
    if not os.path.isfile(wikitext):
        continue
    
    indexed_contents |= process_wikitext(wikitext)

    file_processed += 1

    if file_processed % 100 == 0:
        print("Processed Wiki file: " + str(file_processed))


print("Hash index construction complete")

player_id_folder = Path("wiki_ex_data/")

output_dir = Path("output/")

for id_file in player_id_folder.rglob("*.txt"):
    output_list = find_player_content(id_file, indexed_contents)
    
    folder_name = output_dir / id_file.stem
    folder_name.mkdir(parents=True, exist_ok=True)

    output_file = folder_name / "wiki_00"

    with open(output_file, "w") as f:
        f.writelines(output_list)

print("Complete")
