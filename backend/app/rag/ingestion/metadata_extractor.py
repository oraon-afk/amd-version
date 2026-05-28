import re


def infer_section_title(text: str) -> str | None:
    for line in text.splitlines()[:6]:
        candidate = line.strip()
        if not candidate:
            continue
        if len(candidate) <= 120 and re.search(r"[A-Za-z]", candidate):
            return candidate.rstrip(":")
    return None


def make_citation_label(*, filename: str, page_number: int, section_title: str | None = None) -> str:
    if section_title:
        return f"{filename}, page {page_number}, {section_title}"
    return f"{filename}, page {page_number}"

