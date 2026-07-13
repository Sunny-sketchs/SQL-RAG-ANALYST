from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True)
    order_number = Column(String, index=True)
    sales_channel = Column(String, index=True)
    warehouse_code = Column(String)
    procured_date = Column(DateTime, nullable=True)
    order_date = Column(DateTime, nullable=True)
    ship_date = Column(DateTime, nullable=True)
    delivery_date = Column(DateTime, nullable=True)
    currency_code = Column(String)
    sales_team_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    store_id = Column(String, index=True)
    product_id = Column(String, index=True)
    order_quantity = Column(Integer)
    discount_applied = Column(Float)
    unit_cost = Column(Float)
    unit_price = Column(Float)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, index=True)
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    content = Column(Text)
    meta_data = Column(Text, nullable=True)
    embedding = Column(Vector(1536))
    created_at = Column(DateTime, server_default=func.now())

    document = relationship("Document", back_populates="chunks")

class UsageLog(Base):
    __tablename__ = "usage_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    node = Column(String)  # "router" | "sql" | "rag" | "synthesis"
    tokens = Column(Integer)
    created_at = Column(DateTime, server_default=func.now(), index=True)