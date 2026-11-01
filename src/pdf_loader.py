# -*- coding: utf-8 -*-

"""
PDF Loader
"""

from pathlib import Path
from typing import List, Dict

import pymupdf


def load_pdf(
    file_path: str,
) -> List[Dict]:

    path = Path(file_path)

    pages = []

    with pymupdf.open(path) as document:

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            text = page.get_text(
                "text"
            ).strip()

            if not text:
                continue

            pages.append(
                {
                    "page": page_number,
                    "text": text,
                }
            )

    return pages
