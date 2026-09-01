from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pymysql


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    column_default: Optional[str]
    is_primary_key: bool
    is_auto_increment: bool
    comment: Optional[str]
    extra: str
    max_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None


@dataclass
class IndexInfo:
    name: str
    columns: List[str]
    is_unique: bool


@dataclass
class ForeignKeyInfo:
    name: str
    column: str
    referenced_table: str
    referenced_column: str


@dataclass
class TableInfo:
    name: str
    comment: Optional[str]
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    foreign_keys: List[ForeignKeyInfo] = field(default_factory=list)
    primary_keys: List[str] = field(default_factory=list)


class MySQLIntrospector:
    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        self.connection: Optional[pymysql.Connection] = None
        self._parse_url()

    def _parse_url(self) -> None:
        parsed = urlparse(self.db_url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 3306
        self.user = parsed.username or "root"
        self.password = parsed.password or ""
        self.database = parsed.path.lstrip("/")

    def connect(self) -> None:
        self.connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None

    def __enter__(self) -> "MySQLIntrospector":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()

    def get_tables(self, table_names: Optional[List[str]] = None) -> List[TableInfo]:
        if not self.connection:
            raise RuntimeError("Not connected to database")

        tables = []
        all_table_names = self._get_table_names()

        if table_names:
            all_table_names = [t for t in all_table_names if t in table_names]

        for table_name in all_table_names:
            table_info = self._get_table_info(table_name)
            tables.append(table_info)

        return tables

    def _get_table_names(self) -> List[str]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
                """,
                (self.database,),
            )
            return [row["TABLE_NAME"] for row in cursor.fetchall()]

    def _get_table_info(self, table_name: str) -> TableInfo:
        comment = self._get_table_comment(table_name)
        columns = self._get_columns(table_name)
        indexes = self._get_indexes(table_name)
        foreign_keys = self._get_foreign_keys(table_name)
        primary_keys = [c.name for c in columns if c.is_primary_key]

        return TableInfo(
            name=table_name,
            comment=comment,
            columns=columns,
            indexes=indexes,
            foreign_keys=foreign_keys,
            primary_keys=primary_keys,
        )

    def _get_table_comment(self, table_name: str) -> Optional[str]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT TABLE_COMMENT 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """,
                (self.database, table_name),
            )
            row = cursor.fetchone()
            comment = row["TABLE_COMMENT"] if row else None
            return comment if comment else None

    def _get_columns(self, table_name: str) -> List[ColumnInfo]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    COLUMN_KEY,
                    EXTRA,
                    COLUMN_COMMENT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
                """,
                (self.database, table_name),
            )

            columns = []
            for row in cursor.fetchall():
                columns.append(
                    ColumnInfo(
                        name=row["COLUMN_NAME"],
                        data_type=row["DATA_TYPE"],
                        is_nullable=row["IS_NULLABLE"] == "YES",
                        column_default=row["COLUMN_DEFAULT"],
                        is_primary_key=row["COLUMN_KEY"] == "PRI",
                        is_auto_increment="auto_increment" in (row["EXTRA"] or "").lower(),
                        comment=row["COLUMN_COMMENT"] or None,
                        extra=row["EXTRA"] or "",
                        max_length=row["CHARACTER_MAXIMUM_LENGTH"],
                        numeric_precision=row["NUMERIC_PRECISION"],
                        numeric_scale=row["NUMERIC_SCALE"],
                    )
                )
            return columns

    def _get_indexes(self, table_name: str) -> List[IndexInfo]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    INDEX_NAME,
                    COLUMN_NAME,
                    NON_UNIQUE
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY INDEX_NAME, SEQ_IN_INDEX
                """,
                (self.database, table_name),
            )

            index_map: Dict[str, IndexInfo] = {}
            for row in cursor.fetchall():
                index_name = row["INDEX_NAME"]
                if index_name == "PRIMARY":
                    continue

                if index_name not in index_map:
                    index_map[index_name] = IndexInfo(
                        name=index_name,
                        columns=[],
                        is_unique=row["NON_UNIQUE"] == 0,
                    )
                index_map[index_name].columns.append(row["COLUMN_NAME"])

            return list(index_map.values())

    def _get_foreign_keys(self, table_name: str) -> List[ForeignKeyInfo]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 
                    CONSTRAINT_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = %s 
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION
                """,
                (self.database, table_name),
            )

            return [
                ForeignKeyInfo(
                    name=row["CONSTRAINT_NAME"],
                    column=row["COLUMN_NAME"],
                    referenced_table=row["REFERENCED_TABLE_NAME"],
                    referenced_column=row["REFERENCED_COLUMN_NAME"],
                )
                for row in cursor.fetchall()
            ]

