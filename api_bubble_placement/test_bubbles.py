import requests
import json

# API endpoint
url = "http://localhost:8000/add_bubbles/"

# Your image file (make sure this file exists!)
files = {"image": open("panel.png", "rb")}

# Bubble configuration
bubbles = [
    {
        "text": "This is amazing!",
        "x": 300,
        "y": 200,
        "width": 250,
        "bubble_type": "speech",
        "tail_direction": "bottom-left",
        "font_size": 24
    },
    {
        "text": "What should I do?",
        "x": 600,
        "y": 400,
        "width": 200,
        "bubble_type": "thought",
        "font_size": 20
    }
]

# Send request
data = {"bubbles": json.dumps(bubbles)}
response = requests.post(url, files=files, data=data)

# Print result
print(response.json())
print("\nImage saved as: manga_with_bubbles.png")