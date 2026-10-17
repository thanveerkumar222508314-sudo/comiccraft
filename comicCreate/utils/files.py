from pathlib import Path
import re
import uuid


ROOT_DIR = Path(
    __file__
).resolve().parents[2]


STATIC_DIR = (
    ROOT_DIR /
    "static"
)


PANELS_DIR = (
    STATIC_DIR /
    "panels"
)


EXPORTS_DIR = (
    ROOT_DIR /
    "exports"
)


PANELS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


EXPORTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def safe_filename(
    value: str,
    max_length: int = 60
) -> str:

    value = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        value.strip()
    )


    value = value.strip(
        "_"
    )


    if not value:

        value = "file"


    return value[:max_length]


def unique_filename(
    prefix: str,
    extension: str
) -> str:

    return (
        f"{safe_filename(prefix)}_"
        f"{uuid.uuid4().hex[:10]}."
        f"{extension.lstrip('.')}"
    )