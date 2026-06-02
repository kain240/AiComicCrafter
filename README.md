# AI Comic Crafter 🎨📖

Transform stories into fully illustrated comics and picture books using AI, NLP, Computer Vision, and automated comic composition.

## Overview

AI Comic Crafter is an AI-powered comic generation platform that converts textual stories into complete visual narratives. The system combines Natural Language Processing (NLP), Generative AI, Computer Vision, and Image Processing to automate every stage of comic creation—from story understanding to final comic assembly.

Given a story prompt, the platform automatically:

- Splits the story into comic scenes
- Generates dialogues for each panel
- Creates AI-generated illustrations
- Calculates optimal speech bubble positions
- Renders dialogue into speech bubbles
- Places bubbles intelligently on images
- Merges panels into a complete comic or picture book

---

## Example Generated Comic

The following comic was generated automatically from a single story prompt using the complete AI Comic Crafter pipeline.

### Story Prompt

> A young hero named Blaze discovers a mysterious power hidden within him. As a dark cosmic entity approaches Earth, Blaze must embrace his destiny and protect the city from destruction.

### Generated Workflow

Story Prompt → Story Segmentation → Dialogue Generation → AI Illustration Creation → Speech Bubble Placement → Comic Assembly → PDF Export

### Sample Output

<p align="center">
  <img src="https://github.com/user-attachments/assets/eb17cc74-06cb-4a6e-829a-4eec474510e5" width="45%" />
  <img src="https://github.com/user-attachments/assets/2bc06643-f35f-467c-a1ad-be714c145f3b" width="45%" />
</p>

This comic book was created automatically with minimal human intervention, demonstrating the platform's ability to transform natural language stories into fully illustrated comic narratives.


## Features

### 📚 Story Understanding
- Story segmentation using Google Gemini
- Automatic scene extraction
- Panel-wise narrative generation
- Structured comic storyboard creation

### 💬 Dialogue Generation
- AI-generated panel dialogues
- Context-aware conversation generation
- Character dialogue creation

### 🎨 AI Image Generation
- Scene-to-image generation
- Multiple visual style support
- AI-powered illustration creation
- High-quality comic artwork generation

### 🗨️ Speech Bubble Generation
- Automatic speech bubble creation
- Support for speech, thought, and shout bubbles
- Dynamic text wrapping
- Dialogue-aware bubble sizing

### 👁️ Computer Vision Pipeline
- Bubble coordinate calculation
- Intelligent dialogue placement
- Layout optimization
- Image composition and rendering

### 📖 Comic Assembly
- Automatic panel generation
- Comic strip creation
- Multi-panel merging
- Final picture book generation

---

## System Architecture

```text
Story Input
      │
      ▼
Story Split Service (Gemini)
      │
      ▼
Dialogue Generation
      │
      ▼
Image Generation
      │
      ▼
Bubble Coordinate Detection
      │
      ▼
Bubble Placement
      │
      ▼
Text Overlay Rendering
      │
      ▼
Comic Panel Generation
      │
      ▼
Comic Merge Service
      │
      ▼
Final Picture Book
```

---

## Project Structure

```bash
AiComicCrafter/
│
├── api_story_split/          # Story segmentation and scene generation
├── api_dialogue_gen/         # Dialogue generation pipeline
├── api_image_gen/            # AI image generation service
├── api_bubble_coordinates/   # Speech bubble coordinate calculation
├── api_bubble_placement/     # Bubble placement optimization
├── api_comic_merge/          # Comic panel merging service
├── comic_generator/          # Main orchestration pipeline
├── text_bubble_extractor/    # Dialogue extraction and processing
└── README.md
```

---

## Technologies Used

### Backend
- Python
- FastAPI

### AI & NLP
- Google Gemini 2.5 Flash
- Prompt Engineering
- Natural Language Processing (NLP)

### Image Generation
- Stable Diffusion XL
- Pollinations AI

### Computer Vision & Image Processing
- OpenCV
- Pillow (PIL)

### Validation & Configuration
- Pydantic
- Python-dotenv

---

## Workflow

### 1. Story Processing
User submits a story prompt.

### 2. Story Segmentation
Gemini converts the story into structured comic panels.

### 3. Dialogue Generation
Panel-specific dialogues are generated.

### 4. Illustration Creation
AI image models generate visuals for each scene.

### 5. Bubble Coordinate Detection
Optimal locations for dialogue bubbles are calculated.

### 6. Bubble Placement
Speech bubbles are positioned without obstructing important visual content.

### 7. Text Rendering
Dialogue is rendered using OpenCV and Pillow.

### 8. Comic Assembly
All generated panels are merged into a complete comic or picture book.

---

## Key Highlights

- End-to-end AI comic generation pipeline
- NLP-driven story understanding
- Automated dialogue generation
- AI-powered image creation
- Computer vision-based bubble placement
- Dynamic speech bubble rendering
- Modular microservice architecture
- Scalable FastAPI backend

---

## Future Enhancements

- Character consistency across panels
- Multi-page picture book generation
- PDF export support
- EPUB export support
- Voice narration
- Interactive story editing
- Custom comic styles
- Multi-language support

---

## Author

**Khushi Jain**

AI • NLP • Computer Vision • Full-Stack Development
