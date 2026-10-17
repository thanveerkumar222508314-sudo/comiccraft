from pathlib import Path

from app.models import (
    PanelStory,
    ComicLayoutItem,
)


def build_comic_layout(
    stories: list[PanelStory],
    image_paths: list[str],
) -> list[ComicLayoutItem]:

    if len(stories) != len(image_paths):

        raise ValueError(
            "Story and image counts do not match."
        )


    layout = []


    for story, image_path in zip(
        stories,
        image_paths
    ):

        filename = Path(
            image_path
        ).name


        panel = ComicLayoutItem(

            **story.model_dump(),

            image_path=image_path,

            image_url=(
                f"/static/panels/{filename}"
            ),
        )


        layout.append(
            panel
        )


    return layout