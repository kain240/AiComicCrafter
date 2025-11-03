# api_text_overlay/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont
import textwrap, os

app = FastAPI()


class TextOverlayRequest(BaseModel):
    image_path: str
    text: str
    output_path: str = "final_panel.png"


@app.post("/add_text/")
async def add_text(req: TextOverlayRequest):
    img = Image.open(req.image_path)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 28)

    lines = textwrap.wrap(req.text, width=30)
    y = img.height - (len(lines) * 35) - 30
    for line in lines:
        draw.text((20, y), line, font=font, fill="white", stroke_fill="black", stroke_width=2)
        y += 35

    img.save(req.output_path)
    return {"status": "success", "image": req.output_path}
