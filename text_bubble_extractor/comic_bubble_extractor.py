import re
import spacy
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class TextBubble:
    bubble_type: str  # speech, thought, shout
    text: str


class ComicBubbleExtractor:

    SPEECH_VERBS = {
        'say','said','ask','asked','reply','replied','answer','answered',
        'whisper','whispered','mutter','muttered','tell','told','speak',
        'spoke','respond','remark','stated','declared','announced','added',
        'called','continued'
    }

    THOUGHT_VERBS = {
        'think','thought','wonder','wondered','ponder','consider','realized',
        'believe','remember','recall','mused','reflect','reckon','felt','figure'
    }

    SHOUT_VERBS = {
        'shout','shouted','yell','yelled','scream','screamed','cry','cried',
        'holler','roar','exclaim','shriek'
    }

    QUOTE_REGEX = re.compile(
        r"(?:\"([^\"]+)\")|(?:'([^']+)')"   # single or double quotes
    )

    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            import subprocess
            subprocess.run(["python","-m","spacy","download","en_core_web_sm"])
            self.nlp = spacy.load("en_core_web_sm")

    def process_paragraph(self, text: str) -> List[TextBubble]:
        bubbles: List[TextBubble] = []

        # Step 1: Direct quotes
        direct_bubbles = self._extract_direct_quotes(text)
        bubbles.extend(direct_bubbles)

        # Step 2: Indirect speech/thought
        leftover_text = self._remove_direct_quotes(text)
        doc = self.nlp(leftover_text)

        for sent in doc.sents:
            converted = self._convert_indirect(sent)
            if converted:
                bubbles.append(converted)

        # Sort bubbles by original position
        bubbles = self._sort_by_position(bubbles, text)
        return bubbles


    # DIRECT QUOTES
    def _extract_direct_quotes(self, text: str) -> List[TextBubble]:
        bubbles = []

        for m in self.QUOTE_REGEX.finditer(text):
            quote = m.group(1) or m.group(2)
            if not quote.strip():
                continue

            before = text[:m.start()].lower()
            after = text[m.end():].lower()

            bubble_type = self._classify_quote(quote, before, after)
            bubbles.append(TextBubble(bubble_type, quote.strip()))

        return bubbles

    def _classify_quote(self, quote: str, before: str, after: str) -> str:
        context = before + " " + after

        # SHOUT rules
        if (
            any(v in context for v in self.SHOUT_VERBS)
            or quote.isupper()
            or quote.endswith("!")
        ):
            return "shout"

        # THOUGHT rules
        if any(v in context for v in self.THOUGHT_VERBS):
            return "thought"

        return "speech"

    # INDIRECT SPEECH / THOUGHT

    def _remove_direct_quotes(self, text: str) -> str:
        return self.QUOTE_REGEX.sub("", text)

    def _convert_indirect(self, sent) -> Optional[TextBubble]:
        verb = None
        verb_type = None

        for t in sent:
            lemma = t.lemma_.lower()

            if lemma in self.SHOUT_VERBS:
                verb, verb_type = t, "shout"; break
            if lemma in self.THOUGHT_VERBS:
                verb, verb_type = t, "thought"; break
            if lemma in self.SPEECH_VERBS:
                verb, verb_type = t, "speech"; break

        if not verb:
            return None

        content = self._extract_clause(sent, verb)
        if not content:
            return None

        direct_text = self._to_first_person(content)
        return TextBubble(verb_type, direct_text)

    def _extract_clause(self, sent, verb):
        for child in verb.children:
            if child.dep_ in ("ccomp","xcomp","advcl","acl"):
                toks = sorted(child.subtree, key=lambda x: x.i)
                text = " ".join(t.text for t in toks)
                text = re.sub(r"^(if|that|whether)\s+","",text,flags=re.I)
                return text.strip()
        return None

    # SIMPLE PRONOUN & GRAMMAR FIXES   
    def _to_first_person(self, text: str) -> str:
        doc = self.nlp(text)
        out = []

        replacements = {
            "he":"I","she":"I","him":"me","her":"me","his":"my","hers":"mine",
            "himself":"myself","herself":"myself","they":"we","them":"us",
            "their":"our","theirs":"ours","they'd":"I'd","he'd":"I'd","she'd":"I'd",
            "they're":"we're","he's":"I'm","she's":"I'm","they'll":"we'll"
        }

        for tok in doc:
            lw = tok.text.lower()

            if lw in replacements:
                out.append(replacements[lw])
                continue

            # fix e.g. "survives" → "survive"
            if tok.pos_ == "VERB" and tok.tag_ == "VBZ":
                if len(out) and out[-1].lower() in ("i","we"):
                    out.append(tok.lemma_)
                    continue

            out.append(tok.text)

        result = " ".join(out)
        if result and not result.endswith(("!","?",".")):
            result += "?"
        return result[0].upper() + result[1:]

    # -----------------------------------------------------------
    def _sort_by_position(self, bubbles, full_text):
        def pos(b):
            i = full_text.lower().find(b.text.lower())
            return i if i != -1 else 999999
        return sorted(bubbles, key=pos)

    def format_output(self, bubbles: List[TextBubble]) -> str:
        return "\n".join(f"[{b.bubble_type}] {b.text}" for b in bubbles)
