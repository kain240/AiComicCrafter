import re
import spacy
from typing import List, Optional, Tuple
from dataclasses import dataclass

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
    
    def _find_all_quotes_with_context(self, text: str) -> List[Tuple[str, int, int, str, str]]:
        """
        Find all quotes and their surrounding context.
        Returns: List of (quote_text, start_pos, end_pos, before_context, after_context)
        """
        quotes = []
        
        # Match various quote styles
        patterns = [
            r'(["\u2018\u2019\u201C\u201D\'])(.+?)\1',  # Matching pairs of straight and curly quotes
            r'"(.+?)"',         # straight double quotes
            r"'(.+?)'",         # straight single quotes
            r'“(.+?)”',         # curly double quotes
            r'‘(.+?)’',         # curly single quotes
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                # Extract the actual quote content
                if match.lastindex == 2:  # Pattern with capturing group for quote type
                    quote_text = match.group(2)
                else:
                    quote_text = match.group(1)
                
                start = match.start()
                end = match.end()
                
                # Get context (up to 100 chars before and after)
                before_ctx = text[max(0, start-100):start]
                after_ctx = text[end:min(len(text), end+100)]
                
                quotes.append((quote_text, start, end, before_ctx, after_ctx))
        
        # Sort by position and remove duplicates
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
        
        # Extract character name
        character = self._extract_character_from_text(before + " " + after)
        
        # Classify the bubble type
        bubble_type = 'speech'  # default
        
        # Check for shout indicators
        if any(verb in context for verb in self.SHOUT_VERBS):
            bubble_type = 'shout'
        elif quote_text.isupper() or quote_text.count('!') >= 2:
            bubble_type = 'shout'
        elif quote_text.endswith('!') and len(quote_text.split()) <= 3:
            bubble_type = 'shout'
        # Check for thought indicators
        elif any(verb in context for verb in self.THOUGHT_VERBS):
            bubble_type = 'thought'
        
        return TextBubble(bubble_type, quote_text, character)
    
    def _extract_non_quoted_text(self, text: str, quote_ranges: List[Tuple[int, int]]) -> List[str]:
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
        
        # Add remaining text after last quote
        if last_end < len(text):
            segment = text[last_end:].strip()
            if segment:
                segments.append(segment)
        
        return segments
    
    def _process_text_segment(self, text: str) -> List[TextBubble]:
        """Process a non-quoted text segment for scene descriptions and indirect speech."""
        bubbles = []
        
        # Split into sentences
        doc = self.nlp(text)
        
        for sent in doc.sents:
            sent_text = sent.text.strip()
            if not sent_text:
                continue
            
            # Check if this is indirect speech/thought
            converted = self._convert_indirect_speech(sent)
            
            if converted:
                bubbles.append(converted)
            else:
                # It's a scene description
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
    
    def _convert_indirect_speech(self, sent) -> Optional[TextBubble]:
        """
        Convert indirect speech/thought to direct form.
        E.g., "Sarah wondered if they'd survive" -> "Will we survive?"
        """
        # Find speech/thought verbs
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
        
        # Extract character (subject)
        character = ""
        for token in sent:
            if token.dep_ == 'nsubj' and token.head == main_verb:
                character = token.text
                break
        
        # Find the content after the verb (the actual speech/thought)
        content = self._extract_speech_content(sent, main_verb)
        
        if not content:
            return None
        
        # Convert to first-person
        converted = self._convert_to_first_person(content, character)
        
        return TextBubble(verb_type, converted, character)
    
    def _extract_speech_content(self, sent, verb_token) -> Optional[str]:
        """Extract the content of what was said/thought after the verb."""
        # Look for dependent clauses
        for child in verb_token.children:
            if child.dep_ in ['ccomp', 'xcomp', 'advcl']:
                # Get all tokens in the subtree
                tokens = sorted(child.subtree, key=lambda t: t.i)
                content = ' '.join([t.text for t in tokens])
                
                # Remove leading conjunctions
                content = re.sub(r'^\s*(if|that|whether|how|why|when|where)\s+', 
                               '', content, flags=re.IGNORECASE)
                
                return content.strip()
        
        return None
    
    def _convert_to_first_person(self, text: str, character: str = "") -> str:
        """Convert third-person narrative to first-person direct speech."""
        # Parse the text
        doc = self.nlp(text)
        result = []
        
        i = 0
        while i < len(doc):
            token = doc[i]
            token_lower = token.text.lower()
            
            # Replace character name with "I"
            if character and token.text == character:
                result.append("I")
            
            # Replace pronouns
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
            
            # Handle contractions like "they'd"
            elif token_lower in ["they'd", "he'd", "she'd"]:
                result.append("I'd")
            elif token_lower in ["they'll", "he'll", "she'll"]:
                result.append("I'll")
            elif token_lower in ["they're", "he's", "she's"]:
                # Could be "is" or "has"
                result.append("I'm")
            
            # Fix verb agreement for "I"
            elif (len(result) > 0 and result[-1].lower() in ['i', 'we'] and 
                  token.pos_ == 'VERB' and token.tag_ == 'VBZ'):
                # Convert third-person singular to base form
                result.append(token.lemma_)
            
            else:
                result.append(token.text)
            
            i += 1
        
        # Reconstruct text with proper spacing
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
        
        # Capitalize first letter
        if output:
            output = output[0].upper() + output[1:]
        
        # Add punctuation if missing
        if output and not output[-1] in ['.', '!', '?']:
            output += '?'
        
        return output
    
    def _extract_character_from_text(self, text: str) -> str:
        """Extract character name from text."""
        doc = self.nlp(text)
        
        # Look for person entities
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                return ent.text
        
        # Fallback: look for proper nouns
        for token in doc:
            if token.pos_ == 'PROPN':
                return token.text
        
        return ""
    
    def _sort_bubbles_by_position(self, bubbles: List[TextBubble], original_text: str) -> List[TextBubble]:
        """Sort bubbles by their position in the original text."""
        def get_position(bubble):
            # Find position in original text
            pos = original_text.lower().find(bubble.text.lower())
            if pos == -1:
                # For converted text, try to find character name
                if bubble.character:
                    pos = original_text.lower().find(bubble.character.lower())
                else:
                    pos = 999999  # Put at end if not found
            return pos
        
        return sorted(bubbles, key=get_position)
    
    def format_output(self, bubbles: List[TextBubble]) -> str:
        """Format bubbles into readable output."""
        lines = []
        for bubble in bubbles:
            if bubble.character:
                lines.append(f"[{bubble.bubble_type}] ({bubble.character}) {bubble.text}")
            else:
                lines.append(f"[{bubble.bubble_type}] {bubble.text}")
        return '\n'.join(lines)


def main():
    """Test the extractor with comprehensive examples."""
    
    extractor = ComicBubbleExtractor()
    
    print("="*70)
    print("TEST CASE 1: Original Example")
    print("="*70)
    
    test1 = (
        "The car screeched. Sarah wondered if they'd survive the night. "
        "'Help!' she shouted. Tom thought, 'Will I make it home?' "
        "He said, 'Let's move!'"
    )
    
    print("\nInput:")
    print(test1)
    print("\nOutput:")
    bubbles = extractor.process_paragraph(test1)
    print(extractor.format_output(bubbles))
    
    print("\n" + "="*70)
    print("TEST CASE 2: Mixed Direct and Indirect")
    print("="*70)
    
    test2 = (
        "Lightning flashed. Maria wondered whether she should tell the truth. "
        "'I NEED TO KNOW!' he screamed. She thought that maybe this was her only chance."
    )
    
    print("\nInput:")
    print(test2)
    print("\nOutput:")
    bubbles = extractor.process_paragraph(test2)
    print(extractor.format_output(bubbles))
    
    print("\n" + "="*70)
    print("TEST CASE 3: Complex Narrative")
    print("="*70)
    
    test3 = (
        "The room fell silent. John realized they were running out of time. "
        "He whispered, 'Are you ready?' Sarah felt that she had no choice."
    )
    
    print("\nInput:")
    print(test3)
    print("\nOutput:")
    bubbles = extractor.process_paragraph(test3)
    print(extractor.format_output(bubbles))
    
    print("\n" + "="*70)
    print("TEST CASE 4: Pure Scene Description")
    print("="*70)
    
    test4 = (
        "The door creaked open. Shadows danced on the walls. "
        "A cold wind swept through the hallway."
    )
    
    print("\nInput:")
    print(test4)
    print("\nOutput:")
    bubbles = extractor.process_paragraph(test4)
    print(extractor.format_output(bubbles))


if __name__ == "__main__":
    main()
    main()
