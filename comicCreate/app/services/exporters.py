from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from app.models import ComicLayoutItem

from utils.files import (
    EXPORTS_DIR,
    unique_filename,
)


def safe_pdf_text(
    text: str
) -> str:

    replacements = {

        "—": "-",

        "–": "-",

        "“": '"',

        "”": '"',

        "‘": "'",

        "’": "'",

        "…": "...",

        "•": "*",

        "\u00a0": " ",
    }


    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )


    return (
        text
        .encode(
            "latin-1",
            "replace"
        )
        .decode(
            "latin-1"
        )
    )


def save_pdf(
    layout: list[ComicLayoutItem]
) -> str:

    if not layout:

        raise ValueError(
            "Cannot create empty PDF."
        )


    filename = unique_filename(

        "ComicCraft_"
        + datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        ),

        "pdf"
    )


    output_path = (
        EXPORTS_DIR /
        filename
    )


    pdf = FPDF(
        orientation="P",
        unit="mm",
        format="A4"
    )


    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )


    for panel in layout:

        pdf.add_page()


        # Title
        pdf.set_font(
            "Helvetica",
            "B",
            18
        )


        pdf.cell(
            0,
            12,
            safe_pdf_text(
                f"Panel {panel.panel_number}: "
                f"{panel.title}"
            ),
            new_x="LMARGIN",
            new_y="NEXT"
        )


        # Image
        image_file = Path(
            panel.image_path
        )


        if image_file.exists():

            pdf.image(
                str(image_file),
                x=15,
                y=28,
                w=180,
                h=105
            )


        pdf.set_y(140)


        # Scene description
        pdf.set_font(
            "Helvetica",
            "I",
            10
        )


        pdf.multi_cell(
            0,
            6,
            safe_pdf_text(
                panel.scene_description
            )
        )


        # Caption
        pdf.ln(3)

        pdf.set_font(
            "Helvetica",
            "B",
            11
        )

        pdf.multi_cell(
            0,
            6,
            "Caption"
        )


        pdf.set_font(
            "Helvetica",
            "",
            10
        )

        pdf.multi_cell(
            0,
            6,
            safe_pdf_text(
                panel.caption
            )
        )


        # Narration
        pdf.ln(2)

        pdf.set_font(
            "Helvetica",
            "B",
            11
        )

        pdf.multi_cell(
            0,
            6,
            "Narration"
        )


        pdf.set_font(
            "Helvetica",
            "",
            10
        )

        pdf.multi_cell(
            0,
            6,
            safe_pdf_text(
                panel.narration
            )
        )


        # Dialogue
        if panel.dialogue.strip():

            pdf.ln(2)

            pdf.set_font(
                "Helvetica",
                "B",
                11
            )

            pdf.multi_cell(
                0,
                6,
                "Dialogue"
            )


            pdf.set_font(
                "Helvetica",
                "",
                10
            )

            pdf.multi_cell(
                0,
                6,
                safe_pdf_text(
                    panel.dialogue
                )
            )


    pdf.output(
        str(output_path)
    )


    return str(output_path)