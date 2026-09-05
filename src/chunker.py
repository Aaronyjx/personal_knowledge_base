from pdf_loader import load_pdf


def split_text(text, chunk_size=800, chunk_overlap=100):
    """
    将文本切分成多个 Chunk。

    chunk_size:
        每个 Chunk 最大字符数

    chunk_overlap:
        相邻 Chunk 重叠字符数
    """

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - chunk_overlap

    return chunks


def build_chunks(pdf_file):

    pages = load_pdf(pdf_file)

    all_chunks = []

    chunk_id = 0

    for page in pages:

        chunks = split_text(
            page["text"],
            chunk_size=800,
            chunk_overlap=100
        )

        for chunk in chunks:

            all_chunks.append({
                "chunk_id": chunk_id,
                "page": page["page"],
                "text": chunk
            })

            chunk_id += 1

    return all_chunks


if __name__ == "__main__":

    pdf_file = "data/raw/中华人民共和国劳动法.pdf"

    chunks = build_chunks(pdf_file)

    print(f"总 Chunk 数量: {len(chunks)}")

    for chunk in chunks[:5]:

        print("\n" + "=" * 70)

        print(
            f"Chunk ID: {chunk['chunk_id']} "
            f"| Page: {chunk['page']}"
        )

        print(chunk["text"])