from typing import List

from pydantic import BaseModel, Field, field_validator


class PromptRequest(BaseModel):
    story_prompt: str = Field(
        ...,
        min_length=3,
        max_length=3000
    )

    character_name: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    setting: str = Field(
        ...,
        min_length=1,
        max_length=200
    )

    tone: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    art_style: str = Field(
        ...,
        min_length=1,
        max_length=100
    )

    @field_validator("*")
    @classmethod
    def clean_value(cls, value: str) -> str:
        return value.strip()


class PanelOutline(BaseModel):
    panel_number: int

    title: str

    scene_description: str

    image_prompt: str


class PanelStory(BaseModel):
    panel_number: int

    title: str

    scene_description: str

    caption: str

    narration: str

    dialogue: str = ""

    image_prompt: str


class ComicLayoutItem(PanelStory):
    image_path: str

    image_url: str


class ComicResponse(BaseModel):
    success: bool

    panels: List[ComicLayoutItem]

    pdf_path: str | None = None