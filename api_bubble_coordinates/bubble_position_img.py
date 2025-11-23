from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Tuple
from PIL import Image, ImageDraw
import io
import numpy as np
import cv2
import json

app = FastAPI()


class BubblePlacement(BaseModel):
    x: int
    y: int
    width: int
    height: int
    confidence: float
    region: str


def detect_important_regions(image_array):
    """
    Detect important regions in the image using edge detection and saliency
    Returns a heatmap where high values = important areas to avoid
    """
    gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
    
    # Edge detection to find character outlines and important objects
    edges = cv2.Canny(gray, 50, 150)
    edges_dilated = cv2.dilate(edges, np.ones((15, 15), np.uint8), iterations=2)
    
    # Saliency detection (finds visually important regions)
    saliency = cv2.saliency.StaticSaliencyFineGrained_create()
    success, saliency_map = saliency.computeSaliency(image_array)
    saliency_map = (saliency_map * 255).astype(np.uint8)
    
    # Combine edge and saliency maps
    combined = cv2.addWeighted(edges_dilated, 0.5, saliency_map, 0.5, 0)
    
    # Blur to create smooth importance map
    importance_map = cv2.GaussianBlur(combined, (31, 31), 0)
    
    return importance_map


def find_empty_regions(image_array, importance_map, num_bubbles=1):
    """
    Find regions with low importance (good for bubble placement)
    Returns list of candidate positions
    """
    height, width = image_array.shape[:2]
    
    # Divide image into grid regions
    regions = {
        "top-left": (0, 0, width // 2, height // 3),
        "top-right": (width // 2, 0, width, height // 3),
        "top-center": (width // 4, 0, 3 * width // 4, height // 3),
        "middle-left": (0, height // 3, width // 3, 2 * height // 3),
        "middle-right": (2 * width // 3, height // 3, width, 2 * height // 3),
        "bottom-left": (0, 2 * height // 3, width // 2, height),
        "bottom-right": (width // 2, 2 * height // 3, width, height),
        "bottom-center": (width // 4, 2 * height // 3, 3 * width // 4, height),
    }
    
    candidates = []
    
    for region_name, (x1, y1, x2, y2) in regions.items():
        # Extract region from importance map
        region_map = importance_map[y1:y2, x1:x2]
        
        # Calculate average importance (lower is better for bubble placement)
        avg_importance = np.mean(region_map)
        
        # Calculate center of region
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2
        
        # Calculate bubble dimensions (proportional to image size)
        bubble_width = min(300, (x2 - x1) - 40)
        bubble_height = min(150, (y2 - y1) - 40)
        
        # Confidence score (inverse of importance)
        confidence = 1.0 - (avg_importance / 255.0)
        
        candidates.append({
            "x": center_x,
            "y": center_y,
            "width": bubble_width,
            "height": bubble_height,
            "confidence": round(confidence, 3),
            "region": region_name,
            "avg_importance": round(avg_importance, 2)
        })
    
    # Sort by confidence (best positions first)
    candidates.sort(key=lambda c: c["confidence"], reverse=True)
    
    return candidates[:num_bubbles]


def visualize_placements(image_array, placements, importance_map=None):
    """
    Draw the suggested bubble placements on the image for visualization
    """
    img = Image.fromarray(image_array)
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Optionally overlay importance map
    if importance_map is not None:
        heatmap = cv2.applyColorMap(importance_map, cv2.COLORMAP_JET)
        heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
        heatmap_img = Image.fromarray(heatmap)
        heatmap_img.putalpha(100)  # Semi-transparent
        img = Image.alpha_composite(img.convert('RGBA'), heatmap_img)
        draw = ImageDraw.Draw(img, 'RGBA')
    
    # Draw each placement
    for i, placement in enumerate(placements):
        x, y = placement["x"], placement["y"]
        w, h = placement["width"], placement["height"]
        
        # Draw bounding box
        bbox = [x - w//2, y - h//2, x + w//2, y + h//2]
        
        # Color based on confidence (green = good, red = bad)
        confidence = placement["confidence"]
        color = (
            int(255 * (1 - confidence)),  # R
            int(255 * confidence),        # G
            0,                             # B
            150                            # A
        )
        
        draw.rectangle(bbox, outline=color, width=3)
        
        # Draw center point
        draw.ellipse([x-5, y-5, x+5, y+5], fill=color)
        
        # Draw label
        label = f"#{i+1} ({confidence:.2f})"
        draw.text((x - w//2 + 5, y - h//2 + 5), label, fill=(255, 255, 255, 255))
    
    return img.convert('RGB')


@app.post("/detect_bubble_positions/")
async def detect_bubble_positions(
    image: UploadFile = File(...),
    num_bubbles: int = Form(default=1),
    visualize: bool = Form(default=True)
):
    """
    Analyze image and suggest optimal bubble placement coordinates
    """
    
    # Load image
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(img)
    
    # Detect important regions to avoid
    importance_map = detect_important_regions(image_array)
    
    # Find best bubble placement positions
    placements = find_empty_regions(image_array, importance_map, num_bubbles)
    
    result = {
        "status": "success",
        "image_size": {
            "width": img.width,
            "height": img.height
        },
        "placements": placements,
        "message": f"Found {len(placements)} optimal bubble position(s)"
    }
    
    # Generate visualization if requested
    if visualize:
        viz_img = visualize_placements(image_array, placements, importance_map)
        
        # Save visualization
        viz_output = "bubble_positions_visualization.png"
        viz_img.save(viz_output)
        
        result["visualization_file"] = viz_output
        result["note"] = "Green boxes = good placement, Red boxes = avoid. Heatmap shows important regions to avoid."
    
    return result


@app.post("/detect_bubble_positions_with_image/")
async def detect_bubble_positions_with_image(
    image: UploadFile = File(...),
    num_bubbles: int = Form(default=1)
):
    """
    Returns the visualization image directly (downloadable in Postman)
    """
    
    # Load image
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(img)
    
    # Detect and find positions
    importance_map = detect_important_regions(image_array)
    placements = find_empty_regions(image_array, importance_map, num_bubbles)
    
    # Generate visualization
    viz_img = visualize_placements(image_array, placements, importance_map)
    
    # Convert to bytes for response
    img_byte_arr = io.BytesIO()
    viz_img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    # Return image directly
    return StreamingResponse(
        img_byte_arr, 
        media_type="image/png",
        headers={
            "Content-Disposition": "attachment; filename=bubble_placement_result.png"
        }
    )


@app.post("/get_coordinates_only/")
async def get_coordinates_only(
    image: UploadFile = File(...),
    num_bubbles: int = Form(default=1)
):
    """
    Simplified endpoint that returns only x, y coordinates
    """
    
    # Load image
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_array = np.array(img)
    
    # Detect and find positions
    importance_map = detect_important_regions(image_array)
    placements = find_empty_regions(image_array, importance_map, num_bubbles)
    
    # Simplified output format
    coordinates = [
        {
            "x": p["x"],
            "y": p["y"],
            "bbox": [
                p["x"] - p["width"]//2,   # x1
                p["y"] - p["height"]//2,  # y1
                p["x"] + p["width"]//2,   # x2
                p["y"] + p["height"]//2   # y2
            ],
            "confidence": p["confidence"],
            "region": p["region"]
        }
        for p in placements
    ]
    
    return {
        "status": "success",
        "coordinates": coordinates
    }


@app.get("/")
async def root():
    return {
        "message": "Smart Bubble Placement API",
        "description": "Automatically detects optimal positions for dialogue bubbles in manga/comic panels",
        "endpoints": {
            "/detect_bubble_positions/": "POST - Get bubble positions with visualization (JSON + saves file)",
            "/detect_bubble_positions_with_image/": "POST - Get visualization image directly (downloadable)",
            "/get_coordinates_only/": "POST - Get just the x,y coordinates",
            "/docs": "API documentation"
        },
        "usage": "Upload an image and get suggested bubble placement coordinates that avoid characters and important objects"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)