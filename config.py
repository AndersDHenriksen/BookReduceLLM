# --- LM Studio Configuration ---
# Find the model identifier in your LM Studio's server logs or UI
# Example: "gemma-2-9b-it"
MODEL_IDENTIFIER = "qwen/qwen3-4b-2507"

# --- E-Book Paths ---
INPUT_EPUB_PATH = "book_full.epub"
OUTPUT_EPUB_PATH = "book_summary.epub"

# --- Progress Saving ---
# The file to save progress to, allowing the script to be resumed.
PROGRESS_FILE_PATH = "progress.json"

# --- Summarization Parameters ---
# The size of text chunks (in characters) sent to the LLM at once.
# Adjust based on your model's context window and your computer's memory.
CHUNK_SIZE = 6000

# The maximum size of the rolling summary (recap) before it gets summarized again.
# This prevents the context sent to the LLM from growing too large.
MAX_RECAP_SIZE = 10000

# --- LLM Prompts ---
# This is the main instruction given to the model for each chunk.
SYSTEM_PROMPT = "You are a ruthless editor. Your sole mission is to drastically reduce a book's length to about 25% of its original size. Do not summarize. You must rewrite the story, but aggressively cut redundant language and dialogue, and non-essential subplots. Retain only the core narrative, character progression, and critical plot points. The final output must be a continuous, flowing story, not a list of events and not consisting of short sentences."

# This prompt template is used for summarizing each chunk of the book.
USER_PROMPT_TEMPLATE = """
CONTEXT:
This is the story so far (condensed):
{recap}

TASK:
Aggressively rewrite and shorten the following text chunk. Your rewritten version MUST be significantly shorter than the original. {continuation_instruction} Focus only on what is essential to move the story forward but write in full sentences.

ORIGINAL CHUNK TO REWRITE:
---
{chunk}
---
"""

# This is the instruction given to the model when the recap becomes too long.
RECAP_SYSTEM_PROMPT = "You are an expert at condensing summaries. Your task is to take a running summary and make it shorter, keeping only the most critical information needed to understand the next part of a story. The condensed summary must be at least 50% shorter than the original."

# This prompt is used to summarize the summary itself.
RECAP_SUMMARY_PROMPT = """
The following summary is becoming too long to be used as context. Please condense it significantly, retaining only the most essential plot points, characters, and setting details that are crucial for understanding what happens next in the book.

Here is the summary to condense:
---
{recap}
---
"""
