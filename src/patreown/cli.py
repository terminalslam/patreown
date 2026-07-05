import typer

from patreown import __version__

app = typer.Typer(
    name="patreown",
    help="Personal offline archive tool for Patreon videos you already have access to.",
    invoke_without_command=True,
)


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show the installed Patreown version.",
    ),
) -> None:
    if version:
        typer.echo(f"patreown {__version__}")
        raise typer.Exit

    typer.echo("Run 'patreown --help' to see available commands.")