"""
Main Orchestrator API - Coordinates all comic generation services
Port: 8000
This API combines all microservices to generate a complete comic book
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
from PIL import Image
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os
from datetime import datetime

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Endpoints Configuration
API_SERVICES = {
    "scene_generator": "http://localhost:8001/generate_scenes/",
    "image_generator": "http://localhost:8002/generate_image/",
    "bubble_placement": "http://localhost:8003/detect_bubble_positions/",
    "dialogue_generator": "http://localhost:8004/generate_dialogue/",
    "bubble_renderer": "http://localhost:8005/add_bubbles/"
}


class ComicBookRequest(BaseModel):
    story: str
    style: str = "manga"
    num_panels: int = 6
    num_bubbles: int = 2
    width: int = 1024
    height: int = 1024


class PanelData(BaseModel):
    scene: str
    image_path: str
    image_url: Optional[str] = None
    bubbles: List[dict] = []


def parse_scenes_from_text(scenes_text: str, num_panels: int) -> List[str]:
    """Extract scene descriptions from numbered list"""
    lines = scenes_text.strip().split('\n')
    scenes = []

    for line in lines:
        line = line.strip()
        # Match lines starting with numbers like "1.", "2.", etc.
        if line and (line[0].isdigit() or line.startswith('-')):
            # Remove numbering and clean up
            scene = line.split('.', 1)[-1].strip()
            if scene:
                scenes.append(scene)

    # Return exactly num_panels scenes
    return scenes[:num_panels]


async def generate_scenes(story: str, num_panels: int) -> List[str]:
    """Step 1: Generate scene descriptions using Gemma"""
    print(f"\n[STEP 1] Generating {num_panels} scenes from story...")

    try:
        response = requests.post(
            API_SERVICES["scene_generator"],
            json={"story": story},
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        scenes_text = data.get("scenes", "")
        scenes = parse_scenes_from_text(scenes_text, num_panels)

        print(f"✓ Generated {len(scenes)} scenes")
        return scenes

    except Exception as e:
        print(f"✗ Scene generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scene generation failed: {str(e)}")


async def generate_image(prompt: str, style: str, output_name: str, width: int, height: int) -> dict:
    """Step 2: Generate image from scene description"""
    print(f"  [STEP 2] Generating image: {output_name}")

    try:
        response = requests.post(
            API_SERVICES["image_generator"],
            json={
                "prompt": prompt,
                "style": style,
                "output_name": output_name,
                "width": width,
                "height": height
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()

        print(f"  ✓ Image generated: {output_name}")
        return data

    except Exception as e:
        print(f"  ✗ Image generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")


async def detect_bubble_positions(image_path: str, num_bubbles: int) -> List[dict]:
    """Step 3: Detect optimal bubble placement positions"""
    print(f"  [STEP 3] Detecting {num_bubbles} bubble positions...")

    if num_bubbles == 0:
        return []

    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'num_bubbles': num_bubbles,
                'visualize': False
            }

            response = requests.post(
                API_SERVICES["bubble_placement"],
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

        positions = result.get('placements', [])
        print(f"  ✓ Found {len(positions)} bubble positions")
        return positions

    except Exception as e:
        print(f"  ✗ Bubble detection failed: {e}")
        # Return empty list instead of failing
        return []


async def generate_dialogue(scene: str, num_bubbles: int, bubble_positions: List[dict]) -> List[dict]:
    """Step 4: Generate contextual dialogue"""
    print(f"  [STEP 4] Generating {num_bubbles} dialogues...")

    if num_bubbles == 0 or not bubble_positions:
        return []

    try:
        response = requests.post(
            API_SERVICES["dialogue_generator"],
            json={
                "scene_description": scene,
                "num_dialogues": num_bubbles,
                "bubble_positions": bubble_positions
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json()

        dialogues = data.get('dialogues', [])
        print(f"  ✓ Generated {len(dialogues)} dialogues")
        return dialogues

    except Exception as e:
        print(f"  ✗ Dialogue generation failed: {e}")
        return []


async def add_bubbles_to_image(image_path: str, bubbles: List[dict], output_path: str) -> str:
    """Step 5: Add dialogue bubbles to image"""
    print(f"  [STEP 5] Adding {len(bubbles)} bubbles to image...")

    if not bubbles:
        print(f"  → No bubbles to add, using original image")
        return image_path

    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {'bubbles': json.dumps(bubbles)}

            response = requests.post(
                API_SERVICES["bubble_renderer"],
                files=files,
                data=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

        # The bubble renderer saves the file
        rendered_file = result.get('output_file', 'manga_with_bubbles.png')

        # Rename to our desired output path
        if os.path.exists(rendered_file) and rendered_file != output_path:
            os.rename(rendered_file, output_path)

        print(f"  ✓ Bubbles added: {output_path}")
        return output_path

    except Exception as e:
        print(f"  ✗ Bubble rendering failed: {e}")
        return image_path  # Return original if failed


def create_comic_book_pdf(panels: List[PanelData], output_filename: str) -> str:
    """Step 6: Combine all panels into a PDF comic book"""
    print(f"\n[STEP 6] Creating comic book PDF with {len(panels)} panels...")

    try:
        # Create PDF
        pdf_path = f"output/{output_filename}"
        os.makedirs("output", exist_ok=True)

        c = canvas.Canvas(pdf_path, pagesize=A4)
        page_width, page_height = A4

        # Title page
        c.setFont("Helvetica-Bold", 36)
        c.drawCentredString(page_width / 2, page_height - 100, "Comic Book")
        c.setFont("Helvetica", 14)
        c.drawCentredString(page_width / 2, page_height - 150, f"Generated on {datetime.now().strftime('%Y-%m-%d')}")

        # Add border to title page
        c.setStrokeColorRGB(0, 0, 0)  # Black color
        c.setLineWidth(2)  # Border thickness
        c.rect(10, 10, page_width - 20, page_height - 20, fill=0)

        c.showPage()

        # Layout configuration for 2x2 grid
        panels_per_page = 4
        margin = 30
        gap = 20  # Gap between panels

        # Calculate panel dimensions
        panel_width = (page_width - 2 * margin - gap) / 2
        panel_height = (page_height - 2 * margin - gap) / 2

        # Process panels in groups of 4
        for page_num in range(0, len(panels), panels_per_page):
            page_panels = panels[page_num:page_num + panels_per_page]
            print(f"  Adding page {page_num // panels_per_page + 1} with {len(page_panels)} panels...")

            # Position for each panel in 2x2 grid
            positions = [
                (margin, page_height - margin - panel_height),  # Top-left
                (margin + panel_width + gap, page_height - margin - panel_height),  # Top-right
                (margin, page_height - margin - 2 * panel_height - gap),  # Bottom-left
                (margin + panel_width + gap, page_height - margin - 2 * panel_height - gap)  # Bottom-right
            ]

            for i, panel in enumerate(page_panels):
                if os.path.exists(panel.image_path):
                    # Load image
                    img = Image.open(panel.image_path)
                    img_width, img_height = img.size

                    # Calculate scaling to fit panel area
                    scale = min(panel_width / img_width, panel_height / img_height)
                    new_width = img_width * scale
                    new_height = img_height * scale

                    # Get position for this panel
                    x, y = positions[i]

                    # Center image within its panel area
                    x_offset = (panel_width - new_width) / 2
                    y_offset = (panel_height - new_height) / 2

                    # Draw image
                    c.drawImage(panel.image_path, x + x_offset, y + y_offset,
                                width=new_width, height=new_height)

                    # Add panel number
                    c.setFont("Helvetica", 9)
                    # c.drawString(x + 5, y + 5, f"Panel {page_num + i + 1}")

            # Add black border to page
            c.setStrokeColorRGB(0, 0, 0)  # Black color
            c.setLineWidth(2)  # Border thickness (adjust as needed)
            c.rect(10, 10, page_width - 20, page_height - 20, fill=0)

            c.showPage()

        c.save()
        print(f"✓ Comic book created: {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"✗ PDF creation failed: {e}")
        raise HTTPException(status_code=500, detail=f"PDF creation failed: {str(e)}")

@app.post("/generate_comic_book/")
async def generate_comic_book(request: ComicBookRequest):
    """
    Main endpoint: Generate a complete comic book from a story

    Pipeline:
    1. Generate scene descriptions
    2. Generate images for each scene
    3. Detect bubble positions (if bubbles requested)
    4. Generate dialogue (if bubbles requested)
    5. Add bubbles to images (if bubbles requested)
    6. Combine all panels into PDF book
    """

    print("\n" + "=" * 60)
    print("🎨 COMIC BOOK GENERATION STARTED")
    print("=" * 60)
    print(f"Story length: {len(request.story)} characters")
    print(f"Style: {request.style}")
    print(f"Panels: {request.num_panels}")
    print(f"Bubbles per panel: {request.num_bubbles}")
    print("=" * 60)

    panels = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Step 1: Generate scenes
        scenes = await generate_scenes(request.story, request.num_panels)

        if not scenes:
            raise HTTPException(status_code=500, detail="No scenes generated")

        # Process each panel
        for i, scene in enumerate(scenes):
            print(f"\n--- Processing Panel {i + 1}/{len(scenes)} ---")

            # Step 2: Generate image
            image_filename = f"panel_{timestamp}_{i}.png"
            img_data = await generate_image(
                prompt=scene,
                style=request.style,
                output_name=image_filename,
                width=request.width,
                height=request.height
            )

            panel_data = PanelData(
                scene=scene,
                image_path=image_filename,
                image_url=img_data.get('image_url')
            )

            # Steps 3-5: Add bubbles if requested
            if request.num_bubbles > 0:
                # Step 3: Detect positions
                positions = await detect_bubble_positions(image_filename, request.num_bubbles)

                if positions:
                    # Step 4: Generate dialogue
                    dialogues = await generate_dialogue(scene, request.num_bubbles, positions)

                    if dialogues:
                        panel_data.bubbles = dialogues

                        # Step 5: Add bubbles to image
                        final_image = f"panel_{timestamp}_{i}_final.png"
                        final_path = await add_bubbles_to_image(
                            image_filename,
                            dialogues,
                            final_image
                        )
                        panel_data.image_path = final_path

            panels.append(panel_data)

        # Step 6: Create PDF book
        pdf_filename = f"comic_book_{timestamp}.pdf"
        pdf_path = create_comic_book_pdf(panels, pdf_filename)

        print("\n" + "=" * 60)
        print("✅ COMIC BOOK GENERATION COMPLETED")
        print("=" * 60)

        return {
            "status": "success",
            "message": f"Comic book generated with {len(panels)} panels",
            "pdf_file": pdf_path,
            "panels": [
                {
                    "scene": p.scene,
                    "image_url": p.image_url,
                    "has_bubbles": len(p.bubbles) > 0
                }
                for p in panels
            ],
            "download_url": f"/download/{pdf_filename}"
        }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/{filename}")
async def download_comic_book(filename: str):
    """Download generated comic book PDF"""
    file_path = f"output/{filename}"

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )


@app.get("/health")
async def health_check():
    """Check if all services are running"""
    services_status = {}

    for service_name, url in API_SERVICES.items():
        try:
            # Try to connect to each service
            response = requests.get(url.replace(url.split('/')[-1], ''), timeout=2)
            services_status[service_name] = "online" if response.status_code < 500 else "error"
        except:
            services_status[service_name] = "offline"

    all_online = all(status == "online" for status in services_status.values())

    return {
        "status": "healthy" if all_online else "degraded",
        "services": services_status,
        "message": "All systems operational" if all_online else "Some services are down"
    }


@app.get("/")
async def root():
    return {
        "message": "🎨 Comic Book Generator - Main Orchestrator",
        "version": "1.0",
        "description": "Coordinates all microservices to generate complete comic books",
        "endpoints": {
            "/generate_comic_book/": "POST - Generate complete comic book",
            "/download/{filename}": "GET - Download generated PDF",
            "/health": "GET - Check services status",
            "/docs": "API documentation"
        },
        "services": list(API_SERVICES.keys())
    }


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("  COMIC BOOK GENERATOR - MAIN ORCHESTRATOR")
    print("=" * 60)
    print("  Port: 8000")
    print("  Endpoints:")
    print("    - POST /generate_comic_book/")
    print("    - GET /download/{filename}")
    print("    - GET /health")
    print("=" * 60)
    print("\n  Required services:")
    for service, url in API_SERVICES.items():
        print(f"    - {service}: {url}")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="127.0.0.1", port=8000)