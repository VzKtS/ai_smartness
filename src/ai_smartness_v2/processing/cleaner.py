"""
Content Cleaner - Generic tool output cleaning.

Extracts meaningful content from any Claude Code tool output format.
No regex per tool - uses recursive JSON parsing and content detection.

This module is designed to be future-proof: if Claude Code changes
its output format, the recursive extraction will likely still work.
"""

import re
import json
import ast
from typing import Tuple, Optional, Any


# Keys that typically contain the actual content we want
CONTENT_KEYS = [
    'content', 'text', 'output', 'stdout', 'message',
    'result', 'body', 'data', 'value'
]

# Keys that contain nested structures with content
CONTAINER_KEYS = ['file', 'response', 'tool_response', 'files']

# Keys to extract as metadata (not content)
METADATA_KEYS = [
    'filePath', 'file_path', 'path', 'url', 'uri',
    'numLines', 'startLine', 'totalLines', 'lineCount',
    'type', 'status', 'exitCode', 'returncode'
]

# Maximum content length to keep (avoid huge files filling threads)
MAX_CONTENT_LENGTH = 5000


def clean_tool_output(raw: str, tool_name: str = "") -> Tuple[str, Optional[str]]:
    """
    Clean tool output and extract meaningful content.

    Args:
        raw: Raw tool output (may be JSON, Python dict repr, or plain text)
        tool_name: Optional tool name for context-aware cleaning

    Returns:
        Tuple of (cleaned_content, extracted_file_path)
    """
    if not raw or not raw.strip():
        return "", None

    # 1. Remove IDE tags first (always present in raw)
    cleaned = remove_ide_tags(raw)

    # 2. Try to parse as structured data and extract content
    content, file_path = extract_from_structured(cleaned)

    if content:
        # 3. Final cleanup
        content = final_cleanup(content)
        # 4. Truncate if too long
        content = smart_truncate(content, MAX_CONTENT_LENGTH)
        return content, file_path

    # 5. Fallback: return cleaned raw text
    cleaned = final_cleanup(cleaned)
    cleaned = smart_truncate(cleaned, MAX_CONTENT_LENGTH)
    return cleaned, None


def remove_ide_tags(text: str) -> str:
    """Remove all IDE-related tags."""
    # Remove <ide_*>...</ide_*> tags
    text = re.sub(r'<ide_[^>]*>.*?</ide_[^>]*>', '', text, flags=re.DOTALL)
    # Remove orphan <ide_*> tags
    text = re.sub(r'<ide_[^>]*>', '', text)
    # Remove <system-reminder> tags
    text = re.sub(r'<system-reminder>.*?</system-reminder>', '', text, flags=re.DOTALL)
    return text.strip()


def parse_permissive(raw: str) -> Optional[Any]:
    """
    Parse JSON or Python dict/list representation permissively.

    Handles:
    - Standard JSON
    - Python repr with single quotes
    - Python repr with True/False/None
    """
    raw = raw.strip()

    # Quick check: does it look like structured data?
    if not (raw.startswith('{') or raw.startswith('[')):
        return None

    # Try standard JSON first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try Python ast.literal_eval (handles single quotes, True/False/None)
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        pass

    # Try converting Python-style to JSON
    try:
        # Replace Python booleans/None with JSON equivalents
        converted = raw.replace("True", "true").replace("False", "false").replace("None", "null")
        # Replace single quotes with double quotes (naive but often works)
        converted = converted.replace("'", '"')
        return json.loads(converted)
    except json.JSONDecodeError:
        pass

    return None


def extract_from_structured(raw: str) -> Tuple[str, Optional[str]]:
    """
    Extract content from structured data (JSON/dict).

    Returns:
        Tuple of (content, file_path)
    """
    data = parse_permissive(raw)

    if data is None:
        return "", None

    # Extract file path if present
    file_path = find_metadata(data, ['filePath', 'file_path', 'path'])

    # Extract content recursively
    content = find_content_recursive(data)

    return content, file_path


def find_metadata(data: Any, keys: list) -> Optional[str]:
    """Find a metadata value by searching for keys."""
    if isinstance(data, dict):
        for key in keys:
            if key in data and isinstance(data[key], str):
                return data[key]
        # Search in nested dicts
        for v in data.values():
            result = find_metadata(v, keys)
            if result:
                return result
    return None


def find_content_recursive(data: Any, depth: int = 0) -> str:
    """
    Recursively find and extract content from any structure.

    The magic: this works regardless of the exact JSON structure
    because it searches for content by key names, not by position.
    """
    if depth > 10:  # Prevent infinite recursion
        return ""

    # Base case: string
    if isinstance(data, str):
        # Skip short strings that are likely metadata
        if len(data) < 20 and not any(c in data for c in '\n.?!'):
            return ""
        return data

    # Dict: search for content keys
    if isinstance(data, dict):
        # First priority: direct content keys
        for key in CONTENT_KEYS:
            if key in data:
                value = data[key]
                if isinstance(value, str) and len(value) > 20:
                    return value
                elif isinstance(value, (dict, list)):
                    result = find_content_recursive(value, depth + 1)
                    if result:
                        return result

        # Second priority: container keys (file, response, etc.)
        for key in CONTAINER_KEYS:
            if key in data:
                result = find_content_recursive(data[key], depth + 1)
                if result:
                    return result

        # Third priority: find the longest string value
        longest = ""
        for key, value in data.items():
            # Skip metadata keys
            if key in METADATA_KEYS:
                continue

            if isinstance(value, str) and len(value) > len(longest):
                longest = value
            elif isinstance(value, (dict, list)):
                result = find_content_recursive(value, depth + 1)
                if len(result) > len(longest):
                    longest = result

        return longest

    # List: concatenate or find best
    if isinstance(data, list):
        # If it's a list of strings, join them
        if all(isinstance(item, str) for item in data):
            return '\n'.join(item for item in data if len(item) > 10)

        # Otherwise, find the longest content
        longest = ""
        for item in data:
            result = find_content_recursive(item, depth + 1)
            if len(result) > len(longest):
                longest = result
        return longest

    return ""


def final_cleanup(text: str) -> str:
    """Final cleanup of extracted content."""
    if not text:
        return ""

    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    # Remove common noise patterns
    noise_patterns = [
        r'^\s*\{["\']?type["\']?\s*:\s*["\']text["\'].*?\}\s*$',  # Wrapper remnants
        r'^\s*None\s*$',
        r'^\s*null\s*$',
    ]
    for pattern in noise_patterns:
        text = re.sub(pattern, '', text, flags=re.MULTILINE | re.IGNORECASE)

    return text.strip()


def smart_truncate(text: str, max_length: int) -> str:
    """
    Truncate text smartly, preserving meaningful boundaries.

    Tries to cut at paragraph/section boundaries rather than mid-sentence.
    """
    if len(text) <= max_length:
        return text

    # Try to find a good cut point
    cut_point = max_length

    # Look for section break (## or ---)
    section_break = text.rfind('\n## ', max_length - 500, max_length)
    if section_break > max_length // 2:
        cut_point = section_break
    else:
        # Look for paragraph break
        para_break = text.rfind('\n\n', max_length - 200, max_length)
        if para_break > max_length // 2:
            cut_point = para_break
        else:
            # Look for sentence break
            sentence_break = max(
                text.rfind('. ', max_length - 100, max_length),
                text.rfind('.\n', max_length - 100, max_length)
            )
            if sentence_break > max_length // 2:
                cut_point = sentence_break + 1

    return text[:cut_point].strip() + "\n\n[... truncated ...]"


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def clean_for_extraction(content: str, tool_name: str = "") -> str:
    """
    Clean content specifically for LLM extraction.

    Returns just the cleaned content (no file_path).
    """
    cleaned, _ = clean_tool_output(content, tool_name)
    return cleaned


def clean_for_storage(content: str, tool_name: str = "") -> Tuple[str, dict]:
    """
    Clean content for thread storage.

    Returns (content, metadata_dict) where metadata includes file_path if found.
    """
    cleaned, file_path = clean_tool_output(content, tool_name)
    metadata = {}
    if file_path:
        metadata['file_path'] = file_path
    return cleaned, metadata


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    # Test with the problematic Read output
    test_input = """{'type': 'text', 'file': {'filePath': '/path/to/file.md', 'content': "# Title\\n\\nThis is the actual content we want.\\n\\nIt has multiple paragraphs.", 'numLines': 10, 'startLine': 1, 'totalLines': 10}}"""

    cleaned, file_path = clean_tool_output(test_input, "Read")
    print(f"File path: {file_path}")
    print(f"Content:\n{cleaned}")
    print(f"\nLength: {len(cleaned)} chars")
