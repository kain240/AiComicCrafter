"""
API 4: Dialogue Generation with Bubble Type Detection
Generates contextual dialogue based on scene descriptions and determines bubble types.
Port: 8004
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv
import os
import google.generativeai as genai
import json
import re

app = FastAPI()
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


class DialogueRequest(BaseModel):
    scene_description: str
    num_dialogues: int = 2
    bubble_positions: List[dict]  # Coordinates from bubble_placement.py (API 3)


class DialogueResponse(BaseModel):
    text: str
    x: int
    y: int
    width: int
    bubble_type: str  # "speech", "thought", "shout"
    tail_direction: str  # "bottom", "top", "bottom-left", etc.
    font_size: int


@app.post("/generate_dialogue/")
async def generate_dialogue(req: DialogueRequest):
    """
    Generate dialogue text appropriate for the scene and determine bubble types.

    Takes scene description and bubble positions, returns complete dialogue data
    ready for bubble rendering.
    """
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    prompt = f"""
You are a professional comic book writer. Given this scene description, create {req.num_dialogues} dialogue lines that would appear in comic panels.

Scene: {req.scene_description}

For each dialogue line, you must:
1. Write natural, concise dialogue (maximum 15 words per bubble - short is better!)
2. Determine the appropriate bubble type:
   - "speech" - Normal talking/conversation
   - "thought" - Internal thoughts, pondering, remembering
   - "shout" - Yelling, excitement, surprise, loud sounds
3. Suggest tail direction based on typical comic layout:
   - "bottom" - Character speaking from below
   - "top" - Character speaking from above
   - "bottom-left", "bottom-right" - Angled tails

CRITICAL: Output ONLY a valid JSON array. No markdown, no explanation, no code blocks.

Format:
[
  {{
    "text": "Short dialogue here!",
    "bubble_type": "speech",
    "tail_direction": "bottom",
    "font_size": 20
  }},
  {{
    "text": "Another line here",
    "bubble_type": "thought",
    "tail_direction": "top",
    "font_size": 18
  }}
]

Remember: Keep dialogue SHORT and impactful! Comics use few words.
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean up response - remove markdown code blocks if present
        if "```json" in response_text:
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
        elif "```" in response_text:
            lines = response_text.split("\n")
            # Remove first and last lines if they contain ```
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines)

        response_text = response_text.strip()

        # Try to parse JSON
        try:
            dialogues = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Response text: {response_text}")
            # Fallback: create default dialogues
            dialogues = []
            for i in range(req.num_dialogues):
                dialogues.append({
                    "text": "...",
                    "bubble_type": "speech",
                    "tail_direction": "bottom",
                    "font_size": 20
                })

        # Validate it's a list
        if not isinstance(dialogues, list):
            dialogues = [dialogues] if isinstance(dialogues, dict) else []

    except Exception as e:
        print(f"Gemini API error: {e}")
        # Fallback dialogues
        dialogues = [
                        {
                            "text": "...",
                            "bubble_type": "speech",
                            "tail_direction": "bottom",
                            "font_size": 20
                        }
                    ] * req.num_dialogues

    # Combine generated dialogue with coordinates from bubble_placement API
    result = []
    for i, dialogue in enumerate(dialogues[:req.num_dialogues]):
        if i < len(req.bubble_positions):
            pos = req.bubble_positions[i]

            # Handle both coordinate formats
            x_coord = pos.get("x", 0)
            y_coord = pos.get("y", 0)
            width = pos.get("width", 200)

            result.append({
                "text": dialogue.get("text", "..."),
                "x": x_coord,
                "y": y_coord,
                "width": width,
                "bubble_type": dialogue.get("bubble_type", "speech"),
                "tail_direction": dialogue.get("tail_direction", "bottom"),
                "font_size": dialogue.get("font_size", 20)
            })

    return {
        "status": "success",
        "dialogues": result,
        "scene": req.scene_description,
        "count": len(result)
    }


@app.post("/generate_dialogue_simple/")
async def generate_dialogue_simple(
        scene_description: str,
        num_dialogues: int = 2
):
    """
    Simplified endpoint - just provide scene description.
    Returns dialogue without coordinates (for testing).
    """
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    prompt = f"""
Create {num_dialogues} short dialogue lines (max 15 words each) for this scene: {scene_description}

Output only JSON array:
[
  {{"text": "dialogue here", "bubble_type": "speech"}},
  {{"text": "more dialogue", "bubble_type": "thought"}}
]
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean markdown
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)

        dialogues = json.loads(response_text)

        return {
            "status": "success",
            "dialogues": dialogues,
            "scene": scene_description
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "dialogues": []
        }


@app.get("/")
async def root():
    return {
        "message": "Dialogue Generation API",
        "version": "1.0",
        "description": "Generates contextual dialogue for comic panels with bubble type detection",
        "endpoints": {
            "/generate_dialogue/": "POST - Generate dialogue with coordinates",
            "/generate_dialogue_simple/": "POST - Generate dialogue without coordinates",
            "/test": "GET - Test API with sample data",
            "/docs": "API documentation"
        },
        "bubble_types": ["speech", "thought", "shout"],
        "tail_directions": ["bottom", "top", "bottom-left", "bottom-right", "top-left", "top-right"]
    }


@app.get("/test")
async def test_endpoint():
    """
    Test endpoint with sample data
    """
    sample_request = DialogueRequest(
        scene_description="A brave knight facing a dragon in a mountain cave",
        num_dialogues=2,
        bubble_positions=[
            {"x": 200, "y": 150, "width": 200},
            {"x": 600, "y": 400, "width": 200}
        ]
    )

    result = await generate_dialogue(sample_request)

    return {
        "message": "Test successful!",
        "sample_input": {
            "scene": sample_request.scene_description,
            "num_dialogues": sample_request.num_dialogues
        },
        "sample_output": result
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  DIALOGUE GENERATION API")
    print("=" * 60)
    print("  Port: 8004")
    print("  Endpoints:")
    print("    - POST /generate_dialogue/")
    print("    - GET /test")
    print("    - GET /docs")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8004)