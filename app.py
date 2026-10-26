import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import database as db

# Inicializar BD
db.init_db()

st.set_page_config(
    page_title="Kiosko Manager",
    page_icon="🏪",
    layout="wide"
)

# Estado de sesión para el carrito
if "carrito" not in st.session_state:
    st.session_state.carrito = []

st.title("🏪 Kiosko Manager")

# Sidebar de navegación
menu = st.sidebar.selectbox(
    "📋 Menú",
    ["🛒 Nueva Venta", "📦 Productos", "📊 Ventas", "⚠️ Bajo Stock", "📈 Reportes"]
)

# ============================================================
# NUEVA VENTA
# ============================================================
if menu == "🛒 Nueva Venta":
    st.header("🛒 Punto de Venta")
    
    productos = db.obtener_productos()
    
    if productos.empty:
        st.warning("No hay productos cargados. Andá a la sección Productos para agregar.")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Agregar producto al carrito")
            with st.form("agregar_item", clear_on_submit=True):
                productos_disponibles = productos[productos["stock"] > 0]
                
                if productos_disponibles.empty:
                    st.warning("No hay productos con stock disponible")
                else:
                    prod_nombre = st.selectbox(
                        "Producto",
                        productos_disponibles["nombre"].tolist()
                    )
                    prod_row = productos_disponibles[productos_disponibles["nombre"] == prod_nombre].iloc[0]
                    
                    st.caption(f"Stock disponible: {prod_row['stock']} | Precio: ${prod_row['precio_venta']:.2f}")
                    
                    cantidad = st.number_input(
                        "Cantidad",
                        min_value=1,
                        max_value=int(prod_row["stock"]),
                        value=1
                    )
                    
                    agregar = st.form_submit_button("➕ Agregar al carrito")
                    
                    if agregar:
                        # Verificar si ya está en carrito
                        existente = next((i for i in st.session_state.carrito 
                                          if i["producto_id"] == prod_row["id"]), None)
                        if existente:
                            existente["cantidad"] += cantidad
                        else:
                            st.session_state.carrito.append({
                                "producto_id": int(prod_row["id"]),
                                "nombre": prod_row["nombre"],
                                "cantidad": cantidad,
                                "precio_unitario": float(prod_row["precio_venta"])
                            })
                        st.rerun()
        
        with col2:
            st.subheader("💰 Carrito")
            if not st.session_state.carrito:
                st.info("Carrito vacío")
            else:
                for i, item in enumerate(st.session_state.carrito):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{item['nombre']}**")
                        st.caption(f"{item['cantidad']} x ${item['precio_unitario']:.2f}")
                    with col_b:
                        if st.button("❌", key=f"del_{i}"):
                            st.session_state.carrito.pop(i)
                            st.rerun()
                
                total = sum(i["cantidad"] * i["precio_unitario"] 
                           for i in st.session_state.carrito)
                st.markdown(f"### Total: ${total:.2f}")
                
                st.divider()
                metodo_pago = st.selectbox(
                    "Método de pago",
                    ["Efectivo", "Débito", "Crédito", "MercadoPago", "Transferencia"]
                )
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Cobrar", type="primary", use_container_width=True):
                        ok, msg, _ = db.registrar_venta(
                            st.session_state.carrito, metodo_pago
                        )
                        if ok:
                            st.success(f"Venta registrada! Total: ${total:.2f}")
                            st.session_state.carrito = []
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"Error: {msg}")
                
                with col_btn2:
                    if st.button("🗑️ Vaciar", use_container_width=True):
                        st.session_state.carrito = []
                        st.rerun()

# ============================================================
# PRODUCTOS
# ============================================================
elif menu == "📦 Productos":
    st.header("📦 Gestión de Productos")
    
    tab1, tab2, tab3 = st.tabs(["Ver/Editar", "Agregar", "Eliminar"])
    
    with tab1:
        productos = db.obtener_productos()
        if productos.empty:
            st.info("No hay productos cargados todavía")
        else:
            # Filtro
            busqueda = st.text_input("🔍 Buscar producto")
            if busqueda:
                productos = productos[
                    productos["nombre"].str.contains(busqueda, case=False, na=False)
                ]
            
            st.dataframe(
                productos[["id", "nombre", "categoria", "precio_compra",
                          "precio_venta", "stock", "stock_minimo"]],
                use_container_width=True,
                hide_index=True
            )
            
            st.divider()
            st.subheader("✏️ Editar producto")
            
            if not productos.empty:
                prod_id = st.selectbox(
                    "Seleccionar producto",
                    productos["id"].tolist(),
                    format_func=lambda x: productos[productos["id"] == x]["nombre"].values[0]
                )
                prod = productos[productos["id"] == prod_id].iloc[0]
                
                with st.form("editar_form"):
                    c1, c2 = st.columns(2)
                    with c1:
                        nombre = st.text_input("Nombre", value=prod["nombre"])
                        categoria = st.text_input("Categoría", value=prod["categoria"] or "")
                        precio_compra = st.number_input(
                            "Precio compra", value=float(prod["precio_compra"]), min_value=0.0
                        )
                    with c2:
                        precio_venta = st.number_input(
                            "Precio venta", value=float(prod["precio_venta"]), min_value=0.0
                        )
                        stock = st.number_input(
                            "Stock", value=int(prod["stock"]), min_value=0
                        )
                        stock_minimo = st.number_input(
                            "Stock mínimo", value=int(prod["stock_minimo"]), min_value=0
                        )
                    
                    if st.form_submit_button("💾 Guardar cambios"):
                        ok, msg = db.actualizar_producto(
                            prod_id, nombre, categoria, precio_compra,
                            precio_venta, stock, stock_minimo
                        )
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    
    with tab2:
        st.subheader("➕ Agregar nuevo producto")
        with st.form("nuevo_producto", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                nombre = st.text_input("Nombre *")
                categoria = st.text_input("Categoría")
                precio_compra = st.number_input("Precio compra", min_value=0.0, value=0.0)
            with c2:
                precio_venta = st.number_input("Precio venta *", min_value=0.0, value=0.0)
                stock = st.number_input("Stock inicial", min_value=0, value=0)
                stock_minimo = st.number_input("Stock mínimo", min_value=0, value=5)
            
            if st.form_submit_button("Guardar producto"):
                if not nombre:
                    st.error("El nombre es obligatorio")
                else:
                    ok, msg = db.agregar_producto(
                        nombre, categoria, precio_compra, precio_venta, stock, stock_minimo
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    
    with tab3:
        st.subheader("🗑️ Eliminar producto")
        productos = db.obtener_productos()
        if not productos.empty:
            prod_id = st.selectbox(
                "Producto a eliminar",
                productos["id"].tolist(),
                format_func=lambda x: productos[productos["id"] == x]["nombre"].values[0],
                key="del_prod"
            )
            st.warning("⚠️ Esta acción no se puede deshacer")
            if st.button("Eliminar definitivamente", type="primary"):
                db.eliminar_producto(prod_id)
                st.success("Producto eliminado")
                st.rerun()
        else:
            st.info("No hay productos para eliminar")

# ============================================================
# VENTAS
# ============================================================
elif menu == "📊 Ventas":
    st.header("📊 Historial de Ventas")
    
    hoy = date.today()
    col1, col2 = st.columns(2)
    with col1:
        desde = st.date_input("Desde", hoy - timedelta(days=30))
    with col2:
        hasta = st.date_input("Hasta", hoy)
    
    ventas = db.obtener_ventas(desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"))
    
    if ventas.empty:
        st.info("No hay ventas en el período seleccionado")
    else:
        total = ventas["total"].sum()
        st.metric("💵 Total facturado", f"${total:,.2f}", f"{len(ventas)} transacciones")
        
        st.dataframe(
            ventas[["id", "fecha", "total", "metodo_pago"]],
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        st.subheader("🔍 Detalle de venta")
        venta_id = st.selectbox("Seleccionar venta", ventas["id"].tolist())
        detalle = db.obtener_detalle_venta(venta_id)
        if not detalle.empty:
            st.dataframe(
                detalle[["producto", "cantidad", "precio_unitario", "subtotal"]],
                use_container_width=True,
                hide_index=True
            )

# ============================================================
# BAJO STOCK
# ============================================================
elif menu == "⚠️ Bajo Stock":
    st.header("⚠️ Productos con Stock Bajo")
    
    prods = db.productos_bajo_stock()
    if prods.empty:
        st.success("✅ Todo el stock está en niveles normales")
    else:
        st.warning(f"Hay {len(prods)} productos con stock bajo")
        st.dataframe(
            prods[["id", "nombre", "categoria", "stock", "stock_minimo"]],
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        st.subheader("📥 Reponer stock")
        prod_id = st.selectbox(
            "Producto",
            prods["id"].tolist(),
            format_func=lambda x: prods[prods["id"] == x]["nombre"].values[0]
        )
        cantidad = st.number_input("Cantidad a agregar", min_value=1, value=10)
        if st.button("➕ Reponer", type="primary"):
            db.actualizar_stock(prod_id, int(cantidad))
            st.success("Stock actualizado")
            st.rerun()

# ============================================================
# REPORTES
# ============================================================
elif menu == "📈 Reportes":
    st.header("📈 Reportes y Estadísticas")
    
    hoy = date.today()
    col1, col2 = st.columns(2)
    with col1:
        desde = st.date_input("Desde", hoy - timedelta(days=7), key="rep_desde")
    with col2:
        hasta = st.date_input("Hasta", hoy, key="rep_hasta")
    
    stats = db.estadisticas(desde.strftime("%Y-%m-%d"), hasta.strftime("%Y-%m-%d"))
    
    col1, col2, col3 = st.columns(3)
    col1.metric("💵 Ventas totales", f"${stats['total_ventas']:,.2f}")
    col2.metric("🧾 Transacciones", stats["num_transacciones"])
    col3.metric("📈 Ganancia estimada", f"${stats['ganancia']:,.2f}")
    
    ventas_df = stats["ventas_df"]
    detalle_df = stats["detalle_df"]
    
    if not ventas_df.empty:
        st.subheader("📅 Ventas por día")
        ventas_df["fecha_dia"] = pd.to_datetime(ventas_df["fecha"]).dt.date
        por_dia = ventas_df.groupby("fecha_dia")["total"].sum()
        st.bar_chart(por_dia)
        
        st.subheader("💳 Ventas por método de pago")
        por_metodo = ventas_df.groupby("metodo_pago")["total"].sum()
        st.bar_chart(por_metodo)
    
    if not detalle_df.empty:
        st.subheader("🏆 Productos más vendidos")
        top = detalle_df.groupby("producto").agg(
            cantidad=("cantidad", "sum"),
            ingresos=("subtotal", "sum")
        ).sort_values("cantidad", ascending=False).head(10)
        st.dataframe(top, use_container_width=True)
        
        st.subheader("💰 Productos más rentables")
        top_rent = detalle_df.groupby("producto").agg(
            ganancia=("ganancia", "sum")
        ).sort_values("ganancia", ascending=False).head(10)
        st.dataframe(top_rent, use_container_width=True)