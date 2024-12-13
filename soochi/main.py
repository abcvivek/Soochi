import json
from math import log
import os
import feedparser
from urllib.parse import urlparse, parse_qs
import trafilatura
from openai import OpenAI
from dotenv import load_dotenv
from soochi.logger import logger
from soochi.config import config
from soochi.sqlite3_client import SQLiteClient
from soochi.utils import hash_url

# Load environment variables
load_dotenv()

# Initializing OpenAI client
client = OpenAI(
    api_key=config.openai_api_key
)

IS_TESTING_MODE = False  # Set to True for testing

def fetch_feeds():
    feed_links = []
    for feed_name, feed_url in config.feeds.items():
        logger.info(f"Fetching feed: {feed_name}")
        try:
            feed = feedparser.parse(feed_url)
            logger.info(f"Found total entries: {len(feed.entries)}")
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
    logger.info(f"New URLs: {len(new_urls)}")
    return new_urls


def fetch_seen_urls_hash():
    with SQLiteClient() as sqlite_client:
        seen_urls_hash = sqlite_client.fetch_seen_urls_hash()
        logger.info(f"Seen URLs: {len(seen_urls_hash)}")
        return seen_urls_hash


def deduplicate_urls_from_all_urls(new_urls, seen_urls_hash):
    deduped_urls_hash = [hash_url(url) for url in new_urls if hash_url(url) not in seen_urls_hash]
    logger.info(f"Deduped URLs: {len(deduped_urls_hash)}")
    return deduped_urls_hash


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
                "model": "gpt-4o",
                "temperature": 0.5,
                "response_format": {
                    "type": "json_object"
                },
                "metadata": {
                    "url": url,
                    "source": "RSS"
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
    logger.info(f"Total entry count: {len(feed_links)}")
    logger.info(f"Deduped URLs: {len(new_urls)}")

    seen_urls_hash = fetch_seen_urls_hash()
    deduped_urls_hash = deduplicate_urls_from_all_urls(new_urls, seen_urls_hash)

    if not IS_TESTING_MODE:
        with SQLiteClient() as sqlite_client:
            sqlite_client.bulk_insert_seen_urls(deduped_urls_hash)

    deduped_urls = [url for url in new_urls if hash_url(url) in deduped_urls_hash]

    if not deduped_urls:
        logger.info("No new URLs to process")
        return

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
    with SQLiteClient() as sqlite_client:
        sqlite_client.create_batch_job(batch_job.id)

    logger.info("Batch job created")

    # Delete the local file
    os.remove(file_name)

    logger.info("Local File deleted")

    # Prompts
    """
    1. Finding SaaS/Startup/Opensource/Project Ideas
    2. Finding a profitable idea which could be a simple dropshipping business
    3. Finding Problems and Pain Points and the mention solutions
    4. Unique concepts mentioned
    """


if __name__ == "__main__":
    init()
