"""SQLite database utilities: initialization, schema access, and safe query execution."""

from __future__ import annotations

import io
import re
import sqlite3
from pathlib import Path

import pandas as pd

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "company.db"
SAMPLE_DATA_DIR = PROJECT_ROOT / "database" / "sample_data"

# CSV upload configuration
CSV_UPLOAD_TABLE_PREFIX = "uploaded_"
MAX_CSV_SIZE_MB = 50
UPLOADED_TABLES_KEY = "_uploaded_tables_metadata"

CUSTOMER_ORDER_SQL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT,
    city TEXT,
    country TEXT,
    joined_date TEXT,
    segment TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    order_date TEXT,
    status TEXT,
    total REAL,
    FOREIGN KEY(customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER,
    unit_price REAL,
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

# Block any mutating or DDL statements (security requirement)
_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|TRUNCATE|CREATE|REPLACE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)


def init_db(force: bool = False) -> None:
    """
    Create company.db from sample CSV files if it does not exist.

    Tables: departments, employees, products, sales
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists() and not force:
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        # Load CSVs into pandas then into SQLite
        departments = pd.read_csv(SAMPLE_DATA_DIR / "departments.csv")
        employees = pd.read_csv(SAMPLE_DATA_DIR / "employees.csv")
        products = pd.read_csv(SAMPLE_DATA_DIR / "products.csv")
        sales = pd.read_csv(SAMPLE_DATA_DIR / "sales.csv")

        departments.to_sql("departments", conn, if_exists="replace", index=False)
        employees.to_sql("employees", conn, if_exists="replace", index=False)
        products.to_sql("products", conn, if_exists="replace", index=False)
        sales.to_sql("sales", conn, if_exists="replace", index=False)

        # Add foreign-key metadata (SQLite enforces when PRAGMA foreign_keys=ON)
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_employees_dept ON employees(department_id);
            CREATE INDEX IF NOT EXISTS idx_sales_product ON sales(product_id);
            CREATE INDEX IF NOT EXISTS idx_sales_employee ON sales(employee_id);
            CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(sale_date);
            """
        )
        conn.executescript(CUSTOMER_ORDER_SQL)
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
            CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
            CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
            CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


def _read_only_connection() -> sqlite3.Connection:
    """Open database in read-only mode via URI."""
    uri = f"file:{DB_PATH.resolve()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def is_read_only_sql(sql: str) -> bool:
    """Return True if SQL appears to be a safe read-only SELECT/WITH query."""
    stripped = sql.strip().rstrip(";")
    if not stripped:
        return False
    if _FORBIDDEN_KEYWORDS.search(stripped):
        return False
    upper = stripped.upper()
    return upper.startswith("SELECT") or upper.startswith("WITH")


def list_tables() -> list[str]:
    """Return sorted list of user table names."""
    conn = _read_only_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def get_table_info() -> dict[str, dict]:
    """
    Return schema metadata for the Streamlit sidebar explorer.

    Each table entry: {columns: PRAGMA rows, count: row count}
    """
    info: dict[str, dict] = {}
    for table in list_tables():
        conn = _read_only_connection()
        try:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = cur.fetchall()
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            info[table] = {"columns": cols, "count": count}
        finally:
            conn.close()
    return info


def execute_query(sql: str, limit: int = 500) -> tuple[pd.DataFrame | None, str | None]:
    """
    Execute a validated read-only query and return (DataFrame, error).

    Automatically appends LIMIT when missing to prevent huge result sets.
    """
    if not is_read_only_sql(sql):
        return None, "Only SELECT statements are allowed. Mutating SQL is blocked."

    wrapped = sql.strip().rstrip(";")
    if "LIMIT" not in wrapped.upper():
        wrapped = f"{wrapped} LIMIT {limit}"

    try:
        conn = _read_only_connection()
        try:
            df = pd.read_sql_query(wrapped, conn)
            return df, None
        finally:
            conn.close()
    except Exception as exc:
        return None, str(exc)


def kpi_metrics() -> dict[str, float | int]:
    """Dashboard KPIs for the Streamlit header."""
    conn = _read_only_connection()
    try:
        total_sales = pd.read_sql(
            "SELECT ROUND(COALESCE(SUM(total_amount), 0), 2) AS v FROM sales", conn
        ).iloc[0, 0]
        employees = pd.read_sql("SELECT COUNT(*) AS v FROM employees", conn).iloc[0, 0]
        products = pd.read_sql("SELECT COUNT(*) AS v FROM products", conn).iloc[0, 0]
        departments = pd.read_sql("SELECT COUNT(*) AS v FROM departments", conn).iloc[0, 0]
        return {
            "total_sales": float(total_sales),
            "employees": int(employees),
            "products": int(products),
            "departments": int(departments),
        }
    finally:
        conn.close()


def load_csv_to_sqlite(
    csv_file: io.BytesIO,
    original_filename: str,
    session_state: dict = None,
) -> tuple[str, pd.DataFrame, str | None]:
    """
    Load a CSV file into a temporary SQLite table.
    
    Args:
        csv_file: BytesIO object containing CSV data
        original_filename: Original filename for display/naming
        session_state: Streamlit session state for metadata tracking
        
    Returns:
        (table_name, dataframe, error_message)
        - table_name: Name of the created table (with csv_ prefix) or None on error
        - dataframe: Loaded dataframe or None on error
        - error_message: Error description if failed, None on success
    """
    try:
        # Read CSV into dataframe
        csv_file.seek(0)
        df = pd.read_csv(csv_file, dtype_backend="numpy_nullable", low_memory=False)
        
        if df.empty:
            return None, None, "CSV file is empty."
        
        if len(df.columns) == 0:
            return None, None, "CSV has no columns."
        
        # Sanitize column names: lowercase, replace spaces with underscores
        df.columns = [str(col).lower().replace(" ", "_").replace("-", "_") for col in df.columns]
        
        # Generate table name from filename
        base_name = Path(original_filename).stem.lower().replace("-", "_").replace(" ", "_")
        base_name = re.sub(r"[^a-z0-9_]", "", base_name)
        if not base_name:
            base_name = "data"
        
        # Ensure unique table name
        table_name = f"{CSV_UPLOAD_TABLE_PREFIX}{base_name}"
        counter = 1
        original_table_name = table_name
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            while True:
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table_name,)
                )
                if not cursor.fetchone():
                    break
                table_name = f"{original_table_name}_{counter}"
                counter += 1
            
            # Load dataframe into SQLite
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            conn.commit()
            
            # Track uploaded table in session state
            if session_state is not None:
                if UPLOADED_TABLES_KEY not in session_state:
                    session_state[UPLOADED_TABLES_KEY] = {}
                
                session_state[UPLOADED_TABLES_KEY][table_name] = {
                    "filename": original_filename,
                    "row_count": len(df),
                    "columns": list(df.columns),
                    "uploaded_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            return table_name, df, None
        finally:
            conn.close()
            
    except pd.errors.EmptyDataError:
        return None, None, "CSV file is empty."
    except pd.errors.ParserError as e:
        return None, None, f"Failed to parse CSV: {str(e)}"
    except Exception as e:
        return None, None, f"Error loading CSV: {str(e)}"


def get_uploaded_tables(session_state: dict = None) -> dict[str, dict]:
    """
    Get metadata for all uploaded tables in the session.
    
    Args:
        session_state: Streamlit session state dict
        
    Returns:
        Dict mapping table names to metadata
    """
    if session_state is None:
        return {}
    return session_state.get(UPLOADED_TABLES_KEY, {})


def is_uploaded_table(table_name: str) -> bool:
    """Check if a table is an uploaded CSV table."""
    return table_name.startswith(CSV_UPLOAD_TABLE_PREFIX)


def drop_uploaded_table(table_name: str, session_state: dict = None) -> tuple[bool, str]:
    """
    Drop an uploaded table from the database.
    
    Args:
        table_name: Name of the table to drop
        session_state: Streamlit session state dict
        
    Returns:
        (success, message)
    """
    if not is_uploaded_table(table_name):
        return False, "Can only drop uploaded tables."
    
    try:
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            conn.commit()
            
            # Remove from session state
            if session_state is not None and UPLOADED_TABLES_KEY in session_state:
                session_state[UPLOADED_TABLES_KEY].pop(table_name, None)
            
            return True, f"Dropped table '{table_name}'."
        finally:
            conn.close()
    except Exception as e:
        return False, f"Error dropping table: {str(e)}"


def clear_all_uploaded_tables(session_state: dict = None) -> tuple[int, str]:
    """
    Drop all uploaded tables from the session.
    
    Returns:
        (count_dropped, error_message or empty string)
    """
    metadata = get_uploaded_tables(session_state)
    count = 0
    errors = []
    
    for table_name in list(metadata.keys()):
        success, msg = drop_uploaded_table(table_name, session_state)
        if success:
            count += 1
        else:
            errors.append(msg)
    
    error_msg = " ".join(errors) if errors else ""
    return count, error_msg
