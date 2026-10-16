from collections.abc import Iterator
from contextlib import contextmanager
import logging

import psycopg
from psycopg.rows import dict_row

from app.config import settings

logger = logging.getLogger(__name__)


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    with psycopg.connect(settings.database_url, row_factory=dict_row) as connection:
        yield connection


def initialize_database() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
          id UUID PRIMARY KEY,
          email VARCHAR(255) NOT NULL UNIQUE,
          display_name VARCHAR(255) NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          github_username VARCHAR(255),
          github_token VARCHAR(255),
          created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """,
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS github_token VARCHAR(255)",
        """
        CREATE TABLE IF NOT EXISTS repositories (
          id UUID PRIMARY KEY,
          owner_id UUID NOT NULL REFERENCES users(id),
          github_id BIGINT,
          name VARCHAR(255) NOT NULL,
          full_name VARCHAR(500) NOT NULL,
          default_branch VARCHAR(255) NOT NULL DEFAULT 'main',
          language VARCHAR(100),
          imported_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS analyses (
          id UUID PRIMARY KEY,
          repository_id UUID NOT NULL REFERENCES repositories(id),
          branch VARCHAR(255) NOT NULL,
          commit_sha VARCHAR(64),
          maintainability_score INTEGER DEFAULT 0,
          technical_debt_hours INTEGER DEFAULT 0,
          status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
          progress INTEGER DEFAULT 0,
          error_message TEXT,
          started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
          completed_at TIMESTAMP WITH TIME ZONE
        )
        """,
        "ALTER TABLE analyses ALTER COLUMN maintainability_score DROP NOT NULL",
        "ALTER TABLE analyses ALTER COLUMN technical_debt_hours DROP NOT NULL",
        "ALTER TABLE analyses ALTER COLUMN maintainability_score SET DEFAULT 0",
        "ALTER TABLE analyses ALTER COLUMN technical_debt_hours SET DEFAULT 0",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS progress INTEGER DEFAULT 0",
        "ALTER TABLE analyses ADD COLUMN IF NOT EXISTS error_message TEXT",
        """
        CREATE TABLE IF NOT EXISTS findings (
          id UUID PRIMARY KEY,
          analysis_id UUID NOT NULL REFERENCES analyses(id),
          category VARCHAR(100) NOT NULL,
          severity VARCHAR(50) NOT NULL,
          file_path TEXT NOT NULL,
          title TEXT NOT NULL,
          suggestion TEXT,
          line_number INTEGER
        )
        """,
    ]

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
            connection.commit()
    except Exception as exc:
        logger.warning("Could not initialize PostgreSQL database tables: %s", exc)
