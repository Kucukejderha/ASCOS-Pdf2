from __future__ import annotations

import argparse


def escape_rtf(text: str) -> str:
    parts = []
    for char in text:
        code = ord(char)
        if char == "\\":
            parts.append("\\\\")
        elif char == "{":
            parts.append("\\{")
        elif char == "}":
            parts.append("\\}")
        elif char == "\t":
            parts.append("\\tab ")
        elif char == "\r":
            continue
        elif char == "\n":
            parts.append("\\par\n")
        elif code < 128:
            parts.append(char)
        else:
            signed = code if code <= 0x7FFF else code - 0x10000
            parts.append(f"\\u{signed}?")
    return "".join(parts)


def convert(source_path: str, target_path: str) -> None:
    with open(source_path, "r", encoding="utf-8") as handle:
        text = handle.read()
    header = (
        "{\\rtf1\\ansi\\ansicpg1254\\deff0"
        "{\\fonttbl{\\f0\\fswiss\\fprq2\\fcharset162 Tahoma;}}"
        "\\viewkind4\\uc1\\f0\\fs20\n"
    )
    with open(target_path, "w", encoding="ascii", errors="strict") as handle:
        handle.write(header + escape_rtf(text) + "}\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Metin dosyasini MSI lisans sayfasi icin RTF'e cevirir."
    )
    parser.add_argument("source", help="Kaynak metin dosyasi (UTF-8)")
    parser.add_argument("target", help="Uretilecek RTF dosyasi")
    args = parser.parse_args(argv)
    convert(args.source, args.target)
    print(f"RTF olusturuldu: {args.target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
