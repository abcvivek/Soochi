import json
import os
import feedparser
from urllib.parse import urlparse, parse_qs
import trafilatura
from openai import OpenAI
from dotenv import load_dotenv
from soochi.logger import logger
from soochi.config import config
from soochi.mongodb_client import MongoDBClient
from soochi.utils import hash_url

# Load environment variables
load_dotenv()

# Initializing OpenAI client
client = OpenAI(
    api_key=config.openai_api_key
)


def fetch_feeds():
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
    seen_hashes = set()
    new_urls = []
    for url in feed_links:
        url_hash = hash_url(url)
        if url_hash not in seen_hashes:
            seen_hashes.add(url_hash)
            new_urls.append(url)
    return new_urls


def fetch_seen_urls_hash():
    with MongoDBClient() as mongodb_client:
        seen_urls_hash = mongodb_client.fetch_seen_urls_hash()
        logger.info(f"Seen URLs From DB: {len(seen_urls_hash)}")
        return seen_urls_hash


def deduplicate_urls_from_all_urls(new_urls, seen_urls_hash):
    deduped_urls = [url for url in new_urls if hash_url(url) not in seen_urls_hash]
    logger.info(f"Deduped URLs after removing seen URLs from DB: {len(deduped_urls)}")
    return deduped_urls


def extract_url_metadata(urls):
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


def create_tasks(deduped_urls):
    tasks = []
    with open('soochi/prompts/idea_extractor.txt', 'r') as prompt_file:
        prompt_content = prompt_file.read()

    for url in deduped_urls[0:2]:
        raw_content = trafilatura.fetch_url(url)
        content = trafilatura.extract(raw_content)
        if not content:
            continue
        task = {
            "custom_id": f"task-{hash_url(url)}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": config.openai_model,
                "temperature": 0.5,
                "response_format": {
                    "type": "json_object"
                },
                "messages": [
                    {
                        "role": "system",
                        "content": prompt_content
                    },
                    {
                        "role": "user",
                        "content": f"""
                            Input: {content}
                            Response (JSON):
                        """
                    }
                ],
            }
        }
        tasks.append(task)
    return tasks


def create_file(tasks):
    # create data folder if it doesn't exist
    if not os.path.exists("data"):
        os.makedirs("data")

    file_name = "data/batch_tasks_idea.jsonl"
    with open(file_name, 'w') as file:
        for obj in tasks:
            file.write(json.dumps(obj) + '\n')
    logger.info(f"File created at {file_name}")
    return file_name


def init():
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

    tasks = create_tasks(deduped_urls)
    logger.info(len(tasks))

    file_name = create_file(tasks)

    batch_file = client.files.create(
        file=open(file_name, "rb"),
        purpose="batch"
    )

    logger.info(batch_file)

    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    logger.info(batch_job)

    # Store the batch jobId in a database
    with MongoDBClient() as mongodb_client:
        mongodb_client.create_batch_job(batch_job.id)

    logger.info("Batch job created")

    # Delete the local file
    os.remove(file_name)

    logger.info("Local File deleted")


if __name__ == "__main__":
    init()
