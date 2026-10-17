import logging
from pathlib import Path

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
)
from fastapi.templating import Jinja2Templates

from app.models import PromptRequest

from app.services.gemini_flash import generate_outline
from app.services.gemini_pro import generate_story
from app.services.image_generator import generate_image
from app.services.layout_builder import build_comic_layout
from app.services.exporters import save_pdf

from utils.files import EXPORTS_DIR


logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(
    directory="templates"
)


# ============================================================
# COMPLETE COMIC GENERATION
# ============================================================

def generate_complete_comic(
    data: PromptRequest,
):

    # --------------------------------------------------------
    # STEP 1: Generate outline
    # --------------------------------------------------------

    logger.info(
        "STEP 1: Generating comic outline..."
    )

    outline = generate_outline(
        story_prompt=data.story_prompt,
        character_name=data.character_name,
        setting=data.setting,
        tone=data.tone,
        art_style=data.art_style,
    )

    logger.info(
        "STEP 1 COMPLETE: Outline generated."
    )

    # --------------------------------------------------------
    # STEP 2: Generate story
    # --------------------------------------------------------

    logger.info(
        "STEP 2: Generating comic story..."
    )

    stories = generate_story(
        outline=outline,
        story_prompt=data.story_prompt,
        character_name=data.character_name,
        setting=data.setting,
        tone=data.tone,
        art_style=data.art_style,
    )

    logger.info(
        "STEP 2 COMPLETE: Story generated."
    )

    # --------------------------------------------------------
    # STEP 3: Generate images
    # --------------------------------------------------------

    logger.info(
        "STEP 3: Generating comic images..."
    )

    image_paths = []

    for panel in stories:

        logger.info(
            "Generating image for panel %s...",
            panel.panel_number,
        )

        image_path = generate_image(
            prompt=panel.image_prompt,
            prefix=(
                f"panel_"
                f"{panel.panel_number}_"
                f"{panel.title}"
            ),
        )

        image_paths.append(
            image_path
        )

        logger.info(
            "Panel %s image generated: %s",
            panel.panel_number,
            image_path,
        )

    logger.info(
        "STEP 3 COMPLETE: All images generated."
    )

    # --------------------------------------------------------
    # STEP 4: Build comic layout
    # --------------------------------------------------------

    logger.info(
        "STEP 4: Building comic layout..."
    )

    layout = build_comic_layout(
        stories,
        image_paths,
    )

    logger.info(
        "STEP 4 COMPLETE: Comic layout built."
    )

    # --------------------------------------------------------
    # STEP 5: Export PDF
    # --------------------------------------------------------

    logger.info(
        "STEP 5: Exporting PDF..."
    )

    pdf_path = save_pdf(
        layout
    )

    logger.info(
        "STEP 5 COMPLETE: PDF created at %s",
        pdf_path,
    )

    return layout, pdf_path


# ============================================================
# HOME
# ============================================================

@router.get(
    "/",
    response_class=HTMLResponse,
)
async def home(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


# ============================================================
# FORM GENERATION
# ============================================================

@router.post(
    "/generate",
    response_class=HTMLResponse,
)
async def generate(
    request: Request,

    story_prompt: str = Form(...),

    character_name: str = Form(...),

    setting: str = Form(...),

    tone: str = Form(...),

    art_style: str = Form(...),
):

    data = PromptRequest(
        story_prompt=story_prompt,
        character_name=character_name,
        setting=setting,
        tone=tone,
        art_style=art_style,
    )

    try:

        layout, pdf_path = (
            generate_complete_comic(
                data
            )
        )

        return templates.TemplateResponse(

            request=request,

            name="comic_preview.html",

            context={
                "layout": layout,
                "pdf_filename": (
                    Path(pdf_path).name
                ),
            },
        )

    except Exception as exc:

        logger.exception(
            "Comic generation failed"
        )

        return templates.TemplateResponse(

            request=request,

            name="index.html",

            context={
                "error": str(exc),
            },

            status_code=500,
        )


# ============================================================
# JSON API
# ============================================================

@router.post(
    "/generate-comic/json"
)
async def generate_comic_json(
    data: PromptRequest,
):

    try:

        layout, pdf_path = (
            generate_complete_comic(
                data
            )
        )

        return JSONResponse(

            content={
                "success": True,

                "panels": [
                    panel.model_dump()
                    for panel in layout
                ],

                "pdf_path": (
                    f"/download/"
                    f"{Path(pdf_path).name}"
                ),
            }
        )

    except Exception as exc:

        logger.exception(
            "JSON comic generation failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# IMAGE TEST
# ============================================================

@router.post(
    "/test-image"
)
async def test_image(
    payload: dict,
):

    prompt = str(
        payload.get(
            "prompt",
            "",
        )
    ).strip()

    if not prompt:

        raise HTTPException(
            status_code=422,
            detail="prompt is required",
        )

    try:

        path = generate_image(
            prompt=prompt,
            prefix="test",
        )

        return {
            "success": True,
            "image_url": (
                f"/static/panels/"
                f"{Path(path).name}"
            ),
        }

    except Exception as exc:

        logger.exception(
            "Image generation failed"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


# ============================================================
# PDF DOWNLOAD
# ============================================================

@router.get(
    "/download/{filename}"
)
async def download(
    filename: str,
):

    safe_name = Path(
        filename
    ).name

    target = (
        EXPORTS_DIR /
        safe_name
    ).resolve()

    exports_dir = (
        EXPORTS_DIR.resolve()
    )

    if not target.exists():

        raise HTTPException(
            status_code=404,
            detail="PDF not found",
        )

    if target.parent != exports_dir:

        raise HTTPException(
            status_code=404,
            detail="Invalid file",
        )

    return FileResponse(
        target,
        media_type="application/pdf",
        filename=target.name,
    )


# ============================================================
# EXPORT SUCCESS
# ============================================================

@router.get(
    "/export-success",
    response_class=HTMLResponse,
)
async def export_success(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={},
    )