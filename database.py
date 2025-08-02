from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True, nullable=False)
    channel_name = Column(String, nullable=False)
    added_by = Column(String, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Settings
    header_enabled = Column(Boolean, default=False)
    header_text = Column(Text, default="")
    footer_enabled = Column(Boolean, default=False)
    footer_text = Column(Text, default="")
    
    posts = relationship("ScheduledPost", back_populates="channel")

class ScheduledPost(Base):
    __tablename__ = 'scheduled_posts'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, ForeignKey('channels.channel_id'), nullable=False)
    content = Column(Text, nullable=False)
    buttons = Column(Text, default="")  # JSON string
    scheduled_time = Column(DateTime, nullable=True)
    auto_delete_time = Column(DateTime, nullable=True)
    silent = Column(Boolean, default=False)
    pin_message = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent = Column(Boolean, default=False)
    message_id = Column(Integer, nullable=True)
    
    channel = relationship("Channel", back_populates="posts")

class BotSettings(Base):
    __tablename__ = 'bot_settings'
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Text, nullable=False)

# Database setup
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/telegram_bot')
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()