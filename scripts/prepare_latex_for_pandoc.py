#!/usr/bin/env python3
"""把教材中的自定义代码环境转换为 Pandoc 可稳定识别的 lstlisting。"""

import argparse
import re
import sys
from pathlib import Path


TCOLOR_LISTING_PATTERN = re.compile(
    r"\\begin\{tcolorbox\}(?:\[([^\]]*)\])?\s*"
    r"\\begin\{lstlisting\}(?:\[([^\]]*)\])?\s*\n?"
    r"(.*?)"
    r"\\end\{lstlisting\}\s*\\end\{tcolorbox\}",
    flags=re.DOTALL,
)
PSEUDOCODE_PATTERN = re.compile(
    r"\\begin\{pseudocodebox\}\{([^}]*)\}\s*\n?"
    r"(.*?)"
    r"\\end\{pseudocodebox\}",
    flags=re.DOTALL,
)


def clean_title(title):
    """把代码框标题中的简单 LaTeX 标记转成纯文本。"""
    previous = None
    while previous != title:
        previous = title
        title = re.sub(
            r"\\(?:textbf|textit|emph|texttt|underline)\{([^{}]*)\}",
            r"\1",
            title,
        )
    title = (
        title.replace(r"\_", "_")
        .replace(r"\%", "%")
        .replace(r"\&", "&")
        .replace("~", " ")
    )
    return re.sub(r"\s+", " ", title).strip()


def option_value(options, key):
    if not options:
        return ""
    match = re.search(
        rf"(?:^|,)\s*{re.escape(key)}\s*=\s*(?:\{{([^{{}}]*)\}}|([^,]*))",
        options,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    return (match.group(1) or match.group(2) or "").strip()


def build_listing(code, language="", title=""):
    options = []
    if language:
        options.append(f"language={language}")
    if title:
        options.append(f"caption={{{clean_title(title)}}}")
    option_text = f"[{','.join(options)}]" if options else ""
    return (
        f"\\begin{{lstlisting}}{option_text}\n"
        f"{code.strip(chr(10))}\n"
        f"\\end{{lstlisting}}"
    )


def normalize_source(source):
    def tcolor_replacer(match):
        box_options, listing_options, code = match.groups()
        title = option_value(box_options, "title")
        language = option_value(listing_options, "language")
        return build_listing(code, language=language, title=title)

    source, tcolor_count = TCOLOR_LISTING_PATTERN.subn(tcolor_replacer, source)

    def pseudocode_replacer(match):
        title, code = match.groups()
        return build_listing(code, language="go", title=title)

    source, pseudocode_count = PSEUDOCODE_PATTERN.subn(
        pseudocode_replacer,
        source,
    )
    return source, tcolor_count, pseudocode_count


def main():
    parser = argparse.ArgumentParser(
        description="规范化 LaTeX 代码环境，供 Pandoc 转换使用"
    )
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = args.input.read_text(encoding="utf-8")
    normalized, tcolor_count, pseudocode_count = normalize_source(source)
    args.output.write_text(normalized, encoding="utf-8")
    print(
        f"CODE_ENV_NORMALIZED file={args.input} "
        f"tcolor={tcolor_count} pseudocode={pseudocode_count}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
