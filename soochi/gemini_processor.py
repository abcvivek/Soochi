"""
Gemini processor for Soochi - processes content using Google's Gemini Flash 2.0 model.
This is a separate entrypoint from the OpenAI batch completion system.
"""

import json
import os
import time
import feedparser
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import trafilatura
from google import genai
from openai import OpenAI
from dotenv import load_dotenv
from soochi.logger import logger
from soochi.config import config
from soochi.mongodb_client import MongoDBClient
from soochi.utils import hash_url
from soochi.constants import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    EMBEDDING_METRIC,
    SIMILARITY_THRESHOLD,
    AWS_REGION,
    AWS_CLOUD
)
from pinecone import Pinecone, ServerlessSpec
from notion_client import Client as NotionClient
from pydantic import BaseModel, Field
from typing import Union

# Load environment variables
load_dotenv()

# Initialize Google AI client
gemini_client = genai.Client(api_key=config.google_ai_api_key)

# Initialize OpenAI client for embeddings only
openai_client = OpenAI(api_key=config.openai_api_key)

# Initialize Pinecone client
pinecone_index_name = config.pinecone_index_name
pinecone_client = Pinecone(api_key=config.pinecone_api_key)

# Initialize Notion client
notion_client = NotionClient(auth=config.notion_api_key)

class Idea(BaseModel):
    title: str = Field(..., description="A catchy, descriptive title for the idea")
    type: str = Field(..., description="SaaS, Startup, Open-Source, or General-Project")
    problemStatement: str = Field(..., description="Briefly describe the issue or opportunity the idea addresses")
    solution: str = Field(..., description="Explain the proposed solution breifly in no more than 100 words")
    targetAudience: str = Field(..., description="Identify the primary beneficiaries")
    innovationScore: float = Field(..., description="Measure of idea's innovative potential on a scale of 0-10")
    potentialApplications: str = Field(..., description="Mention areas or scenarios where the idea could be used")
    prerequisites: str = Field(..., description="Note any technologies, datasets, or skills needed")
    additionalNotes: str = Field(..., description="Any supplementary information, trends, or context")

class Response(BaseModel):
    endReason: Union[str, None]
    output: Union[list[Idea], None]

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


def fetch_feeds():
    """Fetch feeds from the configured sources."""
    feed_links = []
    for feed_name, feed_url in config.feeds.items():
        logger.info("*****************")
        logger.info(f"Fetching feed: {feed_name}")
        try:
            feed = feedparser.parse(feed_url)
            logger.info(f"Found total entries: {len(feed.entries)}")
            logger.info("*****************")
            feed_links.extend(process_feed_entries(feed.entries))
        except Exception as e:
            logger.error(f"Error fetching feed {feed_name}: {e}")
    return feed_links


def process_feed_entries(entries):
    """Process feed entries and extract URLs."""
    feed_links = []
    for entry in entries:
        parsed_url = urlparse(entry.link)
        actual_url = parse_qs(parsed_url.query).get('url', [None])[0]
        if actual_url:
            feed_links.append(actual_url)
        else:
            logger.error(f"Invalid URL: {entry.link}")
    return feed_links


def deduplicate_urls(feed_links):
    """Remove duplicate URLs based on their hash."""
    seen_hashes = set()
    new_urls = []
    for url in feed_links:
        url_hash = hash_url(url)
        if url_hash not in seen_hashes:
            seen_hashes.add(url_hash)
            new_urls.append(url)
    return new_urls


def fetch_seen_urls_hash():
    """Fetch hashes of URLs that have already been processed."""
    with MongoDBClient() as mongodb_client:
        seen_urls_hash = mongodb_client.fetch_seen_urls_hash()
        logger.info(f"Seen URLs From DB: {len(seen_urls_hash)}")
        return seen_urls_hash


def deduplicate_urls_from_all_urls(new_urls, seen_urls_hash):
    """Remove URLs that have already been processed."""
    deduped_urls = [url for url in new_urls if hash_url(url) not in seen_urls_hash]
    logger.info(f"Deduped URLs after removing seen URLs from DB: {len(deduped_urls)}")
    return deduped_urls


def extract_url_metadata(urls):
    """Extract metadata from URLs."""
    url_data_list = []
    
    for url in urls:
        try:
            raw_content = trafilatura.fetch_url(url)
            if not raw_content:
                continue
                
            # Extract title and content
            metadata = trafilatura.extract_metadata(raw_content)
                
            title = metadata.title if metadata and metadata.title else "No title"
            
            url_data = {
                "url_hash": hash_url(url),
                "url": url,
                "title": title,
            }
            
            url_data_list.append(url_data)
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {url}: {e}")
    
    return url_data_list


def process_content_with_gemini(deduped_urls):
    """Process content with Google's Gemini model."""
    processed_results = []
    with open('soochi/prompts/idea_extractor.txt', 'r') as prompt_file:
        prompt_content = prompt_file.read()

    # First extract all content
    contents = []
    urls = []
    for url in deduped_urls[0:2]:
        raw_content = trafilatura.fetch_url(url)
        content = trafilatura.extract(raw_content)
        if not content:
            continue
        contents.append(content)
        urls.append(url)
    
    # Process all content with Gemini
    logger.info(f"Processing {len(contents)} URLs with Gemini")
    
    for i, content in enumerate(contents):
        url = urls[i]
        logger.info(f"Processing URL {i+1}/{len(contents)}: {url}")
        
        try:
            # Configure the model
            generation_config = {
                "temperature": 0.5,
                "response_mime_type": "application/json",
                "response_schema": Response,
            }
            
            # Create the prompt
            prompt_parts = [
                {"text": prompt_content},  # System prompt
                {"text": f"Input: {content}\nResponse (JSON):"}  # User content
            ]
            
            # Generate response
            response = gemini_client.models.generate_content(
                model=config.google_ai_model,
                contents=prompt_parts,
                config=generation_config
            )
            
            if response and response.text:
                # Parse the JSON content
                parsed_result = json.loads(response.text)
                
                # Add URL hash to each idea
                if parsed_result.get('output'):
                    for idea in parsed_result['output']:
                        idea['url_hash'] = hash_url(url)
                
                processed_results.append(parsed_result)
            else:
                logger.warning(f"No response text returned from Gemini for URL: {url}")
                
        except Exception as e:
            logger.error(f"Error processing URL with Gemini: {url}, Error: {e}")
    
    return processed_results


def save_results(results):
    """Save results to a JSON file."""
    # create data folder if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")

    file_name = "data/gemini_results.json"
    with open(file_name, 'w') as file:
        json.dump(results, file)
    logger.info(f"Results saved at {file_name}")
    return file_name


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


def find_idea_in_notion(title):
    """Find an idea in Notion by its title using Notion's filter API."""
    logger.debug(f"Searching for idea in Notion: {title}")
    try:
        response = notion_client.databases.query(
            database_id=config.notion_database_id,
            filter={
                "property": "Title",
                "title": {
                    "equals": title
                }
            }
        )
        
        if response["results"]:
            logger.debug(f"Found idea in Notion: {title}")
            return response["results"][0]
        
        logger.debug(f"Idea not found in Notion: {title}")
        return None
    except Exception as e:
        logger.error(f"Error searching for idea in Notion: {e}")
        return None


def fetch_url_metadata(mongodb_client, url_hash):
    """Fetch URL metadata from the seen_urls collection."""
    logger.debug(f"Fetching URL metadata for hash: {url_hash}")
    try:
        url_data = mongodb_client.fetch_url_metadata(url_hash)
        if url_data:
            logger.debug(f"Found URL metadata for hash: {url_hash}")
            return {
                "url": url_data.get("url", ""),
                "title": url_data.get("title", ""),
                "created_at": url_data.get("created_at", "")
            }
        logger.debug(f"URL metadata not found for hash: {url_hash}")
        return {"url": "", "title": "", "created_at": ""}
    except Exception as e:
        logger.error(f"Error fetching URL metadata: {e}")
        return {"url": "", "title": "", "created_at": ""}


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
                # Convert datetime to ISO format string if it's a datetime object
                created_at = url_metadata["created_at"]
                if isinstance(created_at, datetime):
                    created_at = created_at.isoformat()
                
                notion_date = {
                    "date": {
                        "start": created_at
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
                    }
                )
            else:
                # Create new Notion page
                logger.info(f"Creating new idea in Notion: {idea['title']}")
                
                properties = {
                    "Title": {"title": [{"text": {"content": idea['title']}}]},
                    "Count": {"number": 1},
                    "Type": {"rich_text": [{"text": {"content": idea['type']}}]},
                    "Problem Statement": {"rich_text": [{"text": {"content": idea['problemStatement']}}]},
                    "Solution": {"rich_text": [{"text": {"content": idea['solution']}}]},
                    "Target Audience": {"rich_text": [{"text": {"content": idea['targetAudience']}}]},
                    "Innovation Score": {"number": idea['innovationScore']},
                    "Potential Applications": {"rich_text": [{"text": {"content": idea['potentialApplications']}}]},
                    "Prerequisites": {"rich_text": [{"text": {"content": idea['prerequisites']}}]},
                    "Additional Notes": {"rich_text": [{"text": {"content": idea['additionalNotes']}}]},
                }
                
                # Add URL if available
                if url_metadata["url"]:
                    properties["Source URL"] = {"url": url_metadata["url"]}
                
                # Add Source Title if available
                if url_metadata["title"]:
                    properties["Source Title"] = {"rich_text": [{"text": {"content": url_metadata["title"]}}]}
                
                # Add Date if available
                if notion_date:
                    properties["Processed Date"] = notion_date
                
                notion_client.pages.create(
                    parent={"database_id": config.notion_database_id},
                    properties=properties
                )
    except Exception as e:
        logger.error(f"Error writing ideas to Notion: {e}")
        raise


def main():
    """Main function to process content with Gemini."""
    logger.info("Starting Gemini processing")
    try:
        feed_links = fetch_feeds()
        new_urls = deduplicate_urls(feed_links)
        logger.info(f"Total feed count: {len(config.feeds)}")
        logger.info(f"Total URLs: {len(feed_links)}")
        logger.info(f"Deduped URLs: {len(new_urls)}")

        seen_urls_hash = fetch_seen_urls_hash()
        deduped_urls = deduplicate_urls_from_all_urls(new_urls, seen_urls_hash)

        if not deduped_urls:
            logger.info("No new URLs to process")
            return

        # Extract metadata from URLs
        url_data_list = extract_url_metadata(deduped_urls)
        
        # Insert URLs with metadata into database
        with MongoDBClient() as mongodb_client:
            mongodb_client.bulk_insert_seen_urls(url_data_list)

        # Process content with Gemini
        results = process_content_with_gemini(deduped_urls)
        logger.info(f"Processed {len(results)} results")

        # Save results to file
        file_name = save_results(results)

        # Store a reference to the results in MongoDB
        # We'll use a timestamp as a unique identifier
        batch_id = f"gemini-{int(time.time())}"
        
        with MongoDBClient() as mongodb_client:
            mongodb_client.create_batch_job(batch_id)

        logger.info(f"Stored batch ID: {batch_id}")

        # Extract all ideas from the results
        all_ideas = []
        for result in results:
            if result.get('output'):
                all_ideas.extend(result['output'])
        
        logger.info(f"Extracted {len(all_ideas)} ideas for processing")
        
        # Process the ideas
        process_idea_vectors(all_ideas)
        
        # Write to Notion
        with MongoDBClient() as mongodb_client:
            write_ideas_to_notion(all_ideas, mongodb_client)
        
        logger.info("Processing complete")
    except Exception as e:
        logger.error(f"Error in main function: {e}")
        raise


if __name__ == "__main__":
    main()
