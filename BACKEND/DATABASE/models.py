 # Руководство к файлу (DATABASE/models.py)
 # Назначение:
 # - SQLAlchemy‑модели БД VKMax: USERS, FILES, OPERATIONS, FORMATS.
 # - Совместимы с SQLite (dev) и Postgres (prod) без изменений моделей.
 # Важно:
 # - PK: BigInteger (в SQLite тип не строгий — допустимо).
 # - Таймстемпы по умолчанию через server_default=func.now().

 from __future__ import annotations

 from sqlalchemy import (
     BigInteger,
     Boolean,
     Column,
     DateTime,
     ForeignKey,
     LargeBinary,
     String,
     Text,
     JSON,
     Index,
 )
 from sqlalchemy.orm import declarative_base, relationship
 from sqlalchemy.sql import func

 Base = declarative_base()


 class User(Base):
     __tablename__ = "users"

     id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
     max_id = Column(String(255), nullable=True, index=True)
     name = Column(String(255), nullable=True)
     metadata = Column(JSON, nullable=True)  # JSONB в Postgres
     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
     updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

     files = relationship("File", back_populates="user", cascade="all,delete-orphan")
     operations = relationship("Operation", back_populates="user")


 class Format(Base):
     __tablename__ = "formats"

     id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
     type = Column(String(50), nullable=False)  # document/graph/etc
     prompt = Column(String(1024), nullable=True)
     file_extension = Column(String(20), nullable=True)
     is_input = Column(Boolean, nullable=False, server_default="0")
     is_output = Column(Boolean, nullable=False, server_default="0")
     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

     files = relationship("File", back_populates="format")


 class File(Base):
     __tablename__ = "files"

     id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
     user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
     format_id = Column(BigInteger, ForeignKey("formats.id", ondelete="SET NULL"), nullable=True, index=True)
     content = Column(LargeBinary, nullable=True)
     path = Column(String(1024), nullable=True)
     filename = Column(String(512), nullable=True)
     file_size = Column(BigInteger, nullable=True)
     mime_type = Column(String(255), nullable=True)
     created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
     status = Column(String(50), nullable=True)

     user = relationship("User", back_populates="files")
     format = relationship("Format", back_populates="files")
     source_operations = relationship("Operation", back_populates="file", foreign_keys="Operation.file_id")
     result_operations = relationship("Operation", back_populates="result_file", foreign_keys="Operation.result_file_id")


 class Operation(Base):
     __tablename__ = "operations"

     id = Column(BigInteger, primary_key=True, autoincrement=True, index=True)
     user_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
     file_id = Column(BigInteger, ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True)
     result_file_id = Column(BigInteger, ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True)
     datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
     old_format_id = Column(BigInteger, ForeignKey("formats.id", ondelete="SET NULL"), nullable=True)
     new_format_id = Column(BigInteger, ForeignKey("formats.id", ondelete="SET NULL"), nullable=True)
     status = Column(String(50), nullable=False, server_default="queued")
     error_message = Column(Text, nullable=True)

     user = relationship("User", back_populates="operations")
     file = relationship("File", foreign_keys=[file_id], back_populates="source_operations")
     result_file = relationship("File", foreign_keys=[result_file_id], back_populates="result_operations")
     old_format = relationship("Format", foreign_keys=[old_format_id])
     new_format = relationship("Format", foreign_keys=[new_format_id])


 # Индексы для типичных фильтров
 Index("ix_files_user_created", File.user_id, File.created_at)
 Index("ix_operations_user_datetime", Operation.user_id, Operation.datetime)
 Index("ix_operations_status", Operation.status)

