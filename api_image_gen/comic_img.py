from fastapi import FastAPI
from pydantic import BaseModel
import requests
import urllib.parse

app = FastAPI()

# Pollinations.ai - Completely free, no API key needed!
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"


class ImageRequest(BaseModel):
    prompt: str
    style: str = "manga"
    output_name: str = "panel.png"
    width: int = 1024
    height: int = 1024


@app.post("/generate_image/")
async def generate_image(req: ImageRequest):
    style_prefixes = {
        "manga": "manga style, black and white manga, detailed ink linework, screentone shading, ",
        "sketch": "pencil sketch, hand-drawn sketch, rough lines, graphite texture, ",
        "anime": "anime style, vibrant anime art, cel-shaded, clean lines, ",
        "comic": "comic book style, bold outlines, dynamic shading, ",
        "ink": "ink drawing, traditional ink art, brush strokes, monochrome, ",
        "webtoon": "webtoon style, digital manhwa, clean digital art, "
    }

    style_prefix = style_prefixes.get(req.style, "")
    enhanced_prompt = f"{style_prefix}{req.prompt}"

    # URL encode the prompt
    encoded_prompt = urllib.parse.quote(enhanced_prompt)

    # Build URL with parameters
    image_url = f"{POLLINATIONS_URL}{encoded_prompt}?width={req.width}&height={req.height}&nologo=true"

    try:
        # Download the image
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()

        # Save image locally
        with open(req.output_name, "wb") as f:
            f.write(response.content)

        return {
            "status": "success",
            "image_url": image_url,
            "local_file": req.output_name,
            "style_used": req.style,
            "enhanced_prompt": enhanced_prompt
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "details": str(e)
        }


@app.get("/styles")
async def get_available_styles():
    return {
        "styles": ["manga", "sketch", "anime", "comic", "ink", "webtoon"],
        "note": "Using Pollinations.ai - No API key required!"
    }