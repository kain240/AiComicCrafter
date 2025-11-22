from comic_bubble_extractor import ComicBubbleExtractor

def main():
    simple_examples = [
        "John said, 'I am coming home.'",
        "'Run!' he shouted.",
        "'Be quiet,' Mary whispered.",
        "Sarah wondered if he was safe.",
        "Tom thought that they were lost.",
        "\"STOP!\" she screamed.",
        "Mike asked, 'Are we late?'"
    ]

    extractor = ComicBubbleExtractor()

    for ex in simple_examples:
        bubbles = extractor.process_paragraph(ex)
        print(f"Input: {ex}")
        print("Extracted Bubbles:")
        print(extractor.format_output(bubbles))
        print("----------------------")

   


if __name__ == "__main__":
    main()
