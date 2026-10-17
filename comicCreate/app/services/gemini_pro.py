import json
import time
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.models import (
    PanelOutline,
    PanelStory,
)


# ============================================================
# STORY MODELS
# ============================================================
#
# IMPORTANT:
# DO NOT USE gemini-3.1-pro-preview HERE.
#
# Your previous error came from the Pro model quota.
# Story generation now uses Flash models.
#

GEMINI_STORY_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
]


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(
    text: str,
) -> Any:

    text = text.strip()

    if text.startswith("```"):

        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(
            lines
        ).strip()

    try:

        return json.loads(text)

    except json.JSONDecodeError:

        pass

    start = text.find("[")

    end = text.rfind("]")

    if start >= 0 and end > start:

        return json.loads(
            text[start:end + 1]
        )

    raise ValueError(
        "Gemini response did not contain valid JSON."
    )


# ============================================================
# GENERATE STORY
# ============================================================

def generate_story(
    outline: list[PanelOutline],
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> list[PanelStory]:

    settings = get_settings()

    if not settings.gemini_api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    client = genai.Client(
        api_key=settings.gemini_api_key
    )

    # --------------------------------------------------------
    # Convert outline to JSON
    # --------------------------------------------------------

    outline_json = json.dumps(

        [
            panel.model_dump()
            for panel in outline
        ],

        ensure_ascii=False,

        indent=2,
    )

    # --------------------------------------------------------
    # Story prompt
    # --------------------------------------------------------

    prompt = f"""
Expand this comic outline into a complete
five-panel comic story.

Original prompt:
{story_prompt}

Character:
{character_name}

Setting:
{setting}

Tone:
{tone}

Art style:
{art_style}

OUTLINE:

{outline_json}

Return ONLY valid JSON.

Return exactly five objects.

Each object must contain:

panel_number
title
scene_description
caption
narration
dialogue
image_prompt

Keep the same panel numbers.

Keep the same story continuity.

The narration should describe what happens.

The caption should provide a short
comic-style environmental caption.

Dialogue should be short and natural.

If dialogue is not required,
return an empty string.

Keep the main character visually
consistent across all panels.

Make every image_prompt detailed enough
for an AI image generator.

Do not use markdown.
""".strip()

    last_error = None

    # --------------------------------------------------------
    # Try Flash models
    # --------------------------------------------------------

    for model_name in GEMINI_STORY_MODELS:

        print(
            f"Trying Gemini story model: "
            f"{model_name}"
        )

        for attempt in range(1, 4):

            try:

                print(
                    f"Story attempt "
                    f"{attempt}/3"
                )

                response = (
                    client.models.generate_content(

                        model=model_name,

                        contents=prompt,

                        config=(
                            types.GenerateContentConfig(

                                response_mime_type=(
                                    "application/json"
                                ),

                                temperature=0.7,
                            )
                        ),
                    )
                )

                if (
                    response
                    and response.text
                ):

                    print(
                        "Story generation "
                        f"successful using "
                        f"{model_name}"
                    )

                    # ------------------------------------------------
                    # Parse JSON
                    # ------------------------------------------------

                    data = extract_json(
                        response.text
                    )

                    if not isinstance(
                        data,
                        list,
                    ):

                        raise RuntimeError(
                            "Gemini story "
                            "was not a list."
                        )

                    if len(data) != 5:

                        raise RuntimeError(
                            f"Gemini returned "
                            f"{len(data)} story "
                            "panels instead of 5."
                        )

                    # ------------------------------------------------
                    # Validate models
                    # ------------------------------------------------

                    stories = []

                    for index, item in enumerate(
                        data,
                        start=1,
                    ):

                        if not isinstance(
                            item,
                            dict,
                        ):

                            raise RuntimeError(
                                f"Story panel "
                                f"{index} is not "
                                "a JSON object."
                            )

                        story_panel = (
                            PanelStory.model_validate(
                                item
                            )
                        )

                        stories.append(
                            story_panel
                        )

                    return stories

            except Exception as exc:

                last_error = exc

                error_text = str(
                    exc
                )

                print(
                    "Gemini story request "
                    f"failed: {error_text}"
                )

                # ------------------------------------------------
                # 503
                # ------------------------------------------------

                if (
                    "503" in error_text
                    or "UNAVAILABLE"
                    in error_text
                ):

                    if attempt < 3:

                        wait = (
                            2 ** attempt
                        )

                        print(
                            "Gemini temporarily "
                            "unavailable. "
                            f"Retrying in "
                            f"{wait} seconds..."
                        )

                        time.sleep(
                            wait
                        )

                        continue

                    break

                # ------------------------------------------------
                # 429
                # ------------------------------------------------

                if (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED"
                    in error_text
                ):

                    raise RuntimeError(
                        "Gemini story generation "
                        "quota has been exhausted. "
                        "Please wait for the quota "
                        "to reset or use another "
                        "Google AI project."
                    ) from exc

                # ------------------------------------------------
                # 404
                # ------------------------------------------------

                if (
                    "404" in error_text
                    or "NOT_FOUND"
                    in error_text
                ):

                    print(
                        f"Model {model_name} "
                        "is unavailable. "
                        "Trying next model."
                    )

                    break

                # ------------------------------------------------
                # Other errors
                # ------------------------------------------------

                raise RuntimeError(
                    "Gemini story generation "
                    f"failed: {exc}"
                ) from exc

    raise RuntimeError(
        "All Gemini story models failed. "
        f"Last error: {last_error}"
    )