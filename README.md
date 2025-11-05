# AiComicCrafter
story to picture book

# api_story_split
“This FastAPI app takes a story input from the user, sends it to Google Gemini, and returns six short comic panel descriptions.
Each import, class, and function has a role — from validating inputs with Pydantic, securing API keys with dotenv, to generating AI output through Gemini’s generative model(gemini-2.5-flash).”

# api_image_gen
1. “This FastAPI app sends a text prompt to Fal.ai’s Stable Diffusion XL API and returns a generated image URL.
It uses environment variables for secure authentication, Pydantic for input validation, and a try-except block for error handling.
The structure ensures the app is safe, maintainable, and ready to connect with a frontend like React.”
2. “This FastAPI app uses Pollinations.ai to generate AI images from text prompts — fully free, no key needed.
The user sends a POST request with a prompt and style, the app builds a descriptive prompt, encodes it, sends it to Pollinations, downloads the image, and returns both the URL and saved file.
It also has a /styles endpoint listing available art styles.”

# api_text_overlay
This code builds a FastAPI-based backend that allows uploading an image and dynamically adding dialogue bubbles.

It validates bubble data using Pydantic models.

Handles drawing (speech, thought, shout) using Pillow.

Wraps text to fit properly.

Combines everything into a single composited image and saves it.
