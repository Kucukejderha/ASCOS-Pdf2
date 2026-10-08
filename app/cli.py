from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.models import ConversionOptions, ConvertMode, ExcelLayout
from app.core.pipeline import available_ocr_engines, convert
from app.core.utils import format_elapsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdf2",
        description="PDF belgelerini Word veya Excel'e dönüştürür.",
    )
    parser.add_argument("files", nargs="+", help="Dönüştürülecek PDF dosyaları")
    parser.add_argument("--to", choices=["word", "excel"], default="word", help="Hedef biçim")
    parser.add_argument("--pages", default="", help="Sayfa aralığı, ör: 1-3,5")
    parser.add_argument("--out", default="", help="Çıktı klasörü")
    parser.add_argument("--no-ocr", action="store_true", help="OCR'ı kapat")
    parser.add_argument("--force-ocr", action="store_true", help="Tüm sayfaları OCR ile aktar")
    parser.add_argument(
        "--no-layout-preserve",
        action="store_true",
        help="Taranmış belgelerde düzeni korumadan düz metin OCR uygula",
    )
    parser.add_argument("--ocr-engine", choices=["auto", "tesseract", "rapidocr"], default="auto")
    parser.add_argument("--ocr-lang", default="tur+eng", help="OCR dili, ör: tur+eng")
    parser.add_argument(
        "--layout", choices=["page_per_sheet", "all_in_one"], default="page_per_sheet"
    )
    parser.add_argument("--no-text-fallback", action="store_true", help="Tablosuz sayfada metni aktarma")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    options = ConversionOptions(
        mode=ConvertMode.WORD if args.to == "word" else ConvertMode.EXCEL,
        pages=args.pages,
        ocr=not args.no_ocr,
        ocr_lang=args.ocr_lang,
        ocr_engine=args.ocr_engine,
        force_ocr=args.force_ocr,
        layout_preserve=not args.no_layout_preserve,
        excel_layout=ExcelLayout(args.layout),
        text_fallback=not args.no_text_fallback,
    )

    output_dir = Path(args.out) if args.out else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    engines = available_ocr_engines()
    print(f"OCR motorları: {', '.join(engines) if engines else 'yok'}")

    exit_code = 0
    for raw in args.files:
        src = Path(raw)
        if not src.exists():
            print(f"[HATA] Bulunamadı: {src}")
            exit_code = 1
            continue

        def on_progress(fraction: float, message: str) -> None:
            print(f"  [{fraction * 100:5.1f}%] {message}")

        try:
            result = convert(src, options, output_dir=output_dir, progress=on_progress)
        except Exception as exc:
            print(f"[HATA] {src.name}: {exc}")
            exit_code = 1
            continue

        print(f"  -> {result.output}  ({format_elapsed(result.elapsed_s)})")
        if result.ocr_pages:
            pages = ", ".join(str(p + 1) for p in result.ocr_pages)
            print(f"  OCR uygulanan sayfalar: {pages}")
        for warning in result.warnings:
            print(f"  [UYARI] {warning}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
