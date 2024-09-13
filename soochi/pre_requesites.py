import datetime
import ollama

from soochi.constants import (
    LOCAL_MODEL,
    NOTION_INTERNAL_INTEGRATION_KEY,
    NOTION_PARENT_PAGE_ID,
)
from rich import print

from notion_client import Client


def is_local_model_running(model: str):
    try:
        model_found = False
        running_models = ollama.ps().get("models", [])

        if not running_models:
            print(
                f"Model [bold red]{model}[/bold red] is not running. Please run the model in a new terminal using the command: [bold green]ollama run {model}[/bold green]"
            )
            return False

        for running_model in running_models:
            if running_model["name"] == model:
                model_found = True
                break

        if not model_found:
            print(
                f"Model [bold red]{model}[/bold red] is not running. Please run the model in a new terminal using the command: [bold green]ollama run {model}[/bold green]"
            )

        return model_found
    except Exception as e:
        print(
            "[bold red]Ollama installation not found/running. Please install/start Ollama and try again.[/bold red]"
        )
        return False


def is_notion_integration_available():
    try:
        integration_key = NOTION_INTERNAL_INTEGRATION_KEY
        parent_page_id = NOTION_PARENT_PAGE_ID

        if not (integration_key or parent_page_id):
            print(
                "[bold red]Notion integration key or parent page key not found. Please set the NOTION_INTERNAL_INTEGRATION_KEY and NOTION_PARENT_PAGE_ID environment variable.[/bold red]"
            )
            return False

        client = Client(auth=integration_key)
        page_data = client.pages.retrieve(page_id=parent_page_id)

        block_data = client.blocks.children.list(block_id=parent_page_id)

        # filter block data by type
        child_blocks = [
            block for block in block_data["results"] if block["type"] == "child_page"
        ]

        if not child_blocks:
            print(
                "[bold red]Could not find any child pages in the parent page.[/bold red]"
            )
            return False

        # filter block data by title
        today = datetime.date.today().strftime("%d-%m-%Y")
        todays_page = [
            block
            for block in child_blocks
            if block["child_page"]["title"] == f"{today}-Soochi"
        ]

        if not todays_page:
            print(
                "[bold red]Could not find any child pages with today's date in the parent page.[/bold red]"
            )
            return False

        return True
    except Exception as e:
        print(
            "[bold red]Notion integration key or parent page key not found. Please set the NOTION_INTERNAL_INTEGRATION_KEY and NOTION_PARENT_PAGE_ID environment variable.[/bold red]"
        )
        return False


# Checks whether all the required integrations are available or not
def pre_check():
    local_model_running = is_local_model_running(LOCAL_MODEL)
    if not local_model_running:
        return False

    print(f"Local model [bold green]{LOCAL_MODEL}[/bold green] is running.")

    notion_integration_available = is_notion_integration_available()
    if not notion_integration_available:
        return False

    print("[bold green]Notion integration is available.[/bold green]")

    return True
