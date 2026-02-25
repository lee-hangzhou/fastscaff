from pathlib import Path
from typing import List, Set

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


class SQLAlchemyModelGenerator:
    def __init__(self, tables: List[TableInfo]) -> None:
        self.tables = tables

    def generate(self) -> str:
        imports = self._generate_imports()
        models = [self._generate_model(table) for table in self.tables]
        return imports + "\n\n" + "\n\n".join(models) + "\n"

    def _generate_imports(self) -> str:
        type_set: Set[str] = set()
        has_index = False
        has_foreign_key = False

        for table in self.tables:
            for col in table.columns:
                sa_type = MYSQL_TO_SQLALCHEMY.get(col.data_type.lower(), "String")
                type_set.add(sa_type)
            if table.indexes:
                has_index = True
            if table.foreign_keys:
                has_foreign_key = True

        type_imports = ", ".join(sorted(type_set))
        lines = [
            "from datetime import datetime",
            "from typing import Optional",
            "",
            f"from sqlalchemy import Column, {type_imports}",
        ]

        if has_index:
            lines.append("from sqlalchemy import Index")
        if has_foreign_key:
            lines.append("from sqlalchemy import ForeignKey")
            lines.append("from sqlalchemy.orm import relationship")

        lines.append("")
        lines.append("from app.models.base import BaseModel")

        return "\n".join(lines)

    def _generate_imports_for_table(self, table: TableInfo) -> str:
        type_set: Set[str] = set()
        has_index = bool(table.indexes)
        has_foreign_key = bool(table.foreign_keys)
        for col in table.columns:
            sa_type = MYSQL_TO_SQLALCHEMY.get(col.data_type.lower(), "String")
            type_set.add(sa_type)
        type_imports = ", ".join(sorted(type_set))
        lines = [
            "from datetime import datetime",
            "from typing import Optional",
            "",
            f"from sqlalchemy import Column, {type_imports}",
        ]
        if has_index:
            lines.append("from sqlalchemy import Index")
        if has_foreign_key:
            lines.append("from sqlalchemy import ForeignKey")
            lines.append("from sqlalchemy.orm import relationship")
        lines.append("")
        lines.append("from app.models.base import BaseModel")
        return "\n".join(lines)

    def generate_single(self, table: TableInfo) -> str:
        imports = self._generate_imports_for_table(table)
        model = self._generate_model(table)
        return imports + "\n\n" + model + "\n"

    def _generate_model(self, table: TableInfo) -> str:
        class_name = snake_to_pascal(table.name)
        lines = []

        # Class definition with docstring
        lines.append(f"class {class_name}(BaseModel):")
        if table.comment:
            lines.append(f'    """{table.comment}"""')
        lines.append(f'    __tablename__ = "{table.name}"')
        lines.append("")

        # Columns
        for col in table.columns:
            col_def = self._generate_column(col, table.foreign_keys)
            lines.append(f"    {col_def}")

        # Indexes (non-unique indexes only, unique is handled in column)
        non_pk_indexes = [idx for idx in table.indexes if not idx.is_unique]
        if non_pk_indexes:
            lines.append("")
            lines.append("    __table_args__ = (")
            for idx in non_pk_indexes:
                cols = ", ".join(f'"{c}"' for c in idx.columns)
                lines.append(f'        Index("{idx.name}", {cols}),')
            lines.append("    )")

        # Relationships
        if table.foreign_keys:
            lines.append("")
            for fk in table.foreign_keys:
                rel = self._generate_relationship(fk, table.name)
                lines.append(f"    {rel}")

        return "\n".join(lines)

    def _generate_column(
        self, col: ColumnInfo, foreign_keys: List[ForeignKeyInfo]
    ) -> str:
        sa_type = MYSQL_TO_SQLALCHEMY.get(col.data_type.lower(), "String")

        # Build column arguments
        args = []

        # Check if this column is a foreign key
        fk = next((f for f in foreign_keys if f.column == col.name), None)
        if fk:
            args.append(f'ForeignKey("{fk.referenced_table}.{fk.referenced_column}")')

        # Type with length for string types
        if sa_type == "String" and col.data_type.lower() in ("char", "varchar"):
            args.insert(0, "String(255)")
        else:
            args.insert(0, sa_type)

        kwargs = []

        if col.is_primary_key:
            kwargs.append("primary_key=True")
        if col.is_auto_increment:
            kwargs.append("autoincrement=True")
        if not col.is_nullable and not col.is_primary_key:
            kwargs.append("nullable=False")
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

        all_args = args + kwargs
        args_str = ", ".join(all_args)

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
        lines = [
            "from tortoise import fields",
            "from tortoise.models import Model",
        ]
        return "\n".join(lines)

    def _generate_model(self, table: TableInfo) -> str:
        class_name = snake_to_pascal(table.name)
        lines = []

        lines.append(f"class {class_name}(Model):")
        if table.comment:
            lines.append(f'    """{table.comment}"""')
        lines.append("")

        # Columns
        for col in table.columns:
            col_def = self._generate_field(col, table.foreign_keys, table.name)
            lines.append(f"    {col_def}")

        # Meta class
        lines.append("")
        lines.append("    class Meta:")
        lines.append(f'        table = "{table.name}"')

        # Indexes
        indexes = [idx for idx in table.indexes if not idx.is_unique]
        if indexes:
            idx_tuples = [tuple(idx.columns) for idx in indexes]
            lines.append(f"        indexes = {idx_tuples}")

        return "\n".join(lines)

    def generate_single(self, table: TableInfo) -> str:
        imports = self._generate_imports()
        model = self._generate_model(table)
        return imports + "\n\n" + model + "\n"

    def _generate_field(
        self, col: ColumnInfo, foreign_keys: List[ForeignKeyInfo], table_name: str
    ) -> str:
        # Check if this column is a foreign key
        fk = next((f for f in foreign_keys if f.column == col.name), None)
        if fk:
            related_class = snake_to_pascal(fk.referenced_table)
            return (
                f'{col.name.replace("_id", "")} = fields.ForeignKeyField('
                f'"models.{related_class}", related_name="{table_name}s")'
            )

        field_type = MYSQL_TO_TORTOISE.get(col.data_type.lower(), "CharField")

        kwargs = []

        if col.is_primary_key:
            if col.is_auto_increment:
                return f"{col.name} = fields.IntField(pk=True)"
            kwargs.append("pk=True")

        if field_type == "CharField":
            kwargs.append("max_length=255")

        if not col.is_nullable and not col.is_primary_key:
            kwargs.append("null=False")
        elif col.is_nullable:
            kwargs.append("null=True")

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

