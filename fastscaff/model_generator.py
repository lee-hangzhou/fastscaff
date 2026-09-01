from pathlib import Path
from typing import List, Set, Tuple

from fastscaff.introspector import ColumnInfo, ForeignKeyInfo, IndexInfo, TableInfo

# MySQL type to SQLAlchemy type mapping
MYSQL_TO_SQLALCHEMY = {
    "tinyint": "Boolean",
    "smallint": "SmallInteger",
    "mediumint": "Integer",
    "int": "Integer",
    "integer": "Integer",
    "bigint": "BigInteger",
    "float": "Float",
    "double": "Float",
    "decimal": "Numeric",
    "char": "String",
    "varchar": "String",
    "tinytext": "Text",
    "text": "Text",
    "mediumtext": "Text",
    "longtext": "Text",
    "binary": "LargeBinary",
    "varbinary": "LargeBinary",
    "blob": "LargeBinary",
    "tinyblob": "LargeBinary",
    "mediumblob": "LargeBinary",
    "longblob": "LargeBinary",
    "date": "Date",
    "datetime": "DateTime",
    "timestamp": "DateTime",
    "time": "Time",
    "year": "Integer",
    "json": "JSON",
    "enum": "String",
    "set": "String",
}

# MySQL type to Tortoise type mapping
MYSQL_TO_TORTOISE = {
    "tinyint": "BooleanField",
    "smallint": "SmallIntField",
    "mediumint": "IntField",
    "int": "IntField",
    "integer": "IntField",
    "bigint": "BigIntField",
    "float": "FloatField",
    "double": "FloatField",
    "decimal": "DecimalField",
    "char": "CharField",
    "varchar": "CharField",
    "tinytext": "TextField",
    "text": "TextField",
    "mediumtext": "TextField",
    "longtext": "TextField",
    "binary": "BinaryField",
    "varbinary": "BinaryField",
    "blob": "BinaryField",
    "tinyblob": "BinaryField",
    "mediumblob": "BinaryField",
    "longblob": "BinaryField",
    "date": "DateField",
    "datetime": "DatetimeField",
    "timestamp": "DatetimeField",
    "time": "TimeField",
    "year": "IntField",
    "json": "JSONField",
    "enum": "CharField",
    "set": "CharField",
}


def snake_to_pascal(name: str) -> str:
    return "".join(word.capitalize() for word in name.split("_"))


def _single_column_uniques(indexes: List[IndexInfo]) -> Set[str]:
    return {idx.columns[0] for idx in indexes if idx.is_unique and len(idx.columns) == 1}


def _composite_unique_indexes(indexes: List[IndexInfo]) -> List[IndexInfo]:
    return [idx for idx in indexes if idx.is_unique and len(idx.columns) > 1]


def _non_unique_indexes(indexes: List[IndexInfo]) -> List[IndexInfo]:
    return [idx for idx in indexes if not idx.is_unique]


class SQLAlchemyModelGenerator:
    def __init__(self, tables: List[TableInfo]) -> None:
        self.tables = tables

    def generate(self) -> str:
        imports = self._generate_imports()
        models = [self._generate_model(table) for table in self.tables]
        return imports + "\n\n" + "\n\n".join(models) + "\n"

    def _collect_types(self, tables: List[TableInfo]) -> Tuple[Set[str], bool, bool, bool]:
        type_set: Set[str] = set()
        has_index = False
        has_unique_constraint = False
        has_foreign_key = False

        for table in tables:
            for col in table.columns:
                sa_type = MYSQL_TO_SQLALCHEMY.get(col.data_type.lower(), "String")
                type_set.add(sa_type)
            if _non_unique_indexes(table.indexes):
                has_index = True
            if _composite_unique_indexes(table.indexes):
                has_unique_constraint = True
            if table.foreign_keys:
                has_foreign_key = True

        return type_set, has_index, has_unique_constraint, has_foreign_key

    def _format_imports(
        self,
        type_set: Set[str],
        has_index: bool,
        has_unique_constraint: bool,
        has_foreign_key: bool,
    ) -> str:
        type_imports = ", ".join(sorted(type_set))
        lines = [
            "from datetime import datetime",
            "from typing import Optional",
            "",
            f"from sqlalchemy import Column, {type_imports}",
        ]

        extra_imports: List[str] = []
        if has_index:
            extra_imports.append("Index")
        if has_unique_constraint:
            extra_imports.append("UniqueConstraint")
        if extra_imports:
            lines.append(f"from sqlalchemy import {', '.join(extra_imports)}")
        if has_foreign_key:
            lines.append("from sqlalchemy import ForeignKey")
            lines.append("from sqlalchemy.orm import relationship")

        # Use Base (not BaseModel) so introspected columns are not duplicated
        # against the scaffold's id/created_at/updated_at mixins.
        lines.append("")
        lines.append("from app.models.base import Base")

        return "\n".join(lines)

    def _generate_imports(self) -> str:
        type_set, has_index, has_unique, has_fk = self._collect_types(self.tables)
        return self._format_imports(type_set, has_index, has_unique, has_fk)

    def _generate_imports_for_table(self, table: TableInfo) -> str:
        type_set, has_index, has_unique, has_fk = self._collect_types([table])
        return self._format_imports(type_set, has_index, has_unique, has_fk)

    def generate_single(self, table: TableInfo) -> str:
        imports = self._generate_imports_for_table(table)
        model = self._generate_model(table)
        return imports + "\n\n" + model + "\n"

    def _generate_model(self, table: TableInfo) -> str:
        class_name = snake_to_pascal(table.name)
        lines = []
        unique_cols = _single_column_uniques(table.indexes)

        lines.append(f"class {class_name}(Base):")
        if table.comment:
            lines.append(f'    """{table.comment}"""')
        lines.append(f'    __tablename__ = "{table.name}"')
        lines.append("")

        for col in table.columns:
            col_def = self._generate_column(col, table.foreign_keys, unique_cols)
            lines.append(f"    {col_def}")

        table_args = self._generate_table_args(table.indexes)
        if table_args:
            lines.append("")
            lines.extend(table_args)

        if table.foreign_keys:
            lines.append("")
            for fk in table.foreign_keys:
                rel = self._generate_relationship(fk, table.name)
                lines.append(f"    {rel}")

        return "\n".join(lines)

    def _generate_table_args(self, indexes: List[IndexInfo]) -> List[str]:
        non_unique = _non_unique_indexes(indexes)
        composite_unique = _composite_unique_indexes(indexes)
        if not non_unique and not composite_unique:
            return []

        lines = ["    __table_args__ = ("]
        for idx in non_unique:
            cols = ", ".join(f'"{c}"' for c in idx.columns)
            lines.append(f'        Index("{idx.name}", {cols}),')
        for idx in composite_unique:
            cols = ", ".join(f'"{c}"' for c in idx.columns)
            lines.append(f'        UniqueConstraint({cols}, name="{idx.name}"),')
        lines.append("    )")
        return lines

    def _sa_type_expr(self, col: ColumnInfo) -> str:
        sa_type = MYSQL_TO_SQLALCHEMY.get(col.data_type.lower(), "String")
        data_type = col.data_type.lower()

        if sa_type == "String" and data_type in ("char", "varchar", "enum", "set"):
            length = col.max_length or 255
            return f"String({length})"
        if sa_type == "Numeric":
            precision = col.numeric_precision or 10
            scale = col.numeric_scale if col.numeric_scale is not None else 0
            return f"Numeric({precision}, {scale})"
        return sa_type

    def _generate_column(
        self,
        col: ColumnInfo,
        foreign_keys: List[ForeignKeyInfo],
        unique_cols: Set[str],
    ) -> str:
        args: List[str] = [self._sa_type_expr(col)]

        fk = next((f for f in foreign_keys if f.column == col.name), None)
        if fk:
            args.append(f'ForeignKey("{fk.referenced_table}.{fk.referenced_column}")')

        kwargs: List[str] = []

        if col.is_primary_key:
            kwargs.append("primary_key=True")
        if col.is_auto_increment:
            kwargs.append("autoincrement=True")
        if not col.is_nullable and not col.is_primary_key:
            kwargs.append("nullable=False")
        if col.name in unique_cols and not col.is_primary_key:
            kwargs.append("unique=True")
        if col.column_default is not None:
            if col.column_default.upper() == "CURRENT_TIMESTAMP":
                kwargs.append("default=datetime.utcnow")
            elif col.column_default.isdigit():
                kwargs.append(f"default={col.column_default}")
            else:
                kwargs.append(f'default="{col.column_default}"')
        if col.comment:
            escaped_comment = col.comment.replace('"', '\\"')
            kwargs.append(f'comment="{escaped_comment}"')

        args_str = ", ".join(args + kwargs)
        return f"{col.name} = Column({args_str})"

    def _generate_relationship(self, fk: ForeignKeyInfo, table_name: str) -> str:
        related_class = snake_to_pascal(fk.referenced_table)
        rel_name = fk.referenced_table
        return f'{rel_name} = relationship("{related_class}", back_populates="{table_name}s")'


class TortoiseModelGenerator:
    def __init__(self, tables: List[TableInfo]) -> None:
        self.tables = tables

    def generate(self) -> str:
        imports = self._generate_imports()
        models = [self._generate_model(table) for table in self.tables]
        return imports + "\n\n" + "\n\n".join(models) + "\n"

    def _generate_imports(self) -> str:
        return "\n".join(
            [
                "from tortoise import fields",
                "from tortoise.models import Model",
            ]
        )

    def _generate_model(self, table: TableInfo) -> str:
        class_name = snake_to_pascal(table.name)
        lines = []
        unique_cols = _single_column_uniques(table.indexes)

        lines.append(f"class {class_name}(Model):")
        if table.comment:
            lines.append(f'    """{table.comment}"""')
        lines.append("")

        for col in table.columns:
            col_def = self._generate_field(col, table.foreign_keys, table.name, unique_cols)
            lines.append(f"    {col_def}")

        lines.append("")
        lines.append("    class Meta:")
        lines.append(f'        table = "{table.name}"')

        non_unique = _non_unique_indexes(table.indexes)
        if non_unique:
            idx_tuples = [tuple(idx.columns) for idx in non_unique]
            lines.append(f"        indexes = {idx_tuples}")

        composite_unique = _composite_unique_indexes(table.indexes)
        if composite_unique:
            unique_together = [tuple(idx.columns) for idx in composite_unique]
            lines.append(f"        unique_together = {unique_together}")

        return "\n".join(lines)

    def generate_single(self, table: TableInfo) -> str:
        imports = self._generate_imports()
        model = self._generate_model(table)
        return imports + "\n\n" + model + "\n"

    def _generate_field(
        self,
        col: ColumnInfo,
        foreign_keys: List[ForeignKeyInfo],
        table_name: str,
        unique_cols: Set[str],
    ) -> str:
        fk = next((f for f in foreign_keys if f.column == col.name), None)
        if fk:
            related_class = snake_to_pascal(fk.referenced_table)
            return (
                f'{col.name.replace("_id", "")} = fields.ForeignKeyField('
                f'"models.{related_class}", related_name="{table_name}s")'
            )

        data_type = col.data_type.lower()
        field_type = MYSQL_TO_TORTOISE.get(data_type, "CharField")
        kwargs: List[str] = []

        if col.is_primary_key and col.is_auto_increment:
            pk_field = "BigIntField" if data_type == "bigint" else "IntField"
            return f"{col.name} = fields.{pk_field}(pk=True)"

        if col.is_primary_key:
            kwargs.append("pk=True")

        if field_type == "CharField":
            length = col.max_length or 255
            kwargs.append(f"max_length={length}")
        elif field_type == "DecimalField":
            max_digits = col.numeric_precision or 10
            decimal_places = col.numeric_scale if col.numeric_scale is not None else 0
            kwargs.append(f"max_digits={max_digits}")
            kwargs.append(f"decimal_places={decimal_places}")

        if not col.is_nullable and not col.is_primary_key:
            kwargs.append("null=False")
        elif col.is_nullable:
            kwargs.append("null=True")

        if col.name in unique_cols and not col.is_primary_key:
            kwargs.append("unique=True")

        if col.column_default is not None:
            if col.column_default.upper() == "CURRENT_TIMESTAMP":
                kwargs.append("auto_now_add=True")
            elif col.column_default.isdigit():
                kwargs.append(f"default={col.column_default}")
            else:
                kwargs.append(f'default="{col.column_default}"')

        if col.comment:
            escaped_comment = col.comment.replace('"', '\\"')
            kwargs.append(f'description="{escaped_comment}"')

        kwargs_str = ", ".join(kwargs)
        return f"{col.name} = fields.{field_type}({kwargs_str})"


def generate_models(
    tables: List[TableInfo],
    orm: str,
    output_path: Path,
) -> List[Path]:
    """Generate one model file per table; filename is table name (snake_case).py."""
    if orm == "sqlalchemy":
        generator = SQLAlchemyModelGenerator(tables)
    else:
        generator = TortoiseModelGenerator(tables)

    output_path.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for table in tables:
        content = generator.generate_single(table)
        file_path = output_path / f"{table.name}.py"
        file_path.write_text(content, encoding="utf-8")
        written.append(file_path)
    return written
