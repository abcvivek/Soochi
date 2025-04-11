import json
import os
from openai import OpenAI
from soochi.config import config
from soochi.mongodb_client import MongoDBClient
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from notion_client import Client as NotionClient
from soochi.logger import logger
from soochi.constants import (
    EMBEDDING_DIMENSION,
    EMBEDDING_METRIC,
    SIMILARITY_THRESHOLD,
    EMBEDDING_MODEL,
    BATCH_RESULTS_FILE,
    AWS_REGION,
    AWS_CLOUD
)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=config.openai_api_key)

# Initialize Pinecone client
pinecone_index_name = config.pinecone_index_name
pinecone_client = Pinecone(api_key=config.pinecone_api_key)

# Initialize Notion client
notion_client = NotionClient(auth=config.notion_api_key)

# Check if the index already exists
try:
    pinecone_client.describe_index(pinecone_index_name)
    logger.info(f"Index '{pinecone_index_name}' already exists.")
except Exception as e:
    if "not found" in str(e):
        # Index does not exist, so create it
        pinecone_client.create_index(
            name=pinecone_index_name,
            dimension=EMBEDDING_DIMENSION,
            metric=EMBEDDING_METRIC,
            spec=ServerlessSpec(
                cloud=AWS_CLOUD,
                region=AWS_REGION
            )
        )
        logger.info(f"Index '{pinecone_index_name}' created.")
    else:
        logger.error(f"Error checking index: {e}")

def write_ideas_to_notion(ideas, mongodb_client):
    """Write ideas to Notion database, syncing with Pinecone data."""
    logger.info(f"Writing {len(ideas)} ideas to Notion")
    try:
        for idea in ideas:
            # Fetch URL metadata if url_hash is available
            url_metadata = {"url": "", "title": "", "created_at": ""}
            if idea.get('url_hash'):
                url_metadata = fetch_url_metadata(mongodb_client, idea['url_hash'])
            
            # Format date for Notion if available
            notion_date = None
            if url_metadata["created_at"]:
                # Handle the case where created_at is already a string
                notion_date = {
                    "date": {
                        "start": url_metadata["created_at"]
                    }
                }
            
            # Check if idea already exists in Notion
            existing_page = find_idea_in_notion(idea['title'])
            
            if existing_page:
                # Update existing Notion page
                logger.info(f"Updating existing idea in Notion: {idea['title']}")
                
                # Get the latest count from Pinecone
                index = pinecone_client.Index(pinecone_index_name)
                try:
                    pinecone_data = index.fetch(ids=[idea['title']])
                    if idea['title'] in pinecone_data['vectors']:
                        count = pinecone_data['vectors'][idea['title']]['metadata'].get('count', 1)
                    else:
                        count = 1
                except Exception as e:
                    logger.error(f"Error fetching count from Pinecone: {e}")
                    count = 1
                
                notion_client.pages.update(
                    page_id=existing_page['id'],
                    properties={
                        "Count": {"number": count},
                        "Type": {"rich_text": [{"text": {"content": idea['type']}}]},
                        "Problem Statement": {"rich_text": [{"text": {"content": idea['problemStatement']}}]},
                        "Solution": {"rich_text": [{"text": {"content": idea['solution']}}]},
                        "Target Audience": {"rich_text": [{"text": {"content": idea['targetAudience']}}]},
                        "Innovation Score": {"number": idea['innovationScore']},
                        "Potential Applications": {"rich_text": [{"text": {"content": idea['potentialApplications']}}]},
                        "Prerequisites": {"rich_text": [{"text": {"content": idea['prerequisites']}}]},
                        "Additional Notes": {"rich_text": [{"text": {"content": idea['additionalNotes']}}]},
                        "Source URL": {"url": url_metadata["url"] if url_metadata["url"] else None},
                        "Source Title": {"rich_text": [{"text": {"content": url_metadata["title"]}}] if url_metadata["title"] else []},
                        "Processed Date": notion_date if notion_date else {"date": None}
                    }
                )
            else:
                # Create new Notion page
                logger.info(f"Creating new idea in Notion: {idea['title']}")
                notion_client.pages.create(
                    parent={"database_id": os.getenv("NOTION_DATABASE_ID")},
                    properties={
                        "Title": {"title": [{"text": {"content": idea['title']}}]},
                        "Type": {"rich_text": [{"text": {"content": idea['type']}}]},
                        "Problem Statement": {"rich_text": [{"text": {"content": idea['problemStatement']}}]},
                        "Solution": {"rich_text": [{"text": {"content": idea['solution']}}]},
                        "Target Audience": {"rich_text": [{"text": {"content": idea['targetAudience']}}]},
                        "Innovation Score": {"number": idea['innovationScore']},
                        "Potential Applications": {"rich_text": [{"text": {"content": idea['potentialApplications']}}]},
                        "Prerequisites": {"rich_text": [{"text": {"content": idea['prerequisites']}}]},
                        "Additional Notes": {"rich_text": [{"text": {"content": idea['additionalNotes']}}]},
                        "Count": {"number": 1},
                        "Source URL": {"url": url_metadata["url"] if url_metadata["url"] else None},
                        "Source Title": {"rich_text": [{"text": {"content": url_metadata["title"]}}] if url_metadata["title"] else []},
                        "Processed Date": notion_date if notion_date else {"date": None}
                    }
                )
        logger.info("Successfully wrote ideas to Notion")
    except Exception as e:
        logger.error(f"Error writing to Notion: {e}")
        raise

def find_idea_in_notion(title):
    """Find an idea in Notion by its title using Notion's filter API."""
    logger.debug(f"Searching for idea in Notion: {title}")
    try:
        response = notion_client.databases.query(
            database_id=os.getenv("NOTION_DATABASE_ID"),
            filter={
                "property": "Title",
                "title": {
                    "equals": title
                }
            }
        )
        
        if response["results"]:
            logger.debug(f"Found existing idea in Notion: {title}")
            return response["results"][0]
        
        logger.debug(f"No existing idea found in Notion: {title}")
        return None
    except Exception as e:
        logger.error(f"Error searching Notion: {e}")
        return None

def fetch_url_metadata(mongodb_client, url_hash):
    """Fetch URL metadata from the seen_urls collection."""
    logger.debug(f"Fetching URL metadata for hash: {url_hash}")
    try:
        url_data = mongodb_client.seen_urls.find_one({"url_hash": url_hash})
        if url_data:
            # Handle datetime conversion to string if needed
            created_at = url_data.get("created_at", "")
            if created_at and hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
                
            return {
                "url": url_data.get("url", ""),
                "title": url_data.get("title", ""),
                "created_at": created_at
            }
        logger.warning(f"No URL metadata found for hash: {url_hash}")
        return {"url": "", "title": "", "created_at": ""}
    except Exception as e:
        logger.error(f"Error fetching URL metadata: {e}")
        return {"url": "", "title": "", "created_at": ""}

def save_and_parse_results(result_file_id):
    """Save and parse the results from OpenAI batch job."""
    logger.info(f"Fetching content for result file ID: {result_file_id}")
    result = openai_client.files.content(result_file_id).content
    
    logger.debug(f"Saving results to {BATCH_RESULTS_FILE}")
    with open(BATCH_RESULTS_FILE, 'wb') as file:
        file.write(result)
    
    results = []
    logger.debug("Parsing saved results")
    with open(BATCH_RESULTS_FILE, 'r') as file:
        for line in file:
            json_object = json.loads(line.strip())
            results.append(json_object)

    logger.debug("Processing parsed results")
    results_parsed = []
    for result in results:
        # Extract custom_id which contains the URL hash
        custom_id = result.get('custom_id', '')
        url_hash = custom_id.replace('task-', '') if custom_id.startswith('task-') else ''
        
        # Parse the content
        content = json.loads(result['response']['body']['choices'][0]['message']['content'])
        
        # Add the URL hash to each idea for later lookup
        if content.get('output'):
            for idea in content['output']:
                idea['url_hash'] = url_hash
                
        results_parsed.append(content)

    ideas = []
    for result in results_parsed:
        if result.get('output'):
            ideas.extend(result['output'])
    
    logger.info(f"Successfully parsed {len(ideas)} ideas")
    return ideas

def get_latest_batch_id(mongodb_client):
    """Fetch the latest batch ID from the MongoDB database."""
    logger.debug("Fetching latest batch ID from MongoDB")
    batch_id = mongodb_client.get_latest_batch_id()
    if batch_id:
        logger.info(f"Found latest batch ID: {batch_id}")
        return batch_id
    logger.warning("No batch ID found")
    return None

def check_batch_status(batch_id):
    """Check the status of a batch job from OpenAI."""
    logger.info(f"Checking batch status for ID: {batch_id}")
    batch_status = openai_client.batches.retrieve(batch_id)
    if batch_status.status != "completed" or batch_status.output_file_id is None:
        logger.error(f"Batch {batch_id} failed. Please check the logs in platform.openai.com.")
        return
    logger.info(f"Batch {batch_id} completed successfully")
    return batch_status.output_file_id

def create_embedding(text):
    """Create embedding for the given text using OpenAI."""
    logger.debug(f"Creating embedding for text: {text[:50]}...")
    try:
        embedding = openai_client.embeddings.create(
            input=text,
            model=EMBEDDING_MODEL,
            dimensions=EMBEDDING_DIMENSION
        )
        if embedding.data:
            logger.debug("Successfully created embedding")
            return embedding.data[0].embedding
        logger.warning("No embedding data returned from API")
        return None
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        return None

def process_idea_vectors(ideas):
    """Process ideas and handle vector similarity checks."""
    logger.info(f"Processing vectors for {len(ideas)} ideas")
    index = pinecone_client.Index(pinecone_index_name)
    
    for i, idea in enumerate(ideas, 1):
        logger.debug(f"Processing idea {i}/{len(ideas)}: {idea['title']}")
        embedding = create_embedding(f"{idea['problemStatement']}_{idea['solution']}")
        if not embedding:
            logger.warning(f"Skipping idea {idea['title']} due to embedding failure")
            continue
            
        idea['embeddings'] = embedding
        query_result = index.query(
            vector=idea['embeddings'],
            top_k=5,
            include_metadata=True
        )

        if handle_similar_ideas(index, query_result, idea):
            logger.debug(f"Found similar idea for {idea['title']}")
            continue

        logger.debug(f"Adding new idea to DB: {idea['title']}")
        add_new_idea_to_db(index, idea)

def handle_similar_ideas(index, query_result, idea):
    """Handle similar ideas found in the database."""
    for match_ in query_result['matches']:
        if match_['score'] > SIMILARITY_THRESHOLD:
            logger.info(f"Found similar idea with score {match_['score']} for {idea['title']}")
            match_['metadata']['count'] += 1
            index.update(
                id=match_['id'],
                set_metadata=match_['metadata']
            )
            return True
    return False

def add_new_idea_to_db(index, idea):
    """Add a new idea to the vector database."""
    try:
        index.upsert(
            vectors=[{
                "id": idea['title'],
                "metadata": {
                    "title": idea['title'],
                    "type": idea['type'],
                    "problemStatement": idea['problemStatement'],
                    "solution": idea['solution'],
                    "targetAudience": idea['targetAudience'],
                    "innovationScore": idea['innovationScore'],
                    "potentialApplications": idea['potentialApplications'],
                    "prerequisites": idea['prerequisites'],
                    "additionalNotes": idea['additionalNotes'],
                    "count": 1
                },
                "values": idea['embeddings']
            }]
        )
        logger.info(f"Successfully added new idea: {idea['title']}")
    except Exception as e:
        logger.error(f"Error adding idea to database: {e}")
        raise

def fetch_batch_status():
    """Main function to fetch and process batch status."""
    logger.info("Starting batch status fetch process")
    try:
        with MongoDBClient() as mongodb_client:
            batch_id = get_latest_batch_id(mongodb_client)
            if not batch_id:
                logger.warning("No batch jobs found")
                return

            result_file_id = check_batch_status(batch_id)

            if not result_file_id:
                logger.warning("No result file ID found")
                return
            
            ideas = save_and_parse_results(result_file_id)
            process_idea_vectors(ideas)
            write_ideas_to_notion(ideas, mongodb_client)
            
            logger.info(f"Successfully completed batch processing for {batch_id}")
    except Exception as e:
        logger.error(f"Error processing batch: {str(e)}")
        raise

if __name__ == "__main__":
    fetch_batch_status()
