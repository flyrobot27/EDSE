import asyncio
import sys


from neo4j import GraphDatabase

session_token = "your_session_token_here"
conversation_id = None


    
uri = "bolt://localhost:7687"
username = "neo4j"
password = "neo4j"

driver = GraphDatabase.driver(uri, auth=(username, password))
def run_query(query):
    with driver.session() as session:
        result = session.run(query)
        return [record.values()[0] for record in result]


                
from re_gpt import SyncChatGPT

# consts
 # Set it to the conversation ID if you want to continue an existing chat or None to create a new chat

# Create ChatGPT instance using the session token
with SyncChatGPT(session_token=session_token) as chatgpt:
    

    # Continue the existing chat using conversation_id or create a new chat if conversation_id is none
    if conversation_id:
        conversation = chatgpt.get_conversation(conversation_id)
    else:
        conversation = chatgpt.create_new_conversation()
    while True:
            user_input = input("Enter your prompt: ")
            
            # Combine the user input with the engineered prompt for context
            engineered_prompt = ("RETURN ONLY CYPHER TEXT, NO MARKDOWN: Given a dataset in Neo4j containing players and clubs, where players have a PLAYED_FOR "
                                 "relationship with clubs, and clubs have an IS_IN relationship indicating the leagues they belong to, capture club names first "
                                 "please generate a Cypher query to answer the following question and do not use LIMIT or size,  or anything: RETURN JUST THE CYPHER QUERY AND NO TEXT ELSE, add ALL club names as REGEXs for example .*Barcelona.*, AND means and, for example who played for real madrid and barcelona means match player where player played_for real madrid and barcelona, don't use OR, use AND.")
            full_prompt = engineered_prompt + user_input
            # Iterate through the messages received from the chatgpt and print it
            response = ""
            for message_chunk in conversation.chat(full_prompt):
                response += message_chunk["content"]
            
            print(response)
            result = run_query(response)
            print(result)




