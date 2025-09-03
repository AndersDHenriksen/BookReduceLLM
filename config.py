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

# -- Summarization Parameters --
CHUNK_SIZE = 10000  # Number of characters per chunk to send to the LLM
MAX_RECAP_SIZE = 000  # Max characters for the recap before it gets condensed. Set to 0 to disable recap.

# -- System Prompt --
# This is the main instruction given to the model for each chunk.
SYSTEM_PROMPT = "You are a ruthless editor. Your sole mission is to drastically reduce a book's length to about 25% of its original size. Do not summarize. You must rewrite the story, but aggressively cut redundant language and dialogue, and non-essential subplots. Retain only the core narrative, character progression, and critical plot points. The final output must be a continuous, flowing story, not a list of events and not consisting of short sentences."

# -- Prompt Templates --
# These are the building blocks for the final prompt sent to the LLM.

# This part provides the running summary (recap) of the story. It is only used if MAX_RECAP_SIZE > 0.
RECAP_SECTION_TEMPLATE = """CONTEXT:
Below is a summary of the story so far. It is crucial that you use this context to inform your writing, ensuring the narrative flows and remains consistent.

STORY SO FAR:
```
{recap}
```
"""

# This prompt template is used for summarizing each chunk of the book.
USER_PROMPT_TEMPLATE = """
TASK:
Rewrite and shorten the following text chunk. Your rewritten version must be significantly shorter than the original. {continuation_instruction} Focus only on what is essential to move the story forward but write in full sentences.

TEXT CHUNK TO REWRITE:
```
{chunk}
```

REWRITTEN STORY (NO BULLETS, NO INTRODUCTORY PHRASES LIKE "Here is the rewritten text"):"""

# This is the instruction given to the model when the recap becomes too long.
RECAP_SYSTEM_PROMPT = "You are an expert at condensing summaries. Your task is to take a running summary and make it shorter, keeping only the most critical information needed to understand the next part of a story. The condensed summary must be at least 50% shorter than the original."

# This prompt is used to summarize the summary itself.
RECAP_SUMMARY_PROMPT = """
The following summary is becoming too long to be used as context. Please condense it significantly, retaining only the most essential plot points, characters, and setting details that are crucial for understanding what happens next in the book.

TEXT TO CONDENSE:
```
{recap}
```

CONDENSED SUMMARY:"""
