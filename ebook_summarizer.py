# -*- coding: utf-8 -*-

import os
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
    """Splits text into chunks of a specified size."""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


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
        condensed_recap = response[0].text
        print("--- Condensing complete. ---")
        return condensed_recap
    except Exception as e:
        print(f"\nAn error occurred while condensing the recap: {e}")
        print("--- Could not condense. Using original recap. ---")
        return recap_text


def summarize_chapter_content(item_content, llm):
    """Summarizes the text content of a single chapter."""
    original_text = get_text_from_html(item_content)
    text_chunks = chunk_text(original_text, config.CHUNK_SIZE)

    summarized_content = ""
    recap = "This is the beginning of the book."

    for chunk in text_chunks:
        try:
            full_prompt = f"{config.SYSTEM_PROMPT}\n\n{config.USER_PROMPT_TEMPLATE.format(recap=recap, chunk=chunk)}"
            response = llm.respond(full_prompt)
            chunk_summary = response[0].text
            summarized_content += chunk_summary + "\n\n"

            # Update the recap with the latest summary
            if recap == "This is the beginning of the book.":
                recap = chunk_summary
            else:
                recap += "\n\n" + chunk_summary

            # Condense the recap if it's too long
            if len(recap) > config.MAX_RECAP_SIZE:
                recap = condense_recap(recap, llm)

        except Exception as e:
            print(f"\nAn error occurred while communicating with the LLM: {e}")
            print("Skipping this chunk.")
            continue
    return summarized_content


def rebuild_book_structure(original_book, summarized_book, new_items_map):
    """Rebuilds the TOC and spine for the summarized book."""
    print("\nRebuilding e-book structure (TOC and Spine)...")
    summarized_book.toc = []
    for link in original_book.toc:
        original_item_name = ""
        if isinstance(link, tuple) and len(link) > 1 and hasattr(link[1], 'href'):
            original_item_name = os.path.basename(link[1].href.split('#')[0])
            if original_item_name in new_items_map:
                summarized_book.toc.append(
                    epub.Link(new_items_map[original_item_name].file_name, link[1].title, link[1].uid)
                )
        elif hasattr(link, 'href'):
            original_item_name = os.path.basename(link.href.split('#')[0])
            if original_item_name in new_items_map:
                summarized_book.toc.append(
                    epub.Link(new_items_map[original_item_name].file_name, link.title, link.uid)
                )

    summarized_book.spine = ['nav']
    for item_id in original_book.spine:
        original_item = original_book.get_item_with_id(item_id)
        if original_item and original_item.get_name() in new_items_map:
            summarized_book.spine.append(new_items_map[original_item.get_name()])


def summarize_ebook():
    """Main function to read, summarize, and write an EPUB file."""
    if not os.path.exists(config.INPUT_EPUB_PATH):
        print(f"Error: Input file not found at '{config.INPUT_EPUB_PATH}'")
        print("Please place your e-book in the same directory and name it 'input.epub' or update config.py.")
        return

    llm = initialize_llm()
    if not llm:
        return

    print(f"Reading e-book: '{config.INPUT_EPUB_PATH}'")
    original_book = epub.read_epub(config.INPUT_EPUB_PATH)
    summarized_book = epub.EpubBook()
    copy_metadata(original_book, summarized_book)

    new_items_map = {}
    content_items = [item for item in original_book.get_items() if item.get_type() == ebooklib.ITEM_DOCUMENT]

    print("\nStarting summarization process...")
    with tqdm(total=len(content_items), desc="Summarizing Chapters") as pbar:
        for item in original_book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                pbar.set_postfix_str(item.get_name(), refresh=True)
                summarized_text = summarize_chapter_content(item.get_content(), llm)

                new_chapter = epub.EpubHtml(
                    title=item.get_name(),
                    file_name=f"summary_{item.get_name()}",
                    lang='en'
                )
                new_chapter.content = format_summary_as_html(summarized_text)
                summarized_book.add_item(new_chapter)
                new_items_map[item.get_name()] = new_chapter
                pbar.update(1)
            else:
                summarized_book.add_item(item)
                new_items_map[item.get_name()] = item

    rebuild_book_structure(original_book, summarized_book, new_items_map)

    summarized_book.add_item(epub.EpubNcx())
    summarized_book.add_item(epub.EpubNav())

    print(f"\nWriting summarized e-book to: '{config.OUTPUT_EPUB_PATH}'")
    epub.write_epub(config.OUTPUT_EPUB_PATH, summarized_book, {})
    print("\nSummarization complete!")


if __name__ == "__main__":
    summarize_ebook()

