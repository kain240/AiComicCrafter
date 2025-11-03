# using fal.ai (free Stable Diffusion XL) to create images

from fastapi import FastAPI
from pydantic import BaseModel
import requests, os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

FAL_API_URL = "https://fal.run/fal-ai/flux-pro"
headers = {
    "Authorization": f"Key {os.getenv('FAL_KEY')}",
    "Content-Type": "application/json"
}

class ImageRequest(BaseModel):
    prompt: str
    output_name: str = "panel.png"

@app.post("/generate_image/")
async def generate_image(req: ImageRequest):
    payload = {"prompt": req.prompt}

    try:
        response = requests.post(FAL_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        image_url = data["images"][0]["url"]

        return {
            "status": "success",
            "image_url": image_url
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "details": str(e),
            "response": response.text if "response" in locals() else None,
        }
