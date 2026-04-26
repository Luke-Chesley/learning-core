from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from langchain_core.tools import tool

_COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
_USER_AGENT = "learning-core/0.1 (lesson visual search; contact: local-dev)"
_QUERY_STOPWORDS = {
    "a",
    "an",
    "and",
    "available",
    "educational",
    "for",
    "image",
    "lesson",
    "of",
    "photo",
    "picture",
    "reference",
    "simple",
    "the",
    "to",
    "visual",
    "with",
}


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, dict):
        nested = value.get("value")
        if isinstance(nested, str):
            stripped = nested.strip()
            return stripped or None
    return None


def _clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", without_tags).strip()


def _fallback_queries(query: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    queries = [normalized]
    tokens = [
        token
        for token in re.findall(r"[a-z][a-z-]{2,}", normalized)
        if token not in _QUERY_STOPWORDS
    ]

    token_set = set(tokens)
    if "cloud" in token_set or "clouds" in token_set:
        queries.extend(["cloud types", "cumulus cloud", "cirrus cloud", "stratus cloud"])

    if len(tokens) >= 2:
        queries.append(" ".join(tokens[:3]))

    deduped: list[str] = []
    for candidate in queries:
        if candidate and candidate not in deduped:
            deduped.append(candidate)
    return deduped[:6]


def _commons_image_results(query: str, limit: int) -> list[dict[str, str]]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": "6",
        "gsrsearch": query,
        "gsrlimit": str(max(1, min(limit, 8))),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1200",
    }
    request = Request(
        f"{_COMMONS_API_URL}?{urlencode(params)}",
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        },
    )
    with urlopen(request, timeout=8.0) as response:
        payload = json.loads(response.read().decode("utf-8"))

    pages = payload.get("query", {}).get("pages", {})
    if not isinstance(pages, dict):
        return []

    results: list[dict[str, str]] = []
    for page in pages.values():
        if not isinstance(page, dict):
            continue
        image_info = page.get("imageinfo")
        if not isinstance(image_info, list) or not image_info:
            continue
        first_info = image_info[0]
        if not isinstance(first_info, dict):
            continue

        url = _string_value(first_info.get("thumburl")) or _string_value(first_info.get("url"))
        if not url:
            continue
        if ".pdf/" in url.lower() or url.lower().endswith(".pdf"):
            continue

        metadata = first_info.get("extmetadata") if isinstance(first_info.get("extmetadata"), dict) else {}
        title = _clean_text(_string_value(metadata.get("ObjectName")) or str(page.get("title", "Wikimedia Commons image")))
        description_value = _string_value(metadata.get("ImageDescription"))
        description = _clean_text(description_value) if description_value else None
        combined_text = f"{title} {description or ''}".lower()
        weather_cloud_query = any(
            term in query.lower()
            for term in ("cloud types", "cumulus", "cirrus", "stratus", "weather")
        )
        if weather_cloud_query and "computing" in combined_text:
            continue

        license_short = _string_value(metadata.get("LicenseShortName"))
        artist_value = _string_value(metadata.get("Artist"))
        artist = _clean_text(artist_value) if artist_value else None

        results.append(
            {
                "title": title.replace("File:", "").strip(),
                "url": url,
                "source_name": "Wikimedia Commons",
                "license": license_short or "Wikimedia Commons",
                "credit": artist or "Wikimedia Commons contributor",
                "description": description or title,
            }
        )

    return results


@tool
def search_lesson_images(query: str, limit: int = 4) -> str:
    """Search for real, renderable lesson visual aid image URLs.

    Use when a generated lesson would materially benefit from a photo, map,
    diagram, artwork, or other visual reference. Return values are safe
    candidates; copy a result URL exactly into visual_aids[].url only when it
    directly supports the lesson block.
    """
    normalized_query = query.strip()
    if not normalized_query:
        return json.dumps({"results": [], "error": "query is required"})

    attempts = _fallback_queries(normalized_query)
    results: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    try:
        for attempt in attempts:
            for result in _commons_image_results(attempt, limit):
                if result["url"] in seen_urls:
                    continue
                results.append(result)
                seen_urls.add(result["url"])
                if len(results) >= max(1, min(limit, 8)):
                    break
            if len(results) >= max(1, min(limit, 8)):
                break
    except Exception as error:
        return json.dumps({"results": [], "attempts": attempts, "error": str(error)})

    return json.dumps({"results": results, "attempts": attempts}, ensure_ascii=True)
