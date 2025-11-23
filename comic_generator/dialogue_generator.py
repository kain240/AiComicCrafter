"""
API 4: Dialogue Generation with Bubble Type Detection (spaCy-based)
Generates contextual dialogue based on scene descriptions using spaCy NLP.
Port: 8004
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import re
import spacy
from dataclasses import dataclass

app = FastAPI()

@dataclass
class TextBubble:
    """Represents an extracted text bubble."""
    bubble_type: str  # 'speech', 'thought', 'shout', or 'scene'
    text: str
    character: str = ""


class ComicBubbleExtractor:
    """
    Production-grade extractor for comic text bubbles.
    Handles direct quotes and indirect speech with proper conversion.
    """

    SPEECH_VERBS = {
        'say', 'said', 'says', 'ask', 'asked', 'asks', 'reply', 'replied',
        'replies', 'answer', 'answered', 'answers', 'whisper', 'whispered',
        'whispers', 'mutter', 'muttered', 'mutters', 'state', 'stated',
        'states', 'mention', 'mentioned', 'mentions', 'tell', 'told', 'tells',
        'speak', 'spoke', 'speaks', 'respond', 'responded', 'responds',
        'remark', 'remarked', 'remarks', 'announce', 'announced', 'announces',
        'declare', 'declared', 'declares', 'call', 'called', 'calls',
        'add', 'added', 'adds', 'continue', 'continued', 'continues'
    }

    THOUGHT_VERBS = {
        'think', 'thought', 'thinks', 'wonder', 'wondered', 'wonders',
        'ponder', 'pondered', 'ponders', 'consider', 'considered', 'considers',
        'realize', 'realized', 'realizes', 'figure', 'figured', 'figures',
        'imagine', 'imagined', 'imagines', 'believe', 'believed', 'believes',
        'feel', 'felt', 'feels', 'remember', 'remembered', 'remembers',
        'recall', 'recalled', 'recalls', 'muse', 'mused', 'muses',
        'reflect', 'reflected', 'reflects', 'reckon', 'reckoned', 'reckons'
    }

    SHOUT_VERBS = {
        'shout', 'shouted', 'shouts', 'yell', 'yelled', 'yells',
        'scream', 'screamed', 'screams', 'cry', 'cried', 'cries',
        'holler', 'hollered', 'hollers', 'bellow', 'bellowed', 'bellows',
        'roar', 'roared', 'roars', 'exclaim', 'exclaimed', 'exclaims',
        'shriek', 'shrieked', 'shrieks'
    }

    def __init__(self):
        """Initialize with spaCy model."""
        try:
            self.nlp = spacy.load('en_core_web_sm')
        except OSError:
            print("Downloading spaCy model 'en_core_web_sm'...")
            import subprocess
            subprocess.run(['python', '-m', 'spacy', 'download', 'en_core_web_sm'])
            self.nlp = spacy.load('en_core_web_sm')

    def process_paragraph(self, paragraph: str) -> List[TextBubble]:
        """
        Main processing function - extracts all bubbles from a paragraph.
        Uses a two-pass approach: first extract quotes, then process remaining text.
        """
        bubbles = []

        # First pass: Extract all quoted dialogue with their context
        quote_info = self._find_all_quotes_with_context(paragraph)

        if not quote_info:
            # No quotes found, process as pure narrative
            return self._process_pure_narrative(paragraph)

        # Process quotes and remaining text
        processed_ranges = []

        for quote_data in quote_info:
            quote_text, start, end, before_ctx, after_ctx = quote_data

            # Classify and create bubble for the quote
            bubble = self._create_quote_bubble(quote_text, before_ctx, after_ctx)
            bubbles.append(bubble)

            # Mark this range as processed
            processed_ranges.append((start, end))

        # Process non-quoted text (scene descriptions and indirect speech)
        non_quote_text = self._extract_non_quoted_text(paragraph, processed_ranges)

        for text_segment in non_quote_text:
            segment_bubbles = self._process_text_segment(text_segment)
            bubbles.extend(segment_bubbles)

        # Sort bubbles by their original position in text
        bubbles = self._sort_bubbles_by_position(bubbles, paragraph)

        return bubbles

    def _find_all_quotes_with_context(self, text: str):
        """
        Find all quotes and their surrounding context.
        Returns: List of (quote_text, start_pos, end_pos, before_context, after_context)
        """
        quotes = []

        # Match various quote styles
        patterns = [
            r'(["\u2018\u2019\u201C\u201D\'])(.+?)\1',
            r'"(.+?)"',
            r"'(.+?)'",
            r'"(.+?)"',
            r'\u2018(.+?)\u2019',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, text):
                if match.lastindex == 2:
                    quote_text = match.group(2)
                else:
                    quote_text = match.group(1)

                start = match.start()
                end = match.end()

                before_ctx = text[max(0, start-100):start]
                after_ctx = text[end:min(len(text), end+100)]

                quotes.append((quote_text, start, end, before_ctx, after_ctx))

        quotes.sort(key=lambda x: x[1])
        unique_quotes = []
        seen_positions = set()

        for quote in quotes:
            if quote[1] not in seen_positions:
                unique_quotes.append(quote)
                seen_positions.add(quote[1])

        return unique_quotes

    def _create_quote_bubble(self, quote_text: str, before: str, after: str) -> TextBubble:
        """Create a classified bubble from a quote and its context."""
        before_lower = before.lower()
        after_lower = after.lower()
        context = before_lower + " " + after_lower

        character = self._extract_character_from_text(before + " " + after)

        bubble_type = 'speech'

        if any(verb in context for verb in self.SHOUT_VERBS):
            bubble_type = 'shout'
        elif quote_text.isupper() or quote_text.count('!') >= 2:
            bubble_type = 'shout'
        elif quote_text.endswith('!') and len(quote_text.split()) <= 3:
            bubble_type = 'shout'
        elif any(verb in context for verb in self.THOUGHT_VERBS):
            bubble_type = 'thought'

        return TextBubble(bubble_type, quote_text, character)

    def _extract_non_quoted_text(self, text: str, quote_ranges: List):
        """Extract text segments that are not inside quotes."""
        if not quote_ranges:
            return [text]

        segments = []
        last_end = 0

        for start, end in sorted(quote_ranges):
            if last_end < start:
                segment = text[last_end:start].strip()
                if segment:
                    segments.append(segment)
            last_end = end

        if last_end < len(text):
            segment = text[last_end:].strip()
            if segment:
                segments.append(segment)

        return segments

    def _process_text_segment(self, text: str) -> List[TextBubble]:
        """Process a non-quoted text segment for scene descriptions and indirect speech."""
        bubbles = []
        doc = self.nlp(text)

        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:
                continue

            converted = self._convert_indirect_speech(sent)

            if converted:
                bubbles.append(converted)
            else:
                bubbles.append(TextBubble('scene', sent_text))

        return bubbles

    def _process_pure_narrative(self, text: str) -> List[TextBubble]:
        """Process text that contains no quotes."""
        bubbles = []
        doc = self.nlp(text)

        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:
                continue

            converted = self._convert_indirect_speech(sent)
            if converted:
                bubbles.append(converted)
            else:
                bubbles.append(TextBubble('scene', sent_text))

        return bubbles

    def _convert_indirect_speech(self, sent):
        """Convert indirect speech/thought to direct form."""
        main_verb = None
        verb_type = None

        for token in sent:
            lemma = token.lemma_.lower()

            if lemma in self.SHOUT_VERBS:
                main_verb = token
                verb_type = 'shout'
                break
            elif lemma in self.THOUGHT_VERBS:
                main_verb = token
                verb_type = 'thought'
                break
            elif lemma in self.SPEECH_VERBS:
                main_verb = token
                verb_type = 'speech'
                break

        if not main_verb:
            return None

        character = ""
        for token in sent:
            if token.dep_ == 'nsubj' and token.head == main_verb:
                character = token.text
                break

        content = self._extract_speech_content(sent, main_verb)

        if not content:
            return None

        converted = self._convert_to_first_person(content, character)

        return TextBubble(verb_type, converted, character)

    def _extract_speech_content(self, sent, verb_token):
        """Extract the content of what was said/thought after the verb."""
        for child in verb_token.children:
            if child.dep_ in ['ccomp', 'xcomp', 'advcl']:
                tokens = sorted(child.subtree, key=lambda t: t.i)
                content = ' '.join([t.text for t in tokens])
                content = re.sub(r'^\s*(if|that|whether|how|why|when|where)\s+',
                               '', content, flags=re.IGNORECASE)
                return content.strip()

        return None

    def _convert_to_first_person(self, text: str, character: str = "") -> str:
        """Convert third-person narrative to first-person direct speech."""
        doc = self.nlp(text)
        result = []

        i = 0
        while i < len(doc):
            token = doc[i]
            token_lower = token.text.lower()

            if character and token.text == character:
                result.append("I")
            elif token_lower in ['he', 'she']:
                result.append("I")
            elif token_lower in ['him', 'her']:
                result.append("me")
            elif token_lower == 'his':
                result.append("my")
            elif token_lower == 'hers':
                result.append("mine")
            elif token_lower in ['himself', 'herself']:
                result.append("myself")
            elif token_lower == 'they':
                result.append("we")
            elif token_lower == 'them':
                result.append("us")
            elif token_lower == 'their':
                result.append("our")
            elif token_lower == 'theirs':
                result.append("ours")
            elif token_lower in ["they'd", "he'd", "she'd"]:
                result.append("I'd")
            elif token_lower in ["they'll", "he'll", "she'll"]:
                result.append("I'll")
            elif token_lower in ["they're", "he's", "she's"]:
                result.append("I'm")
            elif (len(result) > 0 and result[-1].lower() in ['i', 'we'] and
                  token.pos_ == 'VERB' and token.tag_ == 'VBZ'):
                result.append(token.lemma_)
            else:
                result.append(token.text)

            i += 1

        output = ""
        for i, word in enumerate(result):
            if i == 0:
                output = word
            elif word in ['.', ',', '!', '?', "'", ';', ':', ')']:
                output += word
            elif i > 0 and result[i-1] in ['(', '"', "'"]:
                output += word
            else:
                output += ' ' + word

        if output:
            output = output[0].upper() + output[1:]

        if output and not output[-1] in ['.', '!', '?']:
            output += '?'

        return output

    def _extract_character_from_text(self, text: str) -> str:
        """Extract character name from text."""
        doc = self.nlp(text)

        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text

        for token in doc:
            if token.pos_ == 'PROPN':
                return token.text

        return ""

    def _sort_bubbles_by_position(self, bubbles: List[TextBubble], original_text: str) -> List[TextBubble]:
        """Sort bubbles by their position in the original text."""
        def get_position(bubble):
            pos = original_text.lower().find(bubble.text.lower())
            if pos == -1:
                if bubble.character:
                    pos = original_text.lower().find(bubble.character.lower())
                else:
                    pos = 999999
            return pos

        return sorted(bubbles, key=get_position)


# Initialize extractor globally
extractor = ComicBubbleExtractor()


class DialogueRequest(BaseModel):
    scene_description: str
    num_dialogues: int = 2
    bubble_positions: List[dict]


class DialogueResponse(BaseModel):
    text: str
    x: int
    y: int
    width: int
    bubble_type: str
    tail_direction: str
    font_size: int


def determine_tail_direction(bubble_type: str, index: int) -> str:
    """Determine tail direction based on bubble type and position."""
    if bubble_type == 'thought':
        return 'top'
    elif bubble_type == 'shout':
        return 'bottom' if index % 2 == 0 else 'bottom-right'
    else:
        directions = ['bottom', 'bottom-left', 'bottom-right', 'top']
        return directions[index % len(directions)]


def determine_font_size(bubble_type: str, text_length: int) -> int:
    """Determine font size based on bubble type and text length."""
    if bubble_type == 'shout':
        return 24
    elif text_length < 20:
        return 22
    elif text_length < 50:
        return 20
    else:
        return 18


@app.post("/generate_dialogue/")
async def generate_dialogue(req: DialogueRequest):
    """
    Generate dialogue text appropriate for the scene using spaCy-based extraction.
    """
    try:
        # Process the scene description to extract bubbles
        bubbles = extractor.process_paragraph(req.scene_description)

        # Filter out scene descriptions if we have enough dialogue
        dialogue_bubbles = [b for b in bubbles if b.bubble_type != 'scene']

        # If not enough dialogue, include scene descriptions
        if len(dialogue_bubbles) < req.num_dialogues:
            dialogue_bubbles = bubbles

        # Limit to requested number
        dialogue_bubbles = dialogue_bubbles[:req.num_dialogues]

        # Combine with bubble positions
        result = []
        for i, bubble in enumerate(dialogue_bubbles):
            if i < len(req.bubble_positions):
                pos = req.bubble_positions[i]

                result.append({
                    "text": bubble.text,
                    "x": pos.get("x", 0),
                    "y": pos.get("y", 0),
                    "width": pos.get("width", 200),
                    "bubble_type": bubble.bubble_type,
                    "tail_direction": determine_tail_direction(bubble.bubble_type, i),
                    "font_size": determine_font_size(bubble.bubble_type, len(bubble.text)),
                    "character": bubble.character
                })

        return {
            "status": "success",
            "dialogues": result,
            "scene": req.scene_description,
            "count": len(result)
        }

    except Exception as e:
        print(f"Error processing dialogue: {e}")
        return {
            "status": "error",
            "message": str(e),
            "dialogues": [],
            "scene": req.scene_description,
            "count": 0
        }


@app.post("/generate_dialogue_simple/")
async def generate_dialogue_simple(scene_description: str, num_dialogues: int = 2):
    """
    Simplified endpoint - just provide scene description.
    Returns dialogue without coordinates (for testing).
    """
    try:
        bubbles = extractor.process_paragraph(scene_description)

        dialogue_bubbles = [b for b in bubbles if b.bubble_type != 'scene']
        if len(dialogue_bubbles) < num_dialogues:
            dialogue_bubbles = bubbles

        dialogue_bubbles = dialogue_bubbles[:num_dialogues]

        result = [
            {
                "text": b.text,
                "bubble_type": b.bubble_type,
                "character": b.character,
                "tail_direction": determine_tail_direction(b.bubble_type, i),
                "font_size": determine_font_size(b.bubble_type, len(b.text))
            }
            for i, b in enumerate(dialogue_bubbles)
        ]

        return {
            "status": "success",
            "dialogues": result,
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
        "message": "Dialogue Generation API (spaCy-based)",
        "version": "2.0",
        "description": "Extracts and classifies dialogue from scene descriptions using NLP",
        "endpoints": {
            "/generate_dialogue/": "POST - Generate dialogue with coordinates",
            "/generate_dialogue_simple/": "POST - Generate dialogue without coordinates",
            "/test": "GET - Test API with sample data",
            "/docs": "API documentation"
        },
        "bubble_types": ["speech", "thought", "shout", "scene"],
        "tail_directions": ["bottom", "top", "bottom-left", "bottom-right", "top-left", "top-right"]
    }


@app.get("/test")
async def test_endpoint():
    """Test endpoint with sample data"""
    sample_request = DialogueRequest(
        scene_description=(
            "The dragon roared. The knight wondered if he would survive. "
            "'I must be brave!' he shouted. The princess thought about escaping."
        ),
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
    print("  DIALOGUE GENERATION API (spaCy-based)")
    print("=" * 60)
    print("  Port: 8004")
    print("  Endpoints:")
    print("    - POST /generate_dialogue/")
    print("    - POST /generate_dialogue_simple/")
    print("    - GET /test")
    print("    - GET /docs")
    print("=" * 60)

    uvicorn.run(app, host="127.0.0.1", port=8004)