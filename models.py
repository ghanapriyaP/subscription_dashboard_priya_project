from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="owner", cascade="all, delete")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete")
    preferences = relationship("UserPreference", back_populates="user", cascade="all, delete")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Core fields
    tool_name = Column(String, nullable=False, index=True)
    purchase_date = Column(Date, nullable=False)
    billing_cycle = Column(String, nullable=False)       # "monthly" | "yearly"
    renewal_date = Column(Date, nullable=False, index=True)
    cost = Column(Float, nullable=False)

    # Professional fields
    category = Column(String, default="Other", nullable=False)  # DevOps | Communication | Productivity | Security | Analytics | Design | Other
    status = Column(String, default="active", nullable=False)   # active | inactive | cancelled
    description = Column(Text, nullable=True)
    currency = Column(String, default="USD", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="subscriptions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)    # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_messages")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(Text, nullable=False)

    user = relationship("User", back_populates="preferences")
