# Using Gemini to generate panel-by-panel scene lines.

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import google.generativeai as genai

app = FastAPI()
load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
print("Loaded key:", os.getenv("GEMINI_API_KEY"))

class StoryRequest(BaseModel):
    story: str

@app.post("/generate_scenes/")
async def generate_scenes(req: StoryRequest):
    model = genai.GenerativeModel("models/gemini-2.5-flash")
    prompt = f"""
    Break this story into 6 short comic panel descriptions.
    Each line should vividly describe one visual scene.
    Story: {req.story}
    Output format:
    1. [Scene 1]
    2. [Scene 2]
    ...
    """

    response = model.generate_content(prompt)
    scenes = response.text if hasattr(response, "text") else "No response"

    return {"scenes": scenes}
