"""FastAPI routes for the web UI."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from netlist_converter.config import OutputFormat, get_settings

router = APIRouter()

WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render the main upload page."""
    settings = get_settings()
    formats = [f.value for f in OutputFormat]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "formats": formats, "default_format": settings.default_output_format.value},
    )


@router.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    """Render the conversion history page."""
    settings = get_settings()
    settings.ensure_directories()
    from netlist_converter.db import SQLiteStore
    store = SQLiteStore(settings.sqlite_db_path)
    records = store.list_conversions()
    store.close()
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "records": records},
    )


@router.post("/convert", response_class=HTMLResponse)
async def convert(
    request: Request,
    file: UploadFile = File(...),
    output_format: str = Form("spice"),
):
    """Handle file upload and conversion."""
    settings = get_settings()
    settings.ensure_directories()

    upload_path = settings.upload_dir / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    from netlist_converter.llm import create_llm_provider
    llm = create_llm_provider()

    from netlist_converter.core import analyze_file
    netlist = analyze_file(upload_path, llm)

    from netlist_converter.core.component_parser import validate_components
    from netlist_converter.core.connection_parser import validate_nets
    netlist.components = validate_components(netlist.components)
    netlist.nets = validate_nets(netlist.nets, netlist.components)

    fmt = OutputFormat(output_format)
    from netlist_converter.generators import create_generator
    gen = create_generator(fmt)
    output_path = settings.output_dir / (upload_path.stem + gen.file_extension)
    written_path = gen.write(netlist, output_path)

    json_path = settings.output_dir / (upload_path.stem + ".json")
    netlist.save_json(json_path)

    from netlist_converter.db import SQLiteStore
    store = SQLiteStore(settings.sqlite_db_path)
    conversion_id = store.save_netlist(netlist)
    store.close()

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "netlist": netlist,
            "output_file": written_path.name,
            "json_file": json_path.name,
            "conversion_id": conversion_id,
            "format": fmt.value,
        },
    )


@router.get("/download/{filename}")
async def download(filename: str):
    """Download a generated output file."""
    settings = get_settings()
    file_path = settings.output_dir / filename
    if not file_path.exists():
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(str(file_path), filename=filename)


@router.get("/api/netlist/{conversion_id}")
async def get_netlist_api(conversion_id: int):
    """REST API: get netlist JSON by conversion ID."""
    settings = get_settings()
    settings.ensure_directories()
    from netlist_converter.db import SQLiteStore
    store = SQLiteStore(settings.sqlite_db_path)
    netlist = store.get_netlist(conversion_id)
    store.close()
    if netlist is None:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(netlist.model_dump())


@router.post("/api/visualize/{conversion_id}")
async def visualize_api(conversion_id: int):
    """REST API: generate schematic image for a conversion."""
    settings = get_settings()
    settings.ensure_directories()
    from netlist_converter.db import SQLiteStore
    store = SQLiteStore(settings.sqlite_db_path)
    netlist = store.get_netlist(conversion_id)
    store.close()
    if netlist is None:
        return JSONResponse({"error": "Not found"}, status_code=404)

    from netlist_converter.generators.image import render_netlist_image
    output_path = settings.output_dir / f"schematic_{conversion_id}"
    result_path = render_netlist_image(netlist, output_path)
    return FileResponse(str(result_path), filename=result_path.name)
