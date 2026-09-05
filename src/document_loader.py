# -*- coding: utf-8 -*-

"""
统一文档加载器
"""

from pathlib import Path

from .pdf_loader import load_pdf
from .docx_loader import load_docx


def load_document(
    file_path: str,
):

    path = Path(
        file_path
    )

    suffix = path.suffix.lower()

    if suffix == ".pdf":

        return load_pdf(
            str(path)
        )

    if suffix == ".docx":

        return load_docx(
            str(path)
        )

    raise ValueError(
        f"不支持的文件类型："
        f"{suffix}"
    )