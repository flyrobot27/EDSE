# EDSE: Entity Descriptive Search Engine
This repository is for hosting the code required to complete our project: EDSE: Entity Descriptive Search Engine On Eurpoean Football. We have included the [full paper](https://github.com/flyrobot27/EDSE/blob/master/EDSE__Entity_Descriptive_Search_Engine__Final_Report.pdf) at our repository.

## Repository Structure
All codes are written in Python and Jupyter Notebook. All dependencies are listed under `requirements.txt`.\
Currently, the folders are layered in the following structures:

### Extract entities
This folder contains scripts for extracting all of the players and club's textual descriptions. It is expected the data has been processed by [wikiextractor](https://github.com/attardi/wikiextractor). Once processed, use `Extract_player_id.py` to extract the articles corresponding to the player id. The `Wiki_text_extractor.py` is used for extracting the text articles itself for the players. `wikidata.py` is the tool used for extracting the wikipedia id for the relevant players and clubs. Finally, `constructClubs.py` and `constructPlayers.py` will construct the knowledge graph, using the neo4j database.

### Generate Cypher
This session indicates the 3 methods we have used to translate natural language to Cypher queries (a query language used for querying neo4j database).
- `chatgpt_api_to_cypher.py` requires an api key from openai. Replace the `session_token` variable in the code.
- `cypher_generator_trf.py` is the template method. All templates required for it to be functional are under the `templates` folder.
- `regex_cypher.py` uses regular expression rules to try to translate cypher queries

### T5 Training
This folder contains the code we have used to both generate training data for [T5](https://huggingface.co/docs/transformers/en/model_doc/t5).
- `augment_data.py` is used for generating training sentence / query pairs used for fine tuning T5. `augment_data.ipynb` is the Jupyter Notebook version if step-by-step execution is preferred
- `process_data.ipynd` is the code used for translating the [Text-to-CQL](https://github.com/Guoaibo/Text-to-CQL) dataset from Chinese to English
- `T5_Fine_tuning_with_PyTorch.ipynb` is taken from [Shivanandroy](https://github.com/Shivanandroy/T5-Finetuning-PyTorch) who provided an amazing template for T5 fine tuning. Note: A CUDA compatible GPU is highly recommended for these tasks, as CPU training would otherwise take a very long time. We have tested the code to be functional on both a Tesla P100 (With Cuda Version 12) and a Radeon RX 6700XT (With ROCM 6.0) under Ubuntu 22.04 LTS (Kernel 6.5.0).
- `evaluate_t5.ipynb` is used for evaluating the performance of the fine tuned T5 model using both the BLEU score and Gestalt pattern score

### Templates
This folder contains the templates used by the `cypher_generator_trf.py` and `augment_data.py`:
- `sentence_template.json` specifies the type of sentence we are expecting for a given type of question
- `cypher_template.json` specifies the corresponding Cypher query for a given sentence template
- `entity_count.json` specifies the number of entities stated in each template

These templates are used for generating datasets, and is partially used for translating English to Cypher queries.
