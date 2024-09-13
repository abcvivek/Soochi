import typer
from soochi.pre_requesites import pre_check
from rich import print

app = typer.Typer()


@app.command()
def init():
    if not pre_check():
        print("[bold red]Pre-requisites not met. Exiting...[/bold red]")
        exit(1)


if __name__ == "__main__":
    app()
