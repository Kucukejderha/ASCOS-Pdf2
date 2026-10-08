from __future__ import annotations

import re
from pathlib import Path


def parse_page_range(text: str, page_count: int) -> list[int] | None:
    """'1-3,5' -> 0 tabanlı sayfa listesi. Boş metin None (tüm sayfalar)."""
    text = (text or "").strip()
    if not text:
        return None
    pages: list[int] = []
    for part in re.split(r"[,;]+", text):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                start, end = end, start
            rng = range(max(1, start), min(page_count, end) + 1)
            for n in rng:
                if n - 1 not in pages:
                    pages.append(n - 1)
            continue
        if re.fullmatch(r"\d+", part):
            n = int(part)
            if 1 <= n <= page_count and n - 1 not in pages:
                pages.append(n - 1)
            continue
        raise ValueError(f"Geçersiz sayfa aralığı: '{part}'")
    if not pages:
        raise ValueError("Sayfa aralığı boş sonuç verdi")
    return sorted(pages)


def unique_path(path: Path) -> Path:
    """Dosya varsa 'ad (2).uzanti' biçiminde benzersiz yol üretir."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 2
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def format_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} sn"
    m, s = divmod(int(seconds), 60)
    return f"{m} dk {s} sn"


def parse_number(text: str) -> int | float | str:
    """Türkçe/İngilizce sayı biçimlerini sayıya çevirir; olmazsa metni döndürür."""
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return s
    cleaned = s.replace(" ", "").replace("\u00a0", "")
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", cleaned):
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", cleaned):
        cleaned = cleaned.replace(",", "")
    elif re.fullmatch(r"-?\d+,\d+", cleaned):
        cleaned = cleaned.replace(",", ".")
    if re.fullmatch(r"-?\d+(\.\d+)?", cleaned):
        try:
            num = float(cleaned)
        except ValueError:
            return s
        return int(num) if num.is_integer() else num
    return s
