"""Typer CLI for netlist-converter: convert, visualize, db, web commands."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from netlist_converter.config import OutputFormat, get_settings

app = typer.Typer(
    name="netlist",
    help="Convert circuit datasheets/images to netlists and visualize them.",
)
console = Console()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


def _step(label: str, emoji: str = "") -> None:
    prefix = f"{emoji} " if emoji else ""
    console.print(f"  {prefix}[cyan]{label}[/cyan]")


@app.command()
def convert(
    input_file: Path = typer.Argument(..., help="Input PDF or image file path"),
    output: Path = typer.Option(None, "-o", "--output", help="Output file path"),
    fmt: OutputFormat = typer.Option(
        None, "-f", "--format", help="Output format: spice, edif, kicad, json"
    ),
    save_db: bool = typer.Option(True, "--save-db/--no-db", help="Save result to database"),
    debug: bool = typer.Option(False, "--debug", help="Print raw LLM response for inspection"),
) -> None:
    """Analyze a circuit file and generate a netlist."""
    settings = get_settings()
    settings.ensure_directories()

    chosen_format = fmt if fmt is not None else settings.default_output_format

    if output is None:
        from netlist_converter.generators import create_generator
        gen = create_generator(chosen_format)
        output = settings.output_dir / (input_file.stem + gen.file_extension)

    console.rule("[bold]Netlist Converter[/bold]")
    console.print(f"  Input:  [bold]{input_file}[/bold]")
    console.print(f"  Format: [bold]{chosen_format.value}[/bold]")
    console.print(f"  Output: [bold]{output}[/bold]")
    console.print()

    t_start = time.monotonic()

    _step("Loading document...", "[1/5]")
    from netlist_converter.core.document_loader import load_document
    document = load_document(input_file)
    console.print(f"       {document.page_count} page(s) loaded in "
                  f"{time.monotonic() - t_start:.1f}s")

    _step("Initializing LLM provider...", "[2/5]")
    t2 = time.monotonic()
    from netlist_converter.llm import create_llm_provider
    llm = create_llm_provider()
    console.print(f"       Provider ready in {time.monotonic() - t2:.1f}s")

    _step(
        f"Analyzing {document.page_count} page(s) with vision model "
        f"[dim](this is the slow step — model inference)[/dim]",
        "[3/5]",
    )
    console.print("       [dim]Waiting for first token from Ollama...[/dim]")
    t3 = time.monotonic()
    from netlist_converter.core.vision_analyzer import analyze_document
    netlist = analyze_document(document, llm, debug=debug)
    elapsed = time.monotonic() - t3

    if netlist.component_count == 0:
        console.print(
            f"       [yellow]Done in {elapsed:.1f}s — "
            "WARNING: 0 components extracted. "
            "The model may have returned non-JSON text. "
            "Try running with: netlist convert <file> --debug to see raw output.[/yellow]"
        )
    else:
        console.print(
            f"       Done in [bold]{elapsed:.1f}s[/bold] — "
            f"{netlist.component_count} components, {netlist.net_count} nets "
            f"(confidence {netlist.metadata.confidence:.2f})"
        )

    _step("Post-processing...", "[4/5]")
    from netlist_converter.core.component_parser import validate_components
    from netlist_converter.core.connection_parser import validate_nets
    netlist.components = validate_components(netlist.components)
    netlist.nets = validate_nets(netlist.nets, netlist.components)

    _step("Writing netlist file...", "[5/5]")
    from netlist_converter.generators import create_generator
    gen = create_generator(chosen_format)
    written_path = gen.write(netlist, output)

    console.print()
    console.print(f"[green]Netlist written:[/green] {written_path}")
    console.print(f"  Components : {netlist.component_count}")
    console.print(f"  Nets       : {netlist.net_count}")
    console.print(f"  Confidence : {netlist.metadata.confidence:.2f}")
    console.print(f"  Total time : {time.monotonic() - t_start:.1f}s")

    if save_db:
        from netlist_converter.db import SQLiteStore
        store = SQLiteStore(settings.sqlite_db_path)
        cid = store.save_netlist(netlist)
        store.close()
        console.print(f"  DB ID      : {cid}")


@app.command()
def visualize(
    input_path: Path = typer.Argument(..., help="Netlist JSON file or conversion DB ID"),
    output: Path = typer.Option(None, "-o", "--output", help="Output image path"),
    fmt: str = typer.Option("svg", "-f", "--format", help="Image format: svg or png"),
) -> None:
    """Render a netlist as a schematic diagram image."""
    settings = get_settings()
    settings.ensure_directories()

    from netlist_converter.models import Netlist

    if input_path.suffix == ".json":
        netlist = Netlist.load_json(input_path)
    else:
        db_id = int(input_path.stem)
        from netlist_converter.db import SQLiteStore
        store = SQLiteStore(settings.sqlite_db_path)
        netlist = store.get_netlist(db_id)
        store.close()
        if netlist is None:
            console.print(f"[red]Conversion ID {db_id} not found.[/red]")
            raise typer.Exit(code=1)

    if output is None:
        output = settings.output_dir / f"schematic.{fmt}"

    from netlist_converter.generators.image import render_netlist_image, render_netlist_png

    if fmt == "png":
        result_path = render_netlist_png(netlist, output)
    else:
        result_path = render_netlist_image(netlist, output)

    console.print(f"[green]Image saved to:[/green] {result_path}")


@app.command()
def db(
    action: str = typer.Argument("list", help="Action: list, show <id>, delete <id>"),
    record_id: int = typer.Argument(None, help="Conversion ID for show/delete"),
) -> None:
    """Manage the conversion database."""
    settings = get_settings()
    settings.ensure_directories()

    from netlist_converter.db import SQLiteStore
    store = SQLiteStore(settings.sqlite_db_path)

    if action == "list":
        records = store.list_conversions()
        if not records:
            console.print("[yellow]No conversions found.[/yellow]")
            store.close()
            return

        table = Table(title="Conversion History")
        table.add_column("ID", style="cyan")
        table.add_column("Source File")
        table.add_column("Date")
        table.add_column("Model")
        table.add_column("Confidence", justify="right")

        for rec in records:
            table.add_row(
                str(rec.id),
                rec.source_file,
                rec.created_at,
                rec.llm_model,
                f"{rec.confidence:.2f}",
            )
        console.print(table)

    elif action == "show" and record_id is not None:
        netlist = store.get_netlist(record_id)
        if netlist is None:
            console.print(f"[red]ID {record_id} not found.[/red]")
        else:
            console.print(netlist.model_dump_json(indent=2))

    elif action == "delete" and record_id is not None:
        deleted = store.delete_conversion(record_id)
        msg = (
            f"[green]Deleted ID {record_id}.[/green]"
            if deleted
            else f"[red]ID {record_id} not found.[/red]"
        )
        console.print(msg)

    else:
        console.print("[red]Usage: db list | db show <id> | db delete <id>[/red]")

    store.close()


@app.command()
def web() -> None:
    """Start the web UI server."""
    settings = get_settings()
    settings.ensure_directories()

    import uvicorn
    console.print(
        f"[bold]Starting web server at http://{settings.web_host}:{settings.web_port}[/bold]"
    )
    uvicorn.run(
        "netlist_converter.web.app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=False,
    )
