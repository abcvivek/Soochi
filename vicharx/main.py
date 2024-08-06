import typer

app = typer.Typer()


@app.command()
def init(notion_page_id: str):
    typer.echo("Checking prerequisites...")
    typer.echo("Process completed successfully.")


if __name__ == "__main__":
    app()


# 1. Install black and run black . Add pre-commit hook
# 2. Check if local model is available and running
# 3. Check if notion integration is available
