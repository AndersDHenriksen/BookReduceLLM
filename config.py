# --- LM Studio Configuration ---
# Find the model identifier in your LM Studio's server logs or UI
# Example: "gemma-2-9b-it"
MODEL_IDENTIFIER = "qwen/qwen3-4b-2507"

# --- E-Book Paths ---
INPUT_EPUB_PATH = "book_full.epub"
OUTPUT_EPUB_PATH = "book_summary.epub"

# --- Summarization Parameters ---
# The size of text chunks (in characters) sent to the LLM at once.
# Adjust based on your model's context window and your computer's memory.
CHUNK_SIZE = 6000

# The maximum size of the rolling summary (recap) before it gets summarized again.
# This prevents the context sent to the LLM from growing too large.
MAX_RECAP_SIZE = 10000

# --- LLM Prompts ---
# This is the main instruction given to the model for each chunk.
SYSTEM_PROMPT = "You are a skilled author's assistant. Your task is to rewrite and condense a book, reducing its length to approximately 25% of the original. This is not a summary; you must rewrite the narrative in a continuous, story-like format. Preserve the original author's tone, key characters, and essential plot points. Do not use bullet points or list formats."

# This prompt template is used for summarizing each chunk of the book.
USER_PROMPT_TEMPLATE = """
CONTEXT:
Here is the condensed version of the story so far:
{recap}

CURRENT CHUNK:
Now, please rewrite and condense the following text chunk from the book, seamlessly continuing the story. Maintain a narrative style.
---
{chunk}
---
"""

# This is the instruction given to the model when the recap becomes too long.
RECAP_SYSTEM_PROMPT = "You are an expert at condensing summaries. Your task is to take a running summary and make it shorter, keeping only the most critical information needed to understand the next part of a story."

# This prompt is used to summarize the summary itself.
RECAP_SUMMARY_PROMPT = """
The following summary is becoming too long to be used as context. Please condense it significantly, retaining only the most essential plot points, characters, and setting details that are crucial for understanding what happens next in the book.

Here is the summary to condense:
---
{recap}
---
"""
