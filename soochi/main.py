import json
import feedparser
from urllib.parse import urlparse, parse_qs
import trafilatura
from openai import OpenAI

from soochi.constants import GOOGLE_ALERT_FEEDS
from soochi.sqlite3_client import SQLiteClient
from soochi.utils import hash_url

# Initializing OpenAI client - see https://platform.openai.com/docs/quickstart?context=python
client = OpenAI(
    api_key="<KEY>"
)

def init():

    google_alert_feeds = GOOGLE_ALERT_FEEDS
    feed_links = []

    for feed_name, feed_url in google_alert_feeds.items():
        print(f"Fetching feed: {feed_name}")

        feed = feedparser.parse(feed_url)

        print(f"Found total entries: {len(feed.entries)}")

        for entry in feed.entries:
            # Parse the URL
            parsed_url = urlparse(entry.link)

            # Extract the 'url' parameter, which contains the actual link
            actual_url = parse_qs(parsed_url.query).get('url', [None])[0]

            if actual_url:
                feed_links.append(actual_url)
            else:
                print(f"Invalid URL: {entry.link}")

    print(f"Total feed count: {len(google_alert_feeds)}")
    print(f"Total entry count: {len(feed_links)}")

    # Dedupe links

    # 1. Deduplicate Today's Links

    seen_hashes = set()
    new_urls = []

    for url in feed_links:
        url_hash = hash_url(url)
        if url_hash not in seen_hashes:
            seen_hashes.add(url_hash)
            new_urls.append(url)
       
    print("New URLs: ", len(new_urls))

    # 2. Fetch all the Links

    sqlite_client = SQLiteClient("soochi.db")
    sqlite_client.bulk_delete_seen_urls()

    seen_urls_hash = sqlite_client.fetch_seen_urls_hash()

    print("Seen URLs: ", len(seen_urls_hash))

    # 3. Deduplicate the Today's links from all the links

    deduped_urls_hash = [hash_url(url) for url in new_urls if hash_url(url) not in seen_urls_hash]

    print("Deduped URLs: ", len(deduped_urls_hash))

    # 4: Store Today's deduped links ( Bulk insert )

    # sqlite_client.bulk_insert_seen_urls(deduped_urls_hash)

    sqlite_client.close()

    deduped_urls = [url for url in new_urls if hash_url(url) not in seen_urls_hash]

    print(deduped_urls)


    # Creating an array of json tasks

    tasks = []

    for url in deduped_urls[0:3]:

        # crawl

        raw_content = trafilatura.fetch_url(url)

        content = trafilatura.extract(raw_content)

        if not content:
            continue
        
        task = {
            "custom_id": f"task-{hash_url(url)}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                # This is what you would have in your Chat Completions API call
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "response_format": { 
                    "type": "json_object"
                },
                "messages": [
                    {
                        "role": "system",
                        "content": """
                                You are an expert at analyzing content to extract actionable ideas. Given an article, identify potential SaaS, startup, open-source, 
                                or general project ideas if they are clearly mentioned or can be reasonably inferred. If the article lacks actionable insights, 
                                explicitly state that no ideas were identified. Follow these guidelines:

                                Instructions
                                - Highlight ideas relevant to various domains, such as technology, business, health, environment, social impact or any other applicable field.
                                - Imagine out of the box ideas which is impactful.
                                - Ideas can be research, creative, unmet needs or opportunities with a purpose
                                - Sources of ideas can be explicit mentions, problems or challenges mentioned, emerging trends
                                - Include ideas for both niche and broad markets.
                                - Suggest ideas for different technical and non-technical domains.
                                - Account for varying levels of complexity and scope, from small-scale projects to large ventures.
                                - Balance creativity with feasibility, ensuring ideas are both innovative and practical.
                                - Practice "lateral thinking": Look for unexpected connections and innovative applications
                                - Consider cross-domain innovation potential
                                - Quick validation: Briefly assess initial feasibility and uniqueness

                                Edge Cases
                                - Articles with limited explicit problem statements: Infer issues based on context or trends.
                                - Overly technical or abstract articles: Break down the content into practical applications.
                                - Vague or broad topics: Focus on specific aspects that can inspire actionable ideas.
                                - Articles with multiple unrelated themes: Extract ideas for each significant theme.
                                - Repetition of ideas across sections: Consolidate and refine into a single distinct suggestion.
                                - No Ideas Found: If the article lacks actionable insights, endReason should be "No ideas found"

                                Output Schema reference
                                class Response(BaseModel):
                                    endReason: Union[str, None]
                                    output: Union[list[Idea], None]


                                class Idea(BaseModel):
                                    title: str = Field(..., description="A catchy, descriptive title for the idea")
                                    type: str = Field(..., description="SaaS, Startup, Open-Source, or General Project")
                                    problemStatement: str = Field(..., description="Briefly describe the issue or opportunity the idea addresses")
                                    solution: str = Field(..., description="Explain the proposed solution breifly in no more than 100 words")
                                    targetAudience: str = Field(..., description="Identify the primary beneficiaries")
                                    innovationScore: float = Field(0-10, description="Measure of idea's innovative potential")
                                    readinessLevel: str = Field(..., description="Technology Readiness Level or Market Readiness")
                                    potentialApplications: str = Field(..., description="Mention areas or scenarios where the idea could be used")
                                    prerequisites: str = Field(..., description="Note any technologies, datasets, or skills needed")
                                    additionalNotes: str = Field(..., description="Any supplementary information, trends, or context")
                                """
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

    print(len(tasks))

    # Creating the file

    file_name = "data/batch_tasks_idea.jsonl"

    with open(file_name, 'w') as file:
        for obj in tasks:
            file.write(json.dumps(obj) + '\n')


    print(f"File created at {file_name}")

    batch_file = client.files.create(
        file=open(file_name, "rb"),
        purpose="batch"
    )

    print(batch_file)

    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )

    print(batch_job)

    

    """
    
    1. Prompt Generation - Done
    2. Basic Chat Conversation
    3. Create File
    4. Send Batch Request
    5. Delete File
    6. Response Extraction


    Extracted info will be stored in vector db - pinecone

    We might use Notion as required for UI.
    
    """


    # Prompts
    """
    1. Finding SaaS/Startup/Opensource/Project Ideas
    2. Finding a profitable idea which could be a simple dropshipping business
    3. Finding Problems and Pain Points and the mention solutions
    4. Unique concepts mentioned

    https://chatgpt.com/share/6739c5ab-fecc-8005-acf7-7a4df2b925b9 - Prompt

    https://cookbook.openai.com/examples/batch_processing
    """


if __name__ == "__main__":
    init()

