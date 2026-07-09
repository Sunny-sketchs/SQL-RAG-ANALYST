import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

import os
from pypdf import PdfReader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openai import OpenAI

from src.app.config import settings
from src.app.db.models import Document, Chunk

POLICY_DIR = "data/raw/policies"
CHUNK_SIZE = 800  # characters, simple fixed-size chunking
CHUNK_OVERLAP = 100

client = OpenAI(api_key=settings.openai_api_key)
engine = create_engine(settings.sync_database_url)
Session = sessionmaker(bind=engine)


def chunk_text(text: str) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunks.append(text[start:end])
        start = end - CHUNK_OVERLAP
    return [c.strip() for c in chunks if c.strip()]


def embed(text: str) -> list[float]:
    response = client.embeddings.create(model=settings.embedding_model, input=text)
    return response.data[0].embedding


def main():
    session = Session()

    for filename in os.listdir(POLICY_DIR):
        if not filename.endswith(".pdf"):
            continue

        path = os.path.join(POLICY_DIR, filename)
        reader = PdfReader(path)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

        doc = Document(filename=filename, content=full_text)
        session.add(doc)
        session.flush()  # get doc.id before inserting chunks

        for chunk_content in chunk_text(full_text):
            vector = embed(chunk_content)
            session.add(Chunk(document_id=doc.id, content=chunk_content, embedding=vector))

        print(f"Ingested {filename}: {len(chunk_text(full_text))} chunks.")

    session.commit()
    session.close()


if __name__ == "__main__":
    main()