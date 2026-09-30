from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def _default_clause_for(column):
    """A constant SQL default so SQLite will accept ADD COLUMN on a non-empty table."""
    if column.default is not None and getattr(column.default, "is_scalar", False):
        value = column.default.arg
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        return f"'{value}'"
    type_name = str(column.type).upper()
    if "BOOL" in type_name or "INT" in type_name:
        return "0"
    if "CHAR" in type_name or "TEXT" in type_name or "VARCHAR" in type_name:
        return "''"
    return "NULL"

def sync_schema():
    """
    Self-heals an existing database file when the code's models have grown new
    columns since that file was created. SQLAlchemy's create_all() only creates
    tables that don't exist yet — it never alters existing ones — so without
    this, upgrading the app while keeping an old .db file causes every query
    touching the new column to fail with "no such column: ...".

    Runs once at startup, is a no-op once the schema is already current, and
    only ever adds columns — it never drops or renames anything, so existing
    data is never touched.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.connect() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue  # brand-new table — create_all() already handled it
            existing_columns = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                not_null = "NOT NULL" if not column.nullable else ""
                default = f"DEFAULT {_default_clause_for(column)}"
                ddl = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {not_null} {default}".strip()
                conn.execute(text(ddl))
                print(f">>> Migrated: added column {table_name}.{column.name}")
        conn.commit()