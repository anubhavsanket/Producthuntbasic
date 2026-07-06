import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from .database import Base

# Join table between products and topics
product_topics = Table(
    "product_topics",
    Base.metadata,
    Column("product_id", String, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", String, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)

# Join table between products and makers
product_makers = Table(
    "product_makers",
    Base.metadata,
    Column("product_id", String, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True),
    Column("maker_id", String, ForeignKey("makers.id", ondelete="CASCADE"), primary_key=True),
)

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    tagline = Column(String)
    description = Column(Text)
    website = Column(String)
    product_hunt_url = Column(String)
    votes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    created_at = Column(DateTime, nullable=False)
    featured_at = Column(DateTime)

    # Relationships
    topics = relationship("Topic", secondary=product_topics, back_populates="products")
    makers = relationship("Maker", secondary=product_makers, back_populates="products")
    note = relationship("Note", back_populates="product", uselist=False, cascade="all, delete-orphan")

class Maker(Base):
    __tablename__ = "makers"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    username = Column(String)
    profile_url = Column(String)

    products = relationship("Product", secondary=product_makers, back_populates="makers")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True)

    products = relationship("Product", secondary=product_topics, back_populates="topics")

class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(String, ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    text = Column(Text, default="")
    status_label = Column(String, default="none")  # 'none', 'shortlisted', 'interesting', 'follow_up'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="note")

class SyncRun(Base):
    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    sync_mode = Column(String, nullable=False)  # 'today', 'recent_7_days'
    fetched_count = Column(Integer, default=0)
    error_state = Column(Text)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=True)
