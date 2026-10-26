import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "kiosko.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabla productos
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            categoria TEXT,
            precio_compra REAL DEFAULT 0,
            precio_venta REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            stock_minimo INTEGER DEFAULT 5
        )
    """)
    
    # Tabla ventas (cabecera)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            total REAL NOT NULL,
            metodo_pago TEXT
        )
    """)
    
    # Tabla detalle ventas
    c.execute("""
        CREATE TABLE IF NOT EXISTS venta_detalle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (venta_id) REFERENCES ventas(id),
            FOREIGN KEY (producto_id) REFERENCES productos(id)
        )
    """)
    
    conn.commit()
    conn.close()

# ============ PRODUCTOS ============
def agregar_producto(nombre, categoria, precio_compra, precio_venta, stock, stock_minimo):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO productos (nombre, categoria, precio_compra, precio_venta, stock, stock_minimo) VALUES (?,?,?,?,?,?)",
            (nombre, categoria, precio_compra, precio_venta, stock, stock_minimo)
        )
        conn.commit()
        return True, "Producto agregado correctamente"
    except sqlite3.IntegrityError:
        return False, "Ya existe un producto con ese nombre"
    finally:
        conn.close()

def obtener_productos():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre", conn)
    conn.close()
    return df

def actualizar_producto(prod_id, nombre, categoria, precio_compra, precio_venta, stock, stock_minimo):
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE productos SET nombre=?, categoria=?, precio_compra=?, 
               precio_venta=?, stock=?, stock_minimo=? WHERE id=?""",
            (nombre, categoria, precio_compra, precio_venta, stock, stock_minimo, prod_id)
        )
        conn.commit()
        return True, "Producto actualizado"
    except sqlite3.IntegrityError:
        return False, "Nombre duplicado"
    finally:
        conn.close()

def eliminar_producto(prod_id):
    conn = get_connection()
    conn.execute("DELETE FROM productos WHERE id=?", (prod_id,))
    conn.commit()
    conn.close()

def actualizar_stock(prod_id, cantidad):
    conn = get_connection()
    conn.execute("UPDATE productos SET stock = stock + ? WHERE id=?", (cantidad, prod_id))
    conn.commit()
    conn.close()

# ============ VENTAS ============
def registrar_venta(items, metodo_pago):
    """items: lista de dicts {producto_id, nombre, cantidad, precio_unitario}"""
    conn = get_connection()
    try:
        total = sum(i["cantidad"] * i["precio_unitario"] for i in items)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cur = conn.execute(
            "INSERT INTO ventas (fecha, total, metodo_pago) VALUES (?,?,?)",
            (fecha, total, metodo_pago)
        )
        venta_id = cur.lastrowid
        
        for item in items:
            subtotal = item["cantidad"] * item["precio_unitario"]
            conn.execute(
                """INSERT INTO venta_detalle 
                   (venta_id, producto_id, cantidad, precio_unitario, subtotal)
                   VALUES (?,?,?,?,?)""",
                (venta_id, item["producto_id"], item["cantidad"], 
                 item["precio_unitario"], subtotal)
            )
            # Descontar stock
            conn.execute(
                "UPDATE productos SET stock = stock - ? WHERE id=?",
                (item["cantidad"], item["producto_id"])
            )
        
        conn.commit()
        return True, venta_id, total
    except Exception as e:
        conn.rollback()
        return False, str(e), 0
    finally:
        conn.close()

def obtener_ventas(fecha_desde=None, fecha_hasta=None):
    conn = get_connection()
    query = "SELECT * FROM ventas"
    params = []
    if fecha_desde and fecha_hasta:
        query += " WHERE date(fecha) BETWEEN ? AND ?"
        params = [fecha_desde, fecha_hasta]
    query += " ORDER BY fecha DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def obtener_detalle_venta(venta_id):
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT d.*, p.nombre as producto
        FROM venta_detalle d
        JOIN productos p ON p.id = d.producto_id
        WHERE d.venta_id = ?
    """, conn, params=[venta_id])
    conn.close()
    return df

def productos_bajo_stock():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM productos WHERE stock <= stock_minimo ORDER BY stock ASC",
        conn
    )
    conn.close()
    return df

def estadisticas(desde, hasta):
    conn = get_connection()
    ventas = pd.read_sql_query(
        "SELECT * FROM ventas WHERE date(fecha) BETWEEN ? AND ?",
        conn, params=[desde, hasta]
    )
    detalle = pd.read_sql_query("""
        SELECT d.*, p.nombre as producto, p.precio_compra
        FROM venta_detalle d
        JOIN productos p ON p.id = d.producto_id
        JOIN ventas v ON v.id = d.venta_id
        WHERE date(v.fecha) BETWEEN ? AND ?
    """, conn, params=[desde, hasta])
    conn.close()
    
    total_ventas = ventas["total"].sum() if not ventas.empty else 0
    num_transacciones = len(ventas)
    
    # Ganancia estimada
    ganancia = 0
    if not detalle.empty:
        detalle["costo"] = detalle["cantidad"] * detalle["precio_compra"]
        detalle["ganancia"] = detalle["subtotal"] - detalle["costo"]
        ganancia = detalle["ganancia"].sum()
    
    return {
        "total_ventas": total_ventas,
        "num_transacciones": num_transacciones,
        "ganancia": ganancia,
        "ventas_df": ventas,
        "detalle_df": detalle
    }