import typer
from src import prerequisites, link_discovery, content_crawl, content_analysis, output_to_notion

app = typer.Typer()

@app.command()
def run_all(notion_page_id: str):
    """
    Execute the entire workflow: checking prerequisites, fetching links, crawling content,
    analyzing articles, and storing results back in Notion.
    """
    typer.echo("Checking prerequisites...")
    prerequisites.check_local_model()
    prerequisites.check_notion_integration()
    
    typer.echo("Fetching links from Notion...")
    links = link_discovery.get_links_from_notion(notion_page_id)
    
    typer.echo(f"Crawling content from {len(links)} links...")
    articles = content_crawl.crawl_links(links)
    
    typer.echo("Analyzing content...")
    analysis_results = content_analysis.analyze_articles(articles)
    
    typer.echo("Storing results in Notion...")
    output_to_notion.store_analysis(notion_page_id, analysis_results)
    
    typer.echo("Process completed successfully.")

if __name__ == "__main__":
    app()
