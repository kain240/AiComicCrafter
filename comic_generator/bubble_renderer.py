from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
import io
import math
import json

app = FastAPI()


class DialogueBubble(BaseModel):
    text: str
    x: int
    y: int
    width: Optional[int] = 200
    bubble_type: str = "speech"
    tail_direction: str = "bottom"
    font_size: Optional[int] = 20


def draw_speech_bubble(draw, x, y, width, height, tail_direction):
    bbox = [x - width // 2, y - height // 2, x + width // 2, y + height // 2]  # [left, top, right, bottom]
    draw.ellipse(bbox, fill="white", outline="black", width=3)

    if "bottom" in tail_direction:
        tail_x = x - 20 if "left" in tail_direction else x + 20 if "right" in tail_direction else x
        tail_points = [
            (x - 15, y + height // 2),
            (tail_x, y + height // 2 + 30),
            (x + 15, y + height // 2)
        ]
        draw.polygon(tail_points, fill="white", outline="black")
    elif "top" in tail_direction:
        tail_x = x - 20 if "left" in tail_direction else x + 20 if "right" in tail_direction else x
        tail_points = [
            (x - 15, y - height // 2),
            (tail_x, y - height // 2 - 30),
            (x + 15, y - height // 2)
        ]
        draw.polygon(tail_points, fill="white", outline="black")


def draw_thought_bubble(draw, x, y, width, height):
    bbox = [x - width // 2, y - height // 2, x + width // 2, y + height // 2]
    draw.ellipse(bbox, fill="white", outline="black", width=3)

    circle1 = [x - 30, y + height // 2 + 10, x - 10, y + height // 2 + 30]
    circle2 = [x - 50, y + height // 2 + 30, x - 35, y + height // 2 + 45]
    draw.ellipse(circle1, fill="white", outline="black", width=2)
    draw.ellipse(circle2, fill="white", outline="black", width=2)


def draw_shout_bubble(draw, x, y, width, height):
    points = []
    num_spikes = 16
    for i in range(num_spikes):
        angle = (2 * math.pi * i) / num_spikes
        if i % 2 == 0:
            r = max(width, height) // 2
        else:
            r = max(width, height) // 2 + 15
        px = x + r * math.cos(angle)
        py = y + r * math.sin(angle)
        points.append((px, py))

    draw.polygon(points, fill="white", outline="black", width=3)


def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width"""
    words = text.split()
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    return lines


@app.post("/add_bubbles/")
async def add_dialogue_bubbles(
        image: UploadFile = File(...),
        bubbles: str = Form(...)
):

    print(f"Received bubbles parameter: {bubbles}")

    if not bubbles:
        return {
            "status": "error",
            "message": "No bubbles parameter provided",
            "bubbles_added": 0
        }

    try:
        bubbles_data = json.loads(bubbles)
        print(f"Parsed bubbles data: {bubbles_data}")
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "message": f"Invalid JSON format: {str(e)}",
            "bubbles_received": bubbles,
            "bubbles_added": 0
        }

    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")  # open as PIL img, and add Transparency(A)

    if not bubbles_data or len(bubbles_data) == 0:
        return {
            "status": "warning",
            "message": "Bubbles array is empty",
            "bubbles_data_received": bubbles_data,
            "bubbles_added": 0
        }

    overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)


    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

    for bubble_data in bubbles_data:
        bubble = DialogueBubble(**bubble_data)

        # Wrap text
        max_text_width = bubble.width - 40
        try:
            custom_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", bubble.font_size)
        except:
            try:
                custom_font = ImageFont.truetype("arial.ttf", bubble.font_size)
            except:
                custom_font = font

        lines = wrap_text(bubble.text, custom_font, max_text_width)

        # Calculate bubble height based on text
        line_height = bubble.font_size + 5
        text_height = len(lines) * line_height
        bubble_height = text_height + 40

        # Draw bubble based on type
        if bubble.bubble_type == "speech":
            draw_speech_bubble(draw, bubble.x, bubble.y, bubble.width, bubble_height, bubble.tail_direction)
        elif bubble.bubble_type == "thought":
            draw_thought_bubble(draw, bubble.x, bubble.y, bubble.width, bubble_height)
        elif bubble.bubble_type == "shout":
            draw_shout_bubble(draw, bubble.x, bubble.y, bubble.width, bubble_height)
        else:
            bbox = [bubble.x - bubble.width // 2, bubble.y - bubble_height // 2,
                    bubble.x + bubble.width // 2, bubble.y + bubble_height // 2]
            draw.ellipse(bbox, fill="white", outline="black", width=2)

        # Draw text
        y_offset = bubble.y - text_height // 2
        for line in lines:
            bbox = custom_font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            text_x = bubble.x - text_width // 2
            draw.text((text_x, y_offset), line, fill="black", font=custom_font)
            y_offset += line_height

    # compose the overlay onto the original image
    img = Image.alpha_composite(img, overlay)
    final_img = img.convert("RGB")

    output_buffer = io.BytesIO()
    final_img.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    # Save locally
    output_name = "manga_with_bubbles.png"
    final_img.save(output_name)

    return {
        "status": "success",
        "output_file": output_name,
        "bubbles_added": len(bubbles_data),
        "message": f"Successfully added {len(bubbles_data)} bubble(s)"
    }


@app.get("/")
async def root():
    return {
        "message": "Dialogue Bubble API is running!",
        "endpoints": {
            "/add_bubbles/": "POST - Add dialogue bubbles to image",
            "/docs": "API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8005)