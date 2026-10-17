from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # =========================================================
    # GEMINI
    # =========================================================

    gemini_api_key: str = ""

    gemini_flash_model: str = "gemini-2.5-flash"

    gemini_pro_model: str = "gemini-2.5-flash"

    # =========================================================
    # IMAGE
    # =========================================================

    image_provider: str = "huggingface"

    hf_api_key: str = ""

    hf_image_model: str = (
        "black-forest-labs/FLUX.1-schnell"
    )

    # =========================================================
    # DIFFUSERS
    # =========================================================

    diffusers_model: str = (
        "runwayml/stable-diffusion-v1-5"
    )

    diffusers_device: str = "auto"

    # =========================================================
    # APP
    # =========================================================

    app_name: str = "ComicCraft"

    debug: bool = True

    max_panels: int = 5

    # =========================================================
    # ENV FILE
    # =========================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:

    return Settings()