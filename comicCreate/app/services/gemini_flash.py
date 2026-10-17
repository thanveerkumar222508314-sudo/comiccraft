import json
import re
import time
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.models import PanelOutline


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text: str) -> Any:
    """
    Extract JSON from Gemini response.

    Supports:
    - plain JSON
    - ```json ... ```
    - extra text surrounding JSON
    """

    if not text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    # --------------------------------------------------------
    # Remove markdown code fences
    # --------------------------------------------------------

    if text.startswith("```"):

        lines = text.splitlines()

        if lines:
            lines = lines[1:]

        if (
            lines
            and lines[-1].strip() == "```"
        ):
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # --------------------------------------------------------
    # Try direct JSON
    # --------------------------------------------------------

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        pass

    # --------------------------------------------------------
    # Try JSON array
    # --------------------------------------------------------

    array_start = text.find("[")
    array_end = text.rfind("]")

    if (
        array_start >= 0
        and array_end > array_start
    ):

        try:

            return json.loads(
                text[
                    array_start:
                    array_end + 1
                ]
            )

        except json.JSONDecodeError:
            pass

    # --------------------------------------------------------
    # Try JSON object
    # --------------------------------------------------------

    object_start = text.find("{")
    object_end = text.rfind("}")

    if (
        object_start >= 0
        and object_end > object_start
    ):

        try:

            return json.loads(
                text[
                    object_start:
                    object_end + 1
                ]
            )

        except json.JSONDecodeError:
            pass

    raise ValueError(
        "Gemini response did not contain valid JSON."
    )


# ============================================================
# ERROR HELPERS
# ============================================================

def _get_error_text(
    exc: Exception,
) -> str:

    return str(exc)


def _extract_retry_time(
    error_text: str,
) -> str | None:
    """
    Extract Gemini's suggested retry time.

    Example:

    Please retry in 10h8m29.625671051s.
    """

    match = re.search(
        r"Please retry in\s+([0-9hms.]+)",
        error_text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def _is_invalid_api_key(
    error_text: str,
) -> bool:

    return (
        "API_KEY_INVALID" in error_text
        or "API key not valid" in error_text
        or "API key is invalid" in error_text
    )


def _is_quota_error(
    error_text: str,
) -> bool:

    return (
        "429" in error_text
        or "RESOURCE_EXHAUSTED" in error_text
        or "quota exceeded" in error_text.lower()
        or "quota has been exhausted" in error_text.lower()
    )


def _is_temporary_error(
    error_text: str,
) -> bool:

    return (
        "503" in error_text
        or "UNAVAILABLE" in error_text
        or "temporarily unavailable" in error_text.lower()
    )


# ============================================================
# GEMINI OUTLINE GENERATION
# ============================================================

def generate_outline(
    story_prompt: str,
    character_name: str,
    setting: str,
    tone: str,
    art_style: str,
) -> list[PanelOutline]:

    settings = get_settings()

    # ========================================================
    # API KEY
    # ========================================================

    api_key = (
        settings.gemini_api_key
        if settings.gemini_api_key
        else ""
    ).strip()

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is missing.\n\n"
            "Add a valid Gemini API key to your .env file."
        )

    # --------------------------------------------------------
    # Prevent placeholder key
    # --------------------------------------------------------

    if (
        api_key.startswith("YOUR_")
        or api_key == "YOUR_GEMINI_API_KEY"
    ):

        raise RuntimeError(
            "GEMINI_API_KEY still contains a placeholder.\n\n"
            "Replace it with a real Gemini API key."
        )

    # ========================================================
    # MODEL
    # ========================================================

    model_name = (
        getattr(
            settings,
            "gemini_flash_model",
            None,
        )
        or "gemini-2.5-flash"
    ).strip()

    print(
        f"Using Gemini outline model: {model_name}"
    )

    # ========================================================
    # CREATE CLIENT
    # ========================================================

    try:

        client = genai.Client(
            api_key=api_key
        )

    except Exception as exc:

        raise RuntimeError(
            "Could not create Gemini client.\n\n"
            f"Error: {exc}"
        ) from exc

    # ========================================================
    # PROMPT
    # ========================================================

    prompt = f"""
Create a cohesive five-panel comic outline.

Story prompt:
{story_prompt}

Main character:
{character_name}

Setting:
{setting}

Tone:
{tone}

Art style:
{art_style}

Create exactly five panels.

Return ONLY valid JSON.

The JSON must be an array containing exactly five objects.

Each object must contain:

panel_number
title
scene_description
image_prompt

Rules:

- panel_number must be 1, 2, 3, 4, or 5.
- Use each panel number exactly once.
- Keep the story coherent from beginning to ending.
- Keep the main character visually consistent.
- Make image_prompt detailed and suitable for image generation.
- Include camera composition and important visual details.
- Do not include markdown.
- Do not include explanations outside JSON.
""".strip()

    # ========================================================
    # REQUEST SETTINGS
    # ========================================================

    max_attempts = 3

    response = None
    last_error: Exception | None = None

    # ========================================================
    # GEMINI REQUEST
    # ========================================================

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        print(
            f"Outline attempt "
            f"{attempt}/{max_attempts}"
        )

        try:

            response = client.models.generate_content(

                model=model_name,

                contents=prompt,

                config=types.GenerateContentConfig(

                    temperature=0.8,

                    response_mime_type="application/json",

                ),
            )

            # ------------------------------------------------
            # Validate response
            # ------------------------------------------------

            if not response:

                raise RuntimeError(
                    "Gemini returned no response."
                )

            if not response.text:

                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            print(
                "Gemini outline generation successful."
            )

            break

        # ====================================================
        # ERROR HANDLING
        # ====================================================

        except Exception as exc:

            last_error = exc

            error_text = _get_error_text(
                exc
            )

            print(
                "Gemini outline request failed: "
                f"{error_text}"
            )

            # =================================================
            # INVALID API KEY
            # =================================================

            if _is_invalid_api_key(
                error_text
            ):

                raise RuntimeError(
                    "Gemini API key is invalid.\n\n"

                    "The Google Gemini API rejected "
                    "your API key.\n\n"

                    "Fix:\n"
                    "1. Create a new Gemini API key.\n"
                    "2. Replace GEMINI_API_KEY in .env.\n"
                    "3. Save the .env file.\n"
                    "4. Completely restart the FastAPI server.\n\n"

                    "Do not share your API key publicly."
                ) from exc

            # =================================================
            # 401 AUTHENTICATION
            # =================================================

            if "401" in error_text:

                raise RuntimeError(
                    "Gemini authentication failed.\n\n"
                    "Your GEMINI_API_KEY is invalid, "
                    "expired, or unauthorized.\n\n"
                    "Create a new Gemini API key and "
                    "restart the application."
                ) from exc

            # =================================================
            # 403 PERMISSION
            # =================================================

            if "403" in error_text:

                raise RuntimeError(
                    "Gemini API access was forbidden.\n\n"
                    "Check that your Google project has "
                    "Gemini API access enabled and that "
                    "your API key belongs to that project."
                ) from exc

            # =================================================
            # 429 QUOTA
            #
            # IMPORTANT:
            # DO NOT RETRY 429.
            # =================================================

            if _is_quota_error(
                error_text
            ):

                retry_time = _extract_retry_time(
                    error_text
                )

                if retry_time:

                    message = (
                        "Gemini API quota has been exhausted.\n\n"
                        f"Gemini requested waiting approximately "
                        f"{retry_time} before trying again.\n\n"
                        "This is a Google Gemini quota/billing "
                        "limitation, not a Python code error.\n\n"
                        "You can either:\n"
                        "1. Wait for the quota to reset.\n"
                        "2. Use another Google AI project/API key "
                        "with available quota.\n"
                        "3. Enable billing for the Google AI project."
                    )

                else:

                    message = (
                        "Gemini API quota has been exhausted.\n\n"
                        "This is a Google Gemini quota/billing "
                        "limitation, not a Python code error.\n\n"
                        "Wait for the quota to reset or use "
                        "another Google AI project/API key "
                        "with available quota."
                    )

                raise RuntimeError(
                    message
                ) from exc

            # =================================================
            # 503 TEMPORARY SERVER ERROR
            #
            # RETRY ONLY 503
            # =================================================

            if _is_temporary_error(
                error_text
            ):

                if attempt < max_attempts:

                    wait_time = 2 ** attempt

                    print(
                        "Gemini temporarily unavailable. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(
                        wait_time
                    )

                    continue

                raise RuntimeError(
                    "Gemini service is temporarily "
                    "unavailable after "
                    f"{max_attempts} attempts.\n\n"
                    "Please try again later."
                ) from exc

            # =================================================
            # OTHER ERROR
            # =================================================

            raise RuntimeError(
                "Gemini outline generation failed.\n\n"
                f"{error_text}"
            ) from exc

    # ========================================================
    # ALL ATTEMPTS FAILED
    # ========================================================

    if (
        response is None
        or not response.text
    ):

        raise RuntimeError(
            "Gemini outline generation failed after "
            f"{max_attempts} attempts.\n\n"
            f"Last error: {last_error}"
        )

    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        data = extract_json(
            response.text
        )

    except Exception as exc:

        print(
            "Gemini returned invalid JSON:"
        )

        print(
            response.text
        )

        raise RuntimeError(
            "Gemini returned invalid JSON "
            "for the comic outline."
        ) from exc

    # ========================================================
    # VALIDATE LIST
    # ========================================================

    if not isinstance(
        data,
        list,
    ):

        raise RuntimeError(
            "Gemini outline was not a JSON list."
        )

    # ========================================================
    # VALIDATE FIVE PANELS
    # ========================================================

    if len(data) != 5:

        raise RuntimeError(
            f"Gemini returned {len(data)} panels "
            "instead of exactly 5."
        )

    # ========================================================
    # VALIDATE PANELS
    # ========================================================

    panels: list[PanelOutline] = []

    for index, item in enumerate(
        data,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):

            raise RuntimeError(
                f"Panel {index} is not a "
                "valid JSON object."
            )

        try:

            panel = PanelOutline.model_validate(
                item
            )

        except Exception as exc:

            raise RuntimeError(
                f"Panel {index} failed validation:\n"
                f"{exc}"
            ) from exc

        panels.append(
            panel
        )

    # ========================================================
    # PANEL NUMBER CHECK
    # ========================================================

    panel_numbers = [
        panel.panel_number
        for panel in panels
    ]

    if panel_numbers != [
        1,
        2,
        3,
        4,
        5,
    ]:

        raise RuntimeError(
            "Gemini returned incorrect panel numbers: "
            f"{panel_numbers}"
        )

    # ========================================================
    # SUCCESS
    # ========================================================

    print(
        "Comic outline validated successfully."
    )

    return panels