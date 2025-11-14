ПРИМЕР CACHE_MANAGER С РЭДИС(У НАС ЕГО НЕТ) ИЗ ДРУГОГО ПРОЕКТА ТАКЖЕ МЫ РАЗНЕСЛИ ЕГО НА ДИРЕКТОРИЮ ТАКЖЕ МЫ ИЗНАЧАЛЬНО SQLITE ИСПОЛЬЗУЕМ А ПОТОМ ПЕРЕХОДИМ НА POSTGRES

"""
Руководство к файлу (database/cache_manager.py)

Назначение:
- Высокоуровневый слой доступа к данным + кэш (Redis) для доменов: проекты, лайки, участники, чаты, уведомления и т.д.
- Инкапсулирует транзакционные операции и инвалидации кэшей.

Изменения в этой ревизии:
- Переход на «серию встреч без спринтов»: серия создаётся один раз при достижении полного состава команды.
- Добавлен метод schedule_meeting_series(project_id), который по slots_weekly (МСК), frequency_week и duration_weeks
  создаёт все встречи сразу в общем слое проекта (team_id=NULL), выставляет напоминания и followup‑триггеры.
- Переработан check_project_capacity(): при полном составе → статус "ready" и идемпотентное создание серии;
  при уходе участника → статус "recruiting" и возврат проекта в ленту, без перепланирования.
- Обновлён process_due_meeting_reminders(): ветка followup больше НЕ создаёт следующие встречи, а лишь публикует
  событие в Redis Stream (notif:actions) с action_key="meeting.followup" для последующей обработки воркером.
- Сохранили Redis‑first: кэшируем результаты, на промахе — обращаемся к БД и записываем в Redis с TTL.

Дополнения текущей ревизии:
- DTO summary/detail проектов дополнены полями frequency_week и slots_weekly, чтобы фронт мог читать расписание
  серии встреч из кэша без дополнительных запросов.
- Централизация триггеров готовности: check_project_capacity() вызывается при фактическом добавлении участника
  в assign_participant_role (в момент авто‑создания ProjectParticipant) и после approve_like(add_to_team=True).
- notify_project_full и schedule_meeting_series запускаются из check_project_capacity при первом переходе в ready (идемпотентно).
 - После создания серии встреч публикуется одно HTML‑сообщение в общий чат проекта с брифом первого звонка,
   ссылкой на комнату Jitsi и кратким расписанием; дедупликация через Redis SETNX project:{id}:chat:schedule_posted.
 - Исправление идемпотентности schedule_meeting_series: SETNX project:{id}:series:created теперь выполняется
   ПОСЛЕ валидации параметров и построения непустого списка встреч; если создать нечего, ключ не ставится. При
   гонке, когда после SETNX встречи не создались (created=0), ключ удаляется, чтобы не «заморозить» проект.
 - Расширена notify_project_full: кроме in‑app уведомления теперь публикуется событие для TG-бота через
  _enqueue_tg_out(template_key="project.full") с WebApp-кнопкой на маршрут проекта; включена дедупликация
  по ключу вида project.full#{project_id}#{user_tg_id} и уважение фича‑флага ENABLE_TG_NOTIFICATIONS.
 - Расширено логирование (INFO/DEBUG/WARN) в ключевых методах: ensure_user_in_project, check_project_capacity,
   schedule_meeting_series, notify_project_full, like_project, approve_like — для полной трассировки потока
   «пользователь вошёл → проект готов → уведомления и серия встреч».

Правила разработки:
- Все методы записи обязаны корректно инвалидировать связанные ключи кэша.
- Методы, возвращающие DTO, по возможности кэшируются декоратором cache_result.
"""

from __future__ import annotations
import logging
import datetime
import os
from zoneinfo import ZoneInfo
import functools
import inspect
import asyncio
import json
import sys
import uuid
import random
from typing import Dict, Any, Optional, List, Type, Union, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, RelationshipProperty
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.engine import Row
from sqlalchemy import Column, inspect as sa_inspect, select, func
from zoneinfo import ZoneInfo

from .redis_client import RedisClient
from .crud_new import GenericCrudService, Base, CrudError
from .session import async_session_factory
from .models import (
    User,
    Profession,
    Course,
    Task,
    UserTaskProgress,
    ChatHistory,
    Project,
    ProjectLike,
    Notification,
    ProjectParticipant,
    ProjectMeeting,
    ProjectChat,
    ProjectTask,
    ProjectTeam,
)
from ..config import settings
from ..fast_api.config import settings as api_settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
#   Global TTL presets (пока используем только LONG)
# ------------------------------------------------------------------
TTL_LONG = 3600  # 1 час, единый TTL для всех @cache_result в текущем патче

def cache_result(key_format: str):
    """Декоратор для кэширования результатов функций чтения"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Получаем сигнатуру функции для правильного маппинга аргументов
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            
            # Форматируем ключ с аргументами
            try:
                dynamic_key = key_format.format(**bound_args.arguments)
            except KeyError as e:
                logger.error(f"Ошибка форматирования ключа кэша '{key_format}': {e}")
                raise ValueError(f"Неверный формат ключа кэша: {key_format}")

            # Пробуем получить из кэша
            cached_data = await self.redis.get_cache(dynamic_key)
            if cached_data:
                logger.debug(f"[CacheManager] Cache HIT for key: {dynamic_key}")
                logger.info(f"Получены данные из кэша для ключа {dynamic_key}")
                return cached_data

            # Если нет в кэше, выполняем функцию
            logger.debug(f"[CacheManager] Cache MISS for key: {dynamic_key}. Executing function...")
            result = await func(self, *args, **kwargs)
            
            # Если получили результат, сохраняем в кэш
            if result is not None:
                logger.debug(f"[CacheManager] Setting cache for key: {dynamic_key} with TTL: {TTL_LONG}")
                await self.redis.set_cache(dynamic_key, result, ttl=TTL_LONG)
                logger.info(f"Данные сохранены в кэш для ключа {dynamic_key}")
            else:
                logger.debug(f"[CacheManager] Function returned None for key: {dynamic_key}. Not caching.")
            
            return result
        return wrapper
    return decorator

def invalidate_cache(*key_formats: str):
    """Декоратор для инвалидации кэша после операций записи"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Получаем сигнатуру функции для правильного маппинга аргументов
            sig = inspect.signature(func)
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            
            # Выполняем основную функцию
            result = await func(self, *args, **kwargs)
            
            # Если операция успешна, инвалидируем кэш
            if result:
                for key_format in key_formats:
                    try:
                        dynamic_key = key_format.format(**bound_args.arguments)
                        await self.redis.delete_cache(dynamic_key)
                        logger.info(f"Инвалидирован кэш для ключа {dynamic_key}")
                    except KeyError as e:
                        logger.error(f"Ошибка форматирования ключа кэша '{key_format}': {e}")
            
            return result
        return wrapper
    return decorator

class CacheManager:
    def __init__(self, db: AsyncSession, redis_client: RedisClient):
        self.crud = GenericCrudService(db)
        self.redis = redis_client

    # ------------------- Projects: roles/DTO helpers -------------------
    @staticmethod
    def _extract_roles(team: Any) -> list[dict]:
        roles: list[dict] = []
        try:
            if isinstance(team, dict):
                if isinstance(team.get("roles"), list):
                    for r in team.get("roles"):
                        name = (r or {}).get("name")
                        occupied = bool((r or {}).get("occupied", False))
                        if isinstance(name, str) and name:
                            roles.append({"name": name, "occupied": occupied})
                elif isinstance(team.get("teams"), list):
                    # Агрегируем роли из всех команд (уникальные по имени, occupied=true если занята в любой команде)
                    agg_occ: dict[str, bool] = {}
                    agg_name: dict[str, str] = {}
                    for t in (team.get("teams") or []):
                        for r in (t or {}).get("roles", []) or []:
                            name = (r or {}).get("name")
                            occupied = bool((r or {}).get("occupied", False))
                            if isinstance(name, str) and name:
                                key = " ".join(name.lower().split())
                                prev = agg_occ.get(key, False)
                                agg_occ[key] = prev or occupied
                                # Сохраняем первый встретившийся оригинальный регистр имени
                                if key not in agg_name:
                                    agg_name[key] = name
                    for key, occ in agg_occ.items():
                        roles.append({"name": agg_name.get(key, key), "occupied": occ})
        except Exception:
            pass
        return roles

    def _project_to_summary(self, p: Project) -> Dict[str, Any]:  # type: ignore[name-defined]
        return {
            "id": getattr(p, "id"),
            "title": getattr(p, "title"),
            "description": getattr(p, "description", None),
            "duration_weeks": getattr(p, "duration_weeks", None),
            "participants": getattr(p, "participants", 0),
            "max_participants": getattr(p, "max_participants", 0),
            "company_name": getattr(p, "company_name", None),
            "hypothesis": getattr(p, "hypothesis", None),
            # расписание встреч (для быстрого доступа при необходимости)
            "frequency_week": getattr(p, "frequency_week", None),
            "slots_weekly": getattr(p, "slots_weekly", None),
            "roles": self._extract_roles(getattr(p, "team", None)),
            "updated_at": int((getattr(p, "updated_at", None) or datetime.datetime.utcnow()).timestamp()),
        }

        base = self._project_to_summary(p)
        base["company_description"] = getattr(p, "company_description", None)
        return base

    def _project_to_detail(self, p: Project) -> Dict[str, Any]:  # type: ignore[name-defined]
        """Builds a richer project DTO for detail cache.

        Minimal fields to satisfy refresh_project_cache() usage in tests.
        """
        base = self._project_to_summary(p)
        # Enrich with additional fields commonly used by detail endpoints/UI
        base.update({
            "company_description": getattr(p, "company_description", None),
            "start_date": (
                str(getattr(p, "start_date")) if getattr(p, "start_date", None) else None
            ),
            "status": getattr(p, "status", None),
            "mentor_id": getattr(p, "mentor_id", None),
            # дублируем расписание встреч для деталей
            "frequency_week": getattr(p, "frequency_week", None),
            "slots_weekly": getattr(p, "slots_weekly", None),
        })
        # Mentor lightweight info if relation is present
        try:
            mentor = getattr(p, "mentor", None)
            if mentor is not None:
                base.update({
                    "mentor_name": getattr(mentor, "name", None),
                    "mentor_avatar": getattr(mentor, "avatar", None),
                })
        except Exception:
            pass
        return base

    async def refresh_project_cache(self, project_id: int) -> None:
        """Rebuild and cache summary/detail and update order ZSET."""
        proj = await self.get_one_or_none(
            model=Project,
            where_conditions=[Project.id == project_id],
        )
        if not proj:
            return
        summary = self._project_to_summary(proj)  # type: ignore[arg-type]
        detail = self._project_to_detail(proj)    # type: ignore[arg-type]
        await self.redis.set_project_summary(project_id, summary)
        await self.redis.set_project_detail(project_id, detail)
        # Maintain order only for recruitable projects
        try:
            status = getattr(proj, "status", None)
            score = float(summary.get("updated_at", 0))
            if status == "recruiting":
                await self.redis.zadd_projects_order("projects:order:active", project_id, score)
            else:
                await self.redis.zrem_projects_order("projects:order:active", project_id)
        except Exception:
            # Never fail caller because of ordering cache
            pass


ПРИМЕР MODELS ИЗ ДРУГОГО ПРОЕКТА

# Руководство к файлу: database/models.py
# Назначение:
# - SQLAlchemy-модели и схема БД (schema=settings.schema_name) для доменов: пользователи, проекты, встречи, чаты и т.д.
# Изменения в этой ревизии:
# - Добавлена таблица project_teams (модель ProjectTeam) — слой команд в рамках проекта.
#   Поля: id, project_id(FK), name, description, color, emoji, created_at, updated_at.
#   Ограничения: Unique(project_id, name), Unique(id, project_id) для составных FK.
# - Добавлены поля team_id (NULLABLE) в таблицы: project_chat, project_participants, projects_tasks, project_meetings.
#   Смысл: team_id IS NULL — «общая» сущность для всего проекта; NOT NULL — конкретная команда.
# - Для всех указанных таблиц добавлены составные внешние ключи (team_id, project_id)
#   → (project_teams.id, project_teams.project_id), чтобы гарантировать принадлежность команды тому же проекту.
# - Добавлены индексы по (project_id, team_id) и служебные индексы для сортировок (created_at/meeting_datetime).
# - Добавлен столбец projects.context_feed (JSON) для аккумулирования контекстных записей (например, саммари встреч).
# - Добавлен столбец project_meetings.processed_at (TIMESTAMPTZ NULL) — маркер того, что встреча была полностью
#   обработана (сгенерированы задачи, опубликована сводка в чат и разосланы уведомления). Используется вместо
#   Redis SETNX-дедупликации. Рекомендуется выставлять после успешного завершения обработки.
# - Добавлен столбец project_meetings.sprint_number (INT NULL) — номер спринта для встречи: первая встреча → 1,
#   вторая → 2 и т.д. Используется для привязки генерации чеклистов/канбан-задач к номеру спринта.
# - Добавлен столбец projects.frequency_week (INT NULL) — количество встреч в неделю, задаётся ментором при создании
#   проекта. Используется для планирования серии встреч. Таймзона фиксирована (Москва), отдельного поля не требуется.
# - Новое: добавлен столбец projects.slots_weekly (JSON) — список слотов недели в МСК для планирования серии, формат
#   элементов: {"weekday": 0..6, "time": "HH:MM"}. Используется сервисом CacheManager.schedule_meeting_series.
# - Новое: добавлен уникальный индекс на project_meetings по (project_id, meeting_datetime) — защита от дублей.
# - Добавлен столбец users.social_links (JSON) для хранения ссылок на соцсети (telegram, vk, linkedin и др.).
#   Рекомендуемый формат: {"telegram": "https://t.me/username", "vk": "https://vk.com/id...", "linkedin": "https://..."}.
# - Добавлен столбец users.career_path (JSON) для хранения карьерного пути (учеба/работа/скиллы).
#   Рекомендуемый формат:
#   {
#     "university": {"id 1": {"name": "...", "program": "...", "years": "..."}, "id 2": {...}},
#     "work": {"id 1": {"company": "...", "position": "...", "years": "..."}, ...},
#     "skills": ["..."]
#   }
# - Добавлен столбец users.about_me (VARCHAR) для краткого блока "О себе" на странице профиля.
# Правила:
# - Любые новые поля описываем в комментариях класса и README миграций.
# - Новая таблица `projects_tasks` (модель `ProjectTask`) хранит Kanban‑задачи спринтов по проектам.
#   Поля: project_id, user_id (ответственный), sprint_number, title, description, status, start_date, end_date,
#   created_at, updated_at. Индексы по project_id, user_id, sprint_number. Статус: backlog|in_progress|done.

# Database models (SQLAlchemy) 
import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean, LargeBinary, Table, MetaData, JSON, Date, Index, UniqueConstraint, CheckConstraint, Float, BigInteger, Enum, ForeignKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.sql import func # Для server_default=func.now()
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import literal, func

from ..config import settings # Импортируем настройки для URL базы данных

# Создаем асинхронный движок
# DATABASE_URL = settings.database_url # Получаем из настроек
# engine = create_async_engine(DATABASE_URL, echo=True) # echo=True для логгирования SQL запросов

# Определяем метаданные с указанием схемы
SCHEMA_NAME = settings.schema_name
metadata_obj = MetaData(schema=SCHEMA_NAME)

# Создаем базовый класс для декларативных моделей, используя наши метаданные
Base = declarative_base(metadata=metadata_obj)

# Таблица связи Пользователь-Профессия (многие ко многим)
# Явно указываем схему для внешних ключей
user_profession_association = Table(
    'user_profession', Base.metadata, # Используем metadata от Base
    Column('user_id', Integer, ForeignKey(f'{SCHEMA_NAME}.users.id'), primary_key=True),
    Column('profession_id', Integer, ForeignKey(f'{SCHEMA_NAME}.professions.id'), primary_key=True),
    Column('active', Boolean, default=True, nullable=False),
    Column('similarity_percentage', Integer, nullable=True),
    schema=SCHEMA_NAME
)

# --- NEW association Users ↔ Tags (M2M) ---
user_tag_association = Table(
    'user_tags', Base.metadata,
    Column('user_id', Integer, ForeignKey(f'{SCHEMA_NAME}.users.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey(f'{SCHEMA_NAME}.tags.id'), primary_key=True),
    schema=SCHEMA_NAME
)

class User(Base):
    # Имя таблицы не включает схему, т.к. она в metadata
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=True)
    # Веб-аутентификация
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)
    # --- new fields for mobile_app ---
    username = Column(String(150), unique=True, nullable=True)
    name = Column(String(255), nullable=True)
    avatar = Column(Text, nullable=True)
    role = Column(String(10), nullable=False, default='mentee', server_default='mentee')  # 'mentor' or 'mentee'
    skills = Column(JSON, nullable=True)
    cv = Column(Text, nullable=True)
    # Mentor onboarding linkage (Variant A)
    mentor_token_id = Column(Integer, ForeignKey(f'{SCHEMA_NAME}.mentor_tokens.id'), nullable=True)
    mentor_since = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    # Новые связи для проектов/лайков/уведомлений
    mentor_projects = relationship("Project", back_populates="mentor")
    project_likes = relationship("ProjectLike", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    project_participations = relationship("ProjectParticipant", back_populates="user")
    has_description = Column(Boolean, default=False, nullable=False) # 0 -> False, 1 -> True
    description_text = Column(Text, nullable=True)
    # Для эмбеддингов можно использовать LargeBinary или специальный тип VECTOR из pgvector
    description_embedding = Column(LargeBinary, nullable=True)
    # Новое JSONB-поле для хранения структурированного профиля (пол, образование, опыт и т.д.)
    profile_data = Column(JSONB, nullable=True)
    skill_vector = Column(JSON, nullable=True)
    # Соцсети пользователя (telegram, vk, linkedin и т.д.) в JSON-формате
    social_links = Column(JSON, nullable=True)
    # Карьерный путь (учеба/работа/скиллы) в JSON-формате
    career_path = Column(JSON, nullable=True)
    # Короткий блок "О себе" для профиля
    about_me = Column(String(1024), nullable=True)
    # Онбординг: анкетные данные
    university_name = Column(String(255), nullable=True)
    graduation_year = Column(Integer, nullable=True)
    experience_years = Column(Integer, nullable=True)
    # Мультивыбор целевых ролей (коды), храним как JSON-массив строк
    desired_roles = Column(JSON, nullable=False, server_default='[]')
    # Проходил ли форму Яндекс
    yandex_form_completed = Column(Boolean, nullable=False, default=False, server_default='false')
    # Минимальный график доступности пользователя (JSON)
    # Формат: {"Monday": [{"from": "HH:MM", "to": "HH:MM"}], "Wednesday": [...], "Saturday": [...]}
    available_schedule = Column(JSON, nullable=True)
    total_tokens_used = Column(Integer, nullable=False, default=0, server_default='0')
    # Пользователь запросил подбор ментора (лист ожидания)
    waiting_for_mentor = Column(Boolean, nullable=False, default=False, server_default='false')
    # Онбординг (показывать только один раз на пользователя)
    onboarding_completed = Column(Boolean, nullable=False, default=False, server_default='false')
    # Версия токенов для stateless refresh (Web-2): при logout/rotation инкрементируем
    token_version = Column(Integer, nullable=False, default=0, server_default='0')


ПРИМЕР SESSION ИЗ ДРУГОГО ПРОЕКТА

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from ..config import settings # Импортируем настройки

# Получаем URL базы данных из настроек
DATABASE_URL = str(settings.database_url) # pydantic >= 2 возвращает объект, не строку

# Создаем асинхронный движок SQLAlchemy
# echo=True полезно для отладки, выводит SQL-запросы в лог
# echo=False для продакшена
engine = create_async_engine(DATABASE_URL, echo=False) 

# Создаем фабрику для асинхронных сессий
# expire_on_commit=False важно для асинхронных приложений, 
# чтобы объекты SQLAlchemy оставались доступными после коммита сессии.
async_session_factory = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Асинхронный генератор для получения сессии БД
# Используется как зависимость (dependency injection)
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function that yields an async session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit() # Коммитим изменения, если все прошло успешно
        except Exception: # TODO: Уточнить обработку ошибок
            await session.rollback() # Откатываем изменения в случае ошибки
            raise # Передаем исключение дальше
        finally:
            await session.close() # Закрываем сессию 


ALEMBIC ПРИДУМАЙ САМ ТАКЖЕ A