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


class SimpleDialogueRequest(BaseModel):
    scene_description: str
    num_dialogues: int = 2


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
You are a professional comic book writer. Given this scene description, create {req.num_dialogues} ultra-short dialogue lines for comic bubbles.

Scene: {req.scene_description}

CRITICAL RULES:
1. Each dialogue MUST be 1-5 words ONLY (extremely short!)
2. Use comic book style - punchy, impactful phrases
3. Examples of good short dialogue:
   - "Watch out!"
   - "No way!"
   - "He's here..."
   - "Wait!"
   - "Behind you!"

For each dialogue line:
1. Write VERY SHORT dialogue (1-5 words maximum!)
2. Determine the appropriate bubble type:
   - "speech" - Normal talking/conversation
   - "thought" - Internal thoughts (use italics style)
   - "shout" - Yelling, excitement, loud sounds
3. Suggest tail direction:
   - "bottom" - Character speaking from below
   - "top" - Character speaking from above
   - "bottom-left", "bottom-right", "top-left", "top-right" - Angled tails

Output ONLY a valid JSON array. No markdown, no explanation, no code blocks.

Format:
[
  {{
    "text": "Watch out!",
    "bubble_type": "shout",
    "tail_direction": "bottom",
    "font_size": 20
  }},
  {{
    "text": "Too late...",
    "bubble_type": "thought",
    "tail_direction": "top",
    "font_size": 18
  }}
]

Remember: MAXIMUM 5 WORDS per dialogue! Shorter is better!
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

        # Enforce word limit (1-5 words)
        for dialogue in dialogues:
            text = dialogue.get("text", "")
            words = text.split()
            if len(words) > 5:
                dialogue["text"] = " ".join(words[:5])

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
async def generate_dialogue_simple(req: SimpleDialogueRequest):
    """
    Simplified endpoint - just provide scene description.
    Returns short scene summary (10-15 words) and ultra-short dialogues (1-5 words).
    """
    model = genai.GenerativeModel("models/gemini-2.5-flash")

    prompt = f"""
You are a comic book writer. 

Given this scene: {req.scene_description}

Provide:
1. A concise scene description (10-15 words)
2. {req.num_dialogues} ultra-short dialogue lines (1-5 words each)

Output ONLY valid JSON:
{{
  "scene_summary": "Brief 10-15 word description here",
  "dialogues": [
    {{"text": "1-5 words", "bubble_type": "speech"}},
    {{"text": "short text", "bubble_type": "thought"}}
  ]
}}

Bubble types: "speech", "thought", "shout"
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean markdown
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)

        result = json.loads(response_text)

        # Enforce word limits
        scene_words = result.get("scene_summary", "").split()
        if len(scene_words) > 15:
            result["scene_summary"] = " ".join(scene_words[:15])

        for dialogue in result.get("dialogues", []):
            text_words = dialogue.get("text", "").split()
            if len(text_words) > 5:
                dialogue["text"] = " ".join(text_words[:5])

        return {
            "status": "success",
            "scene_summary": result.get("scene_summary", ""),
            "dialogues": result.get("dialogues", []),
            "original_scene": req.scene_description
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "scene_summary": "",
            "dialogues": []
        }


@app.get("/")
async def root():
    return {
        "message": "Dialogue Generation API",
        "version": "2.0",
        "description": "Generates concise scene descriptions (10-15 words) and ultra-short dialogues (1-5 words)",
        "endpoints": {
            "/generate_dialogue/": "POST - Generate dialogue with coordinates",
            "/generate_dialogue_simple/": "POST - Generate scene summary + dialogues",
            "/test": "GET - Test API with sample data",
            "/docs": "API documentation"
        },
        "dialogue_length": "1-5 words per bubble",
        "scene_summary_length": "10-15 words",
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
        num_dialogues=3,
        bubble_positions=[
            {"x": 200, "y": 150, "width": 200},
            {"x": 600, "y": 400, "width": 200},
            {"x": 400, "y": 300, "width": 200}
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
    print("  DIALOGUE GENERATION API v2.0")
    print("=" * 60)
    print("  Port: 8014")
    print("  Features:")
    print("    - Scene summaries: 10-15 words")
    print("    - Dialogues: 1-5 words each")
    print("  Endpoints:")
    print("    - POST /generate_dialogue/")
    print("    - POST /generate_dialogue_simple/")
    print("    - GET /test")
    print("    - GET /docs")
    print("=" * 60)

    uvicorn.run(app, host="127.0.0.1", port=8014)