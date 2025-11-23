from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import ollama
from typing import List

app = FastAPI()

# Initialize RAG components
print("Loading embedding model... (first time takes ~1 minute)")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
print("Embedding model loaded!")

chroma_client = chromadb.Client(Settings(anonymized_telemetry=False))

collection = chroma_client.get_or_create_collection(
    name="comic_scene_examples",
    metadata={"description": "Example comic panel descriptions"}
)


class StoryRequest(BaseModel):
    story: str


class SceneGeneratorRAG:
    def __init__(self):
        self.setup_knowledge_base()

    def setup_knowledge_base(self):
        examples = [
            {
                "id": "ex1",
                "text": "Action scene: Hero leaping through air with fist extended",
                "description": "Dynamic action shot with motion lines, low angle perspective"
            },
            {
                "id": "ex2",
                "text": "Dialogue scene: Two characters facing each other in conversation",
                "description": "Medium shot, speech bubbles between characters, neutral background"
            },
            {
                "id": "ex3",
                "text": "Establishing scene: Wide view of cityscape at sunset",
                "description": "Panoramic establishing shot, detailed background, dramatic lighting"
            },
            {
                "id": "ex4",
                "text": "Emotional close-up: Character's face showing surprise",
                "description": "Tight close-up on facial features, emphasis on eyes and expression"
            },
            {
                "id": "ex5",
                "text": "Transition scene: Clock showing passage of time",
                "description": "Symbolic panel showing temporal or spatial transition"
            },
            {
                "id": "ex6",
                "text": "Climax scene: Dramatic confrontation with intense lighting",
                "description": "High contrast, dynamic composition, tension through visual elements"
            }
        ]

        try:
            existing_ids = collection.get()['ids']
            for ex in examples:
                if ex["id"] not in existing_ids:
                    collection.add(
                        ids=[ex["id"]],
                        documents=[ex["text"]],
                        metadatas=[{"description": ex["description"]}]
                    )
            print(f"Knowledge base ready with {len(examples)} examples!")
        except:
            for ex in examples:
                collection.add(
                    ids=[ex["id"]],
                    documents=[ex["text"]],
                    metadatas=[{"description": ex["description"]}]
                )
            print(f"Knowledge base created with {len(examples)} examples!")

    def retrieve_relevant_examples(self, query: str, n_results: int = 3) -> List[str]:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )

        return [
            f"{doc} - {meta['description']}"
            for doc, meta in zip(results['documents'][0], results['metadatas'][0])
        ]

    def generate_scenes_with_rag(self, story: str) -> str:
        print("Step 1: Retrieving relevant examples...")
        relevant_examples = self.retrieve_relevant_examples(story)
        print(f"Found {len(relevant_examples)} relevant examples")

        context = "\n".join([f"- {ex}" for ex in relevant_examples])

        prompt = f"""You are a comic book writer. Using the following examples of good comic panel descriptions as reference:

{context}

Now, break this story into 6 short comic panel descriptions. Each line should vividly describe one visual scene suitable for a comic artist.

Story: {story}

Output format:
1. [Scene description]
2. [Scene description]
...
6. [Scene description]

Be specific about camera angles, character positions, and visual mood."""

        print("Step 2: Generating scenes with Gemma (fast and lightweight)...")
        try:
            response = ollama.generate(
                model='gemma:2b',
                prompt=prompt
            )
            print("Scene generation complete!")
            return response['response']
        except Exception as e:
            error_msg = f"Error: {str(e)}\n\n"
            error_msg += "Make sure Gemma model is downloaded:\n"
            error_msg += 'Run: "C:\\Users\\Lenovo\\AppData\\Local\\Programs\\Ollama\\ollama.exe" pull gemma:2b\n'
            return error_msg


print("\n" + "=" * 50)
print("Initializing RAG Scene Generator with Gemma 2B")
print("=" * 50)
rag_generator = SceneGeneratorRAG()
print("=" * 50)
print("✓ System ready!")
print("=" * 50 + "\n")


@app.post("/generate_scenes/")
async def generate_scenes(req: StoryRequest):
    print(f"\n>>> Received story: {req.story[:50]}...")
    scenes = rag_generator.generate_scenes_with_rag(req.story)

    return {
        "scenes": scenes,
        "method": "RAG with Local LLM (Gemma 2B)",
        "retrieval": "Vector similarity search"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "rag_enabled": True,
        "knowledge_base_count": collection.count(),
        "llm_model": "gemma:2b (1.7GB, fast)"
    }


@app.get("/")
async def root():
    return {
        "message": "🎨 Comic Scene Generator API",
        "model": "Gemma 2B (lightweight & fast)",
        "endpoints": {
            "/generate_scenes/": "POST - Generate scenes",
            "/health": "GET - System status",
            "/docs": "GET - API docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)