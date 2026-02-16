from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import relationship
from datetime import datetime

from bot.database.db import Base

# Модель пользователя
class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    language = Column(String, nullable=True)
    ref_tag = Column(String, nullable=True)
    bot_tag = Column(String, nullable=True)  # ← ДОБАВЬ ЭТУ СТРОКУ

    def __repr__(self):
        return (
            f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username}, "
            f"ref_tag={self.ref_tag}, bot_tag={self.bot_tag})>"
        )

# Модель админа
class Admin(Base):
    __tablename__ = "admins"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)

    referrals = relationship("Referral", back_populates="admin", lazy="selectin")

    def __repr__(self):
        return f"<Admin(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"

# Модель вебмастера
class Referral(Base):
    __tablename__ = "referrals"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tag = Column(String, nullable=False)
    admin_id = Column(BigInteger, ForeignKey("admins.telegram_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    admin = relationship("Admin", back_populates="referrals")
    links = relationship("ReferralLink", back_populates="referral", cascade="all, delete-orphan", lazy="selectin")
    invites = relationship("ReferralInvite", back_populates="referral", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Referral(id={self.id}, tag={self.tag}, admin_id={self.admin_id})>"

# Модель ссылок вебмастера 
class ReferralLink(Base):
    __tablename__ = "referral_links"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    referral_id = Column(BigInteger, ForeignKey("referrals.id"), nullable=False)
    link = Column(String, nullable=False)
    source = Column(String, nullable=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_main = Column(Boolean, default=False)

    referral = relationship("Referral", back_populates="links")

    def __repr__(self):
        return f"<ReferralLink(id={self.id}, referral_id={self.referral_id}, link={self.link}, is_main={self.is_main})>"

# Модель ссылки бот + казик
class ReferralInvite(Base):
    __tablename__ = "referral_invites"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    referral_id = Column(BigInteger, ForeignKey("referrals.id"), nullable=False)
    bot_tag = Column(String, nullable=False)
    casino_link = Column(String, nullable=False)
    is_main = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    referral = relationship("Referral", back_populates="invites")

    def __repr__(self):
        return f"<ReferralInvite(id={self.id}, tag={self.bot_tag}, casino={self.casino_link})>"

class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, index=True, nullable=False)
    last_step = Column(String(50), nullable=False)
    bot_name = Column(String(50), nullable=False, default="hackbotukr")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

