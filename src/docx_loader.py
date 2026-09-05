# -*- coding: utf-8 -*-

"""
DOCX Loader
"""

from docx import Document


def load_docx(
    file_path: str,
):

    document = Document(
        file_path
    )

    paragraphs = []

    for paragraph in document.paragraphs:

        text = paragraph.text.strip()

        if text:

            paragraphs.append(
                text
            )

    return [
        {
            "page": "",
            "text": "\n".join(
                paragraphs
            ),
        }
    ]