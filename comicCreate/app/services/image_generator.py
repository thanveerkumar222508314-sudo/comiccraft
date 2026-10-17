import io

import httpx
from PIL import Image

from huggingface_hub import InferenceClient

from app.config import get_settings
from utils.files import PANELS_DIR, unique_filename


DIFFUSERS_PIPELINE = None


def save_image(
    image: Image.Image,
    prefix: str,
) -> str:

    filename = unique_filename(
        prefix,
        "png",
    )

    path = PANELS_DIR / filename

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image.convert("RGB").save(
        path,
        "PNG",
    )

    return str(path)


def generate_huggingface(
    prompt: str,
    prefix: str,
) -> str:

    settings = get_settings()

    if not settings.hf_api_key:
        raise RuntimeError(
            "HF_API_KEY is missing. "
            "Add your Hugging Face access token to .env."
        )

    model = (
        settings.hf_image_model
        or "black-forest-labs/FLUX.1-schnell"
    )

    print(
        f"Generating image with Hugging Face: {model}"
    )

    try:

        client = InferenceClient(
            provider="auto",
            api_key=settings.hf_api_key,
        )

        image = client.text_to_image(
            prompt=prompt,
            model=model,
        )

    except Exception as exc:

        error_text = str(exc)

        if (
            "401" in error_text
            or "Unauthorized" in error_text
            or "Invalid username or password" in error_text
        ):
            raise RuntimeError(
                "Hugging Face authentication failed.\n\n"
                "Your HF_API_KEY is invalid, expired, "
                "incorrectly copied, or does not have "
                "Inference Providers permission.\n\n"
                "Create a valid Hugging Face User Access Token "
                "and put it in your .env file as:\n"
                "HF_API_KEY=hf_your_token_here"
            ) from exc

        raise RuntimeError(
            f"Hugging Face image generation failed: {exc}"
        ) from exc

    if image is None:
        raise RuntimeError(
            "Hugging Face returned no image."
        )

    return save_image(
        image,
        prefix,
    )


def get_diffusers_pipeline():

    global DIFFUSERS_PIPELINE

    if DIFFUSERS_PIPELINE is not None:
        return DIFFUSERS_PIPELINE

    import torch

    from diffusers import StableDiffusionPipeline

    settings = get_settings()

    if (
        settings.diffusers_device == "cuda"
        or (
            settings.diffusers_device == "auto"
            and torch.cuda.is_available()
        )
    ):

        device = "cuda"
        dtype = torch.float16

    else:

        device = "cpu"
        dtype = torch.float32

    print(
        f"Loading Diffusers pipeline on {device}..."
    )

    pipeline = StableDiffusionPipeline.from_pretrained(
        settings.diffusers_model,
        torch_dtype=dtype,
    )

    pipeline = pipeline.to(device)

    DIFFUSERS_PIPELINE = pipeline

    return pipeline


def generate_diffusers(
    prompt: str,
    prefix: str,
) -> str:

    pipeline = get_diffusers_pipeline()

    result = pipeline(
        prompt=prompt,
        num_inference_steps=25,
        guidance_scale=7.0,
        height=768,
        width=768,
    )

    image = result.images[0]

    return save_image(
        image,
        prefix,
    )


def generate_image(
    prompt: str,
    prefix: str = "panel",
) -> str:

    settings = get_settings()

    final_prompt = f"""
{prompt}

High quality comic panel illustration.
Clear storytelling composition.
Consistent character design.
Expressive face.
Cinematic lighting.
Detailed environment.
Professional comic artwork.
No text.
No watermark.
No logo.
""".strip()

    provider = (
        settings.image_provider
        .lower()
        .strip()
    )

    print(
        f"Image provider: {provider}"
    )

    if provider == "huggingface":

        return generate_huggingface(
            final_prompt,
            prefix,
        )

    if provider == "diffusers":

        return generate_diffusers(
            final_prompt,
            prefix,
        )

    raise RuntimeError(
        "IMAGE_PROVIDER must be "
        "'huggingface' or 'diffusers'."
    )