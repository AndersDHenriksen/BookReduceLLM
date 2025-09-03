# -*- coding: utf-8 -*-

import os
import json
import lmstudio as lms
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from tqdm import tqdm
import config


def get_text_from_html(html_content):
    """Extracts plain text from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    return soup.get_text(separator='\n\n', strip=True)


def chunk_text(text, chunk_size):
    """
    Splits text into chunks of a specified size. If the text is larger than
    the chunk size, it tries to split at the nearest preceding double newline,
    then a single newline, to keep paragraphs/sentences intact.
    """
    chunks = []
    remaining_text = text.strip()

    while remaining_text:
        if len(remaining_text) <= chunk_size:
            chunks.append(remaining_text)
            break

        # Prioritize splitting at a double newline (paragraph break)
        split_pos = remaining_text.rfind('\n\n', 0, chunk_size)

        # If no good paragraph break is found, try a single newline (line break)
        if split_pos == -1 or split_pos < chunk_size / 2:
            single_newline_pos = remaining_text.rfind('\n', 0, chunk_size)
            if single_newline_pos != -1 and single_newline_pos >= chunk_size / 2:
                split_pos = single_newline_pos

        # If no suitable break of any kind is found, make a hard cut
        if split_pos == -1 or split_pos < chunk_size / 2:
            split_pos = chunk_size

        chunks.append(remaining_text[:split_pos])
        remaining_text = remaining_text[split_pos:].lstrip()

    return chunks


def format_summary_as_html(summary_text):
    """Converts plain text summary into a simple HTML format for the EPUB."""
    paragraphs = summary_text.strip().split('\n')
    html_content = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
    return f"<h1>Summary</h1>{html_content}"


def initialize_llm():
    """Initializes and returns the LM Studio model."""
    print(f"Loading model '{config.MODEL_IDENTIFIER}' from LM Studio...")
    try:
        return lms.llm(config.MODEL_IDENTIFIER)
    except Exception as e:
        print(f"Error connecting to LM Studio: {e}")
        print("Please ensure LM Studio is running and the model is loaded.")
        return None


def copy_metadata(original_book, summarized_book):
    """Copies metadata from the original to the new e-book."""
    if original_book.get_metadata('DC', 'identifier'):
        summarized_book.set_identifier(original_book.get_metadata('DC', 'identifier')[0][0])
    if original_book.get_metadata('DC', 'title'):
        summarized_book.set_title(f"Summary of {original_book.get_metadata('DC', 'title')[0][0]}")
    if original_book.get_metadata('DC', 'language'):
        summarized_book.set_language(original_book.get_metadata('DC', 'language')[0][0])
    if original_book.get_metadata('DC', 'creator'):
        for author in original_book.get_metadata('DC', 'creator'):
            summarized_book.add_author(author[0])


def condense_recap(recap_text, llm):
    """Condenses the recap summary when it becomes too long."""
    print("\n--- Recap has exceeded max length, condensing... ---")
    try:
        full_prompt = f"{config.RECAP_SYSTEM_PROMPT}\n\n{config.RECAP_SUMMARY_PROMPT.format(recap=recap_text)}"
        response = llm.respond(full_prompt)
        condensed_recap = response.content
        print("--- Condensing complete. ---")
        return condensed_recap
    except Exception as e:
        print(f"\nAn error occurred while condensing the recap: {e}")
        print("--- Could not condense. Using original recap. ---")
        return recap_text


def summarize_chapter_content(item_content, llm, current_recap):
    """Summarizes the text content of a single chapter."""
    original_text = get_text_from_html(item_content)
    text_chunks = chunk_text(original_text, config.CHUNK_SIZE)

    summarized_content = ""
    recap = current_recap
    recap_enabled = config.MAX_RECAP_SIZE > 0

    # Use the end of the previous chapter's summary (the recap) for the first chunk.
    last_summary_snippet = ""
    if recap != "This is the beginning of the book.":
        last_summary_snippet = recap.strip()[-150:]

    for chunk in text_chunks:
        try:
            # Build the continuation instruction if there's a snippet from the previous chunk.
            continuation_instruction = ""
            if last_summary_snippet:
                continuation_instruction = f"\nYour response should seamlessly continue the story from this ending snippet of the previous part: '...{last_summary_snippet}'\n"

            # Always start with the main task, which now includes the continuation instruction placeholder.
            prompt_body = config.TASK_SECTION_TEMPLATE.format(
                chunk=chunk,
                continuation_instruction=continuation_instruction
            )

            # If recap is enabled, prepend the context/recap section
            if recap_enabled:
                recap_section = config.RECAP_SECTION_TEMPLATE.format(recap=recap)
                prompt_body = f"{recap_section}\n\n{prompt_body}"

            # Combine system prompt with the dynamically built body
            full_prompt = f"{config.SYSTEM_PROMPT}\n\n{prompt_body}"

            response = llm.respond(full_prompt)
            chunk_summary = response.content
            summarized_content += chunk_summary + "\n\n"

            # The end of the current summary becomes the snippet for the next chunk.
            last_summary_snippet = chunk_summary.strip()[-150:]

            # Only update and manage the full recap if it's enabled
            if recap_enabled:
                if recap == "This is the beginning of the book.":
                    recap = chunk_summary
                else:
                    recap += "\n\n" + chunk_summary

                if len(recap) > config.MAX_RECAP_SIZE:
                    recap = condense_recap(recap, llm)

        except Exception as e:
            print(f"\nAn error occurred while communicating with the LLM: {e}")
            print("Skipping this chunk.")
            continue
    return summarized_content, recap


def rebuild_book_structure(summarized_book, new_items_map, content_item_names):
    """
    Builds a simple, linear TOC and spine for the summarized book.
    This is more reliable than trying to replicate the original structure.
    """
    print("\nRebuilding e-book structure (TOC and Spine)...")
    summarized_book.toc = []
    summarized_book.spine = ['nav']

    # Create a simple TOC and spine from the summarized content items in order
    for item_name in content_item_names:
        if item_name in new_items_map:
            chapter = new_items_map[item_name]
            # Ensure the item is a chapter and has an ID to prevent errors
            if isinstance(chapter, epub.EpubHtml):
                link = epub.Link(chapter.file_name, chapter.title, uid=str(chapter.id))
                summarized_book.toc.append(link)
                summarized_book.spine.append(chapter)


def load_progress(file_path):
    """Loads summarization progress from a file."""
    if os.path.exists(file_path):
        print(f"Resuming from saved progress file: '{file_path}'")
        with open(file_path, 'r', encoding='utf-8') as f:
            progress = json.load(f)
            return progress.get("recap"), progress.get("processed_chapters", {})
    return "This is the beginning of the book.", {}


def save_progress(file_path, recap, processed_chapters):
    """Saves summarization progress to a file."""
    progress = {
        "recap": recap,
        "processed_chapters": processed_chapters
    }
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=4)


def summarize_ebook():
    """Main function to read, summarize, and write an EPUB file."""
    if not os.path.exists(config.INPUT_EPUB_PATH):
        print(f"Error: Input file not found at '{config.INPUT_EPUB_PATH}'")
        return

    llm = initialize_llm()
    if not llm:
        return

    recap, processed_chapters = load_progress(config.PROGRESS_FILE_PATH)

    print(f"Reading e-book: '{config.INPUT_EPUB_PATH}'")
    original_book = epub.read_epub(config.INPUT_EPUB_PATH)
    summarized_book = epub.EpubBook()
    copy_metadata(original_book, summarized_book)

    new_items_map = {}
    content_items = [item for item in original_book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]
    content_item_names = [item.get_name() for item in content_items]

    print("\nStarting summarization process...")
    with tqdm(total=len(content_items), desc="Summarizing Chapters") as pbar:
        for item in original_book.get_items():
            item_name = item.get_name()
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                pbar.set_postfix_str(item_name, refresh=True)

                if item_name in processed_chapters:
                    print(f"\nSkipping already processed chapter: {item_name}")
                    summarized_text_html = processed_chapters[item_name]
                else:
                    summarized_text, new_recap = summarize_chapter_content(item.get_content(), llm, recap)
                    recap = new_recap
                    summarized_text_html = format_summary_as_html(summarized_text)
                    processed_chapters[item_name] = summarized_text_html
                    save_progress(config.PROGRESS_FILE_PATH, recap, processed_chapters)

                new_chapter = epub.EpubHtml(title=item.title or item_name, file_name=f"summary_{item_name}", lang='en')
                new_chapter.content = summarized_text_html
                summarized_book.add_item(new_chapter)
                new_items_map[item_name] = new_chapter
                pbar.update(1)
            else:
                # Add non-document items like images, css, etc.
                summarized_book.add_item(item)
                new_items_map[item_name] = item

    rebuild_book_structure(summarized_book, new_items_map, content_item_names)

    summarized_book.add_item(epub.EpubNcx())
    summarized_book.add_item(epub.EpubNav())

    print(f"\nWriting summarized e-book to: '{config.OUTPUT_EPUB_PATH}'")
    epub.write_epub(config.OUTPUT_EPUB_PATH, summarized_book, {})
    print("\nSummarization complete!")


if __name__ == "__main__":
    summarize_ebook()

