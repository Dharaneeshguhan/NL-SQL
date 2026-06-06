"""SQLite sample warehouse + read-only query helpers."""

import re
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "analytics_agent.db"

SAMPLE_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT, email TEXT, city TEXT,
    country TEXT, joined_date TEXT, segment TEXT
);
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT, category TEXT,
    price REAL, stock INTEGER, supplier TEXT
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER, order_date TEXT,
    status TEXT, total REAL,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER, product_id INTEGER,
    quantity INTEGER, unit_price REAL,
    FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(product_id) REFERENCES products(id)
);

INSERT OR IGNORE INTO customers VALUES
(1,'Alice Chen','alice@acme.com','New York','USA','2022-01-15','Enterprise'),
(2,'Bob Smith','bob@example.com','London','UK','2022-03-22','SMB'),
(3,'Clara Diaz','clara@bizco.com','Madrid','Spain','2022-06-10','Enterprise'),
(4,'David Park','david@techco.com','Seoul','Korea','2021-11-05','SMB'),
(5,'Eva Mueller','eva@startup.de','Berlin','Germany','2023-02-18','Startup'),
(6,'Frank Liu','frank@corp.cn','Shanghai','China','2022-08-30','Enterprise'),
(7,'Grace Kim','grace@sme.kr','Busan','Korea','2023-04-01','SMB'),
(8,'Hiro Tanaka','hiro@jp.co','Tokyo','Japan','2021-07-14','Enterprise'),
(9,'Isla Brown','isla@gb.com','Manchester','UK','2022-12-01','Startup'),
(10,'James Wilson','james@us.com','Chicago','USA','2021-09-20','Enterprise');

INSERT OR IGNORE INTO products VALUES
(1,'Laptop Pro 15','Electronics',1299.99,45,'TechSupplier'),
(2,'Wireless Mouse','Electronics',29.99,230,'TechSupplier'),
(3,'Standing Desk','Furniture',499.00,18,'OfficeFurn'),
(4,'USB-C Hub','Electronics',49.99,95,'TechSupplier'),
(5,'Ergonomic Chair','Furniture',389.00,12,'OfficeFurn'),
(6,'Monitor 27"','Electronics',349.99,60,'TechSupplier'),
(7,'Keyboard Mech','Electronics',129.99,75,'TechSupplier'),
(8,'Notebook Set','Stationery',14.99,500,'PaperCo'),
(9,'Headphones BT','Electronics',199.99,38,'SoundCo'),
(10,'Webcam HD','Electronics',89.99,82,'TechSupplier'),
(11,'Desk Lamp','Furniture',59.99,9,'OfficeFurn'),
(12,'Pen Set','Stationery',8.99,800,'PaperCo');

INSERT OR IGNORE INTO orders VALUES
(1,1,'2024-01-10','completed',2599.98),(2,2,'2024-01-15','completed',79.98),
(3,3,'2024-01-20','completed',1399.00),(4,4,'2024-02-05','completed',499.99),
(5,5,'2024-02-14','pending',389.00),(6,6,'2024-02-20','completed',3249.95),
(7,7,'2024-03-01','completed',449.97),(8,8,'2024-03-10','completed',1699.97),
(9,9,'2024-03-22','cancelled',199.99),(10,10,'2024-04-01','completed',2199.94),
(11,1,'2024-04-15','completed',499.00),(12,2,'2024-04-20','completed',349.99),
(13,3,'2024-05-05','completed',789.97),(14,4,'2024-05-18','pending',129.99),
(15,5,'2024-06-02','completed',1099.98),(16,6,'2024-06-10','completed',4549.93),
(17,7,'2024-06-25','completed',59.99),(18,8,'2024-07-01','completed',929.97),
(19,1,'2024-07-15','completed',1299.99),(20,10,'2024-07-20','completed',699.97);

INSERT OR IGNORE INTO order_items VALUES
(1,1,1,2,1299.99),(2,2,2,2,29.99),(3,2,7,1,129.99),
(4,3,3,1,499.00),(5,3,2,1,29.99),(6,4,4,2,49.99),
(7,4,7,1,129.99),(8,4,8,3,14.99),(9,5,5,1,389.00),
(10,6,1,2,1299.99),(11,6,4,3,49.99),(12,7,2,3,29.99),
(13,7,8,5,14.99),(14,7,12,10,8.99),(15,8,1,1,1299.99),
(16,8,9,1,199.99),(17,8,2,1,29.99),(18,9,9,1,199.99),
(19,10,1,1,1299.99),(20,10,6,1,349.99),(21,10,7,1,129.99),
(22,11,3,1,499.00),(23,12,6,1,349.99),(24,13,2,5,29.99),
(25,13,10,1,89.99),(26,14,7,1,129.99),(27,15,1,1,1299.99),
(28,15,2,3,29.99),(29,16,1,3,1299.99),(30,16,6,1,349.99),
(31,17,11,1,59.99),(32,18,9,1,199.99),(33,18,10,1,89.99),
(34,18,4,1,49.99),(35,19,1,1,1299.99),(36,20,2,3,29.99),
(37,20,9,1,199.99),(38,20,10,1,89.99);
"""

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SAMPLE_SQL)
    conn.commit()
    conn.close()


def _ro_connection() -> sqlite3.Connection:
    uri = f"file:{DB_PATH.resolve()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _sanitize_table_name(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip())
    safe = re.sub(r"^[^a-zA-Z_]+", "", safe)
    return safe or "uploaded_table"


def _make_unique_table_name(base_name: str) -> str:
    base = _sanitize_table_name(base_name)
    name = base
    index = 1
    existing = set(list_tables())
    while name in existing:
        name = f"{base}_{index}"
        index += 1
    return name


def upload_csv_to_db(uploaded_file, table_name: str | None = None, chunksize: int = 100_000) -> tuple[str, pd.DataFrame]:
    if table_name is None:
        table_name = Path(getattr(uploaded_file, "name", "uploaded_table")).stem
    table_name = _make_unique_table_name(table_name)

    uploaded_file.seek(0)
    try:
        preview = pd.read_csv(uploaded_file, nrows=5, low_memory=False)
    except Exception as exc:
        raise ValueError(f"Unable to read CSV preview: {exc}") from exc

    uploaded_file.seek(0)
    conn = sqlite3.connect(DB_PATH)
    try:
        for chunk in pd.read_csv(uploaded_file, chunksize=chunksize, low_memory=False):
            chunk.to_sql(table_name, conn, if_exists="append", index=False, method="multi")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.commit()
        raise
    finally:
        conn.close()

    return table_name, preview


def is_read_only_sql(sql: str) -> bool:
    stripped = sql.strip().rstrip(";")
    if not stripped:
        return False
    if _FORBIDDEN.search(stripped):
        return False
    return stripped.upper().startswith("SELECT") or stripped.upper().startswith("WITH")


def list_tables() -> list[str]:
    conn = _ro_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    conn.close()
    return tables


def describe_table(table_name: str) -> str:
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
        return "Invalid table name."
    conn = _ro_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    if not cur.fetchone():
        conn.close()
        return f"Table '{table_name}' not found."
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = cur.fetchall()
    cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cur.fetchone()[0]
    cur.execute(f"SELECT * FROM {table_name} LIMIT 3")
    sample_rows = cur.fetchall()
    col_names = [c[1] for c in cols]
    conn.close()

    lines = [
        f"TABLE {table_name} ({count} rows)",
        "Columns: " + ", ".join(f"{c[1]} {c[2]}" + (" PK" if c[5] else "") for c in cols),
        "Sample rows:",
    ]
    for row in sample_rows:
        lines.append("  " + str(dict(zip(col_names, row))))
    return "\n".join(lines)


def run_query(sql: str, limit: int = 500) -> tuple[pd.DataFrame | None, str | None]:
    if not is_read_only_sql(sql):
        return None, "Only read-only SELECT / WITH queries are allowed."
    wrapped = sql.strip().rstrip(";")
    if "LIMIT" not in wrapped.upper():
        wrapped = f"{wrapped} LIMIT {limit}"
    try:
        conn = _ro_connection()
        df = pd.read_sql_query(wrapped, conn)
        conn.close()
        return df, None
    except Exception as exc:
        return None, str(exc)


def get_table_info() -> dict:
    info = {}
    for t in list_tables():
        conn = _ro_connection()
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({t})")
        cols = cur.fetchall()
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        count = cur.fetchone()[0]
        conn.close()
        info[t] = {"columns": cols, "count": count}
    return info


def kpi_metrics() -> dict[str, float | int]:
    conn = _ro_connection()
    orders = pd.read_sql(
        "SELECT COUNT(*) as c FROM orders WHERE status='completed'", conn
    ).iloc[0, 0]
    revenue = pd.read_sql(
        "SELECT ROUND(SUM(total),2) as r FROM orders WHERE status='completed'", conn
    ).iloc[0, 0]
    customers = pd.read_sql("SELECT COUNT(*) as c FROM customers", conn).iloc[0, 0]
    products = pd.read_sql("SELECT COUNT(*) as c FROM products", conn).iloc[0, 0]
    conn.close()
    return {
        "orders": int(orders),
        "revenue": float(revenue),
        "customers": int(customers),
        "products": int(products),
    }
