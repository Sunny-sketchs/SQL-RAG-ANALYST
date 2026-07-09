import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

from sqlalchemy import create_engine, text, inspect
from src.app.db.models import Base
from src.app.config import settings

engine = create_engine(settings.sync_database_url)

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

inspector = inspect(engine)
existing = inspector.get_table_names()

if existing:
    print(f"Tables already exist: {existing}. Skipping create_all.")
else:
    Base.metadata.create_all(bind=engine)
    print("Created tables: sales, documents, chunks.")