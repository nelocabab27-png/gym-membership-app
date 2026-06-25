import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st
import os
import base64

# Configure the Streamlit page layout
st.set_page_config(page_title="Starbucks Philippines Menu", layout="wide")

# Database configuration (v6 to refresh layout changes)
DB_FILE = "starbucks_v7.db"

# Custom CSS to mimic the exact Starbucks styling from image_6e8a5f.png
st.markdown("""
    <style>
    /* Top Navbar styling */
    .stAppHeader {
        background-color: white !important;
    }
    /* Left Sidebar text categories */
    .category-title {
        font-size: 22px;
        font-weight: 800;
        color: #212121;
        margin-bottom: 20px;
        font-family: SoDoSans, sans-serif;
    }
    /* Circular image formatting to clip rectangular assets perfectly */
    .product-circle {
        border-radius: 50% !important;
        width: 130px !important;
        height: 130px !important;
        object-fit: cover !important;
        display: block;
        margin-left: auto;
        margin-right: auto;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .product-row {
        display: flex;
        align-items: center;
        margin-bottom: 30px;
        gap: 20px;
    }
    .product-name {
        font-size: 18px;
        font-weight: bold;
        color: #212121;
        margin-bottom: 2px;
        font-family: SoDoSans, sans-serif;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to inject local images smoothly into circular HTML frames
def get_image_html(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode()
        return f'<img src="data:image/png;base64,{encoded}" class="product-circle">'
    else:
        # High-fidelity fallback circle using the iconic Starbucks Green brand color
        return '<div style="background-color: #006241; border-radius: 50%; width: 130px; height: 130px; display: flex; align-items: center; justify-content: center; color: white; font-size: 40px; margin: auto;">☕</div>'

# ==========================================
# DATABASE SETUP
# ==========================================
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name VARCHAR(100) NOT NULL,
            category VARCHAR(50) NOT NULL,
            base_price DECIMAL(10, 2) NOT NULL,
            image_url TEXT NOT NULL
        );
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_channel VARCHAR(30) NOT NULL,
            is_rewards_member INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            size VARCHAR(10) NOT NULL,
            temperature VARCHAR(10) NOT NULL,
            sugar_level VARCHAR(20) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            item_total DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
        """)
        
        cursor.execute("SELECT COUNT(*) FROM products;")
        if cursor.fetchone()[0] == 0:
            products = [
                ('Iced Caramel Macchiato', 'Iced Espresso', 185.00, 'images/caramel.jpg'),
                ('Caffè Latte', 'Hot Espresso', 165.00, 'images/latte.jpg'),
                ('Iced Americano', 'Iced Espresso', 155.00, 'images/americano.jpg'),
                ('Pure Matcha Cream Frappuccino', 'Blended Beverage', 195.00, 'images/matcha.jpg'),
                ('Iced White Chocolate Mocha', 'Iced Espresso', 190.00, 'images/mocha.jpg')
            ]
            cursor.executemany("INSERT INTO products (product_name, category, base_price, image_url) VALUES (?, ?, ?, ?);", products)
            conn.commit()

init_db()

def run_query(query, params=()):
    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(query, conn, params=params)

# ==========================================
# SESSION STATE MANAGEMENT
# ==========================================
if "order_step" not in st.session_state:
    st.session_state.order_step = 1
if "wiz_drink" not in st.session_state:
    st.session_state.wiz_drink = None
if "wiz_qty" not in st.session_state:
    st.session_state.wiz_qty = 1
if "wiz_temp" not in st.session_state:
    st.session_state.wiz_temp = "Iced"
if "wiz_size" not in st.session_state:
    st.session_state.wiz_size = "Tall"
if "wiz_sugar" not in st.session_state:
    st.session_state.wiz_sugar = "100% (Regular Sweet)"

# ==========================================
# STARBUCKS TOP NAVIGATION BAR
# ==========================================
LOGO_URL = "https://upload.wikimedia.org/wikipedia/en/d/d3/Starbucks_Corporation_Logo.svg"
navbar_col1, navbar_col2 = st.columns([1, 5])
with navbar_col1:
    st.image(LOGO_URL, width=60)
with navbar_col2:
    st.markdown("""
        <div style='display: flex; gap: 30px; margin-top: 15px; font-family: sans-serif; font-weight: bold; font-size: 14px; letter-spacing: 0.1em;'>
            <span style='color: #006241; border-bottom: 4px solid #006241; padding-bottom: 5px; cursor: pointer;'>MENU</span>
            <span style='color: #212121; cursor: pointer;'>MERCHANDISE</span>
            <span style='color: #212121; cursor: pointer;'>REWARDS</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("---")

tab_order, tab_ops, tab_custom = st.tabs(["🛒 Place an Order", "⚡ Live Operations Dashboard", "☕ Customization Trends"])

with tab_order:
    df_menu = run_query("SELECT product_id, product_name, category, base_price, image_url FROM products;")
    
    # --- STEP 1: WEB-STYLE MENU VIEW ---
    if st.session_state.order_step == 1:
        col_left, col_right = st.columns([1, 3])
        
        with col_left:
            st.markdown("<p class='category-title'>Drinks</p>", unsafe_allow_html=True)
            selected_cat = st.radio(
                label="Categories",
                options=["All Drinks", "Iced Espresso", "Hot Espresso", "Blended Beverage"],
                label_visibility="collapsed"
            )
        
        with col_right:
            search_query = st.text_input(label="Search", placeholder="🔍 Search our drinks, food, coffee", label_visibility="collapsed")
            
            st.markdown(f"## {selected_cat if selected_cat != 'All Drinks' else 'Drinks'}")
            st.markdown("---")
            
            filtered_df = df_menu
            if selected_cat != "All Drinks":
                filtered_df = filtered_df[filtered_df["category"] == selected_cat]
            if search_query:
                filtered_df = filtered_df[filtered_df["product_name"].str.contains(search_query, case=False)]
            
            # Formats the layout into a clean grid columns matching image_6e8a5f.png
            if not filtered_df.empty:
                for i in range(0, len(filtered_df), 2):
                    grid_cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(filtered_df):
                            item = filtered_df.iloc[i + j]
                            with grid_cols[j]:
                                c_img, c_txt = st.columns([1, 1.3])
                                with c_img:
                                    # Formats local images (like your caramel photo) into a round layout mask
                                    img_html = get_image_html(item['image_url'])
                                    st.markdown(img_html, unsafe_allow_html=True)
                                with c_txt:
                                    st.markdown(f"<p class='product-name'>{item['product_name']}</p>", unsafe_allow_html=True)
                                    st.caption(f"Base Price: ₱{item['base_price']:.2f}")
                                    if st.button(f"Select", key=f"sel_{item['product_id']}"):
                                        st.session_state.wiz_drink = item['product_name']
                                        st.session_state.order_step = 2
                                        st.rerun()
            else:
                st.info("No drinks matched your search criteria.")

    # --- STEP 2: MODIFICATIONS PANEL ---
    elif st.session_state.order_step == 2:
        st.subheader("🎨 Step 2: Item Modifications")
        st.write(f"Customizing your beverage choice: **{st.session_state.wiz_drink}**")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.radio("Temperature Option:", ["Hot", "Iced"], key="wiz_temp")
            st.radio("Select Size Option:", ["Tall", "Grande (+₱15)", "Venti (+₱30)"], key="wiz_size")
            st.number_input("How many cups?", min_value=1, max_value=10, step=1, key="wiz_qty")
        
        with col_m2:
            st.select_slider(
                "Sugar Concentration:",
                options=["0% (Unsweetened)", "25% (Low Sweet)", "50% (Less Sweet)", "100% (Regular Sweet)"],
                key="wiz_sugar"
            )
            
        st.markdown("---")
        btn_col1, btn_col2 = st.columns([1, 4])
        if btn_col1.button("⬅️ Back Menu"):
            st.session_state.order_step = 1
            st.rerun()
        if btn_col2.button("Next: Proceed to Checkout ➡️", type="primary"):
            st.session_state.order_step = 3
            st.rerun()

    # --- STEP 3: REVIEW & CHECKOUT ---
    elif st.session_state.order_step == 3:
        st.subheader("🏁 Step 3: Review & Complete Order")
        
        drink_info = df_menu[df_menu["product_name"] == st.session_state.wiz_drink].iloc[0]
        base_price = float(drink_info["base_price"])
        
        size_clean = st.session_state.wiz_size.split()[0]
        size_modifier = 15.00 if size_clean == "Grande" else (30.00 if size_clean == "Venti" else 0.00)
        total_bill = (base_price + size_modifier) * st.session_state.wiz_qty
        
        with st.container(border=True):
            st.write("### 🧾 Receipt Overview")
            st.write(f"**Item:** {st.session_state.wiz_qty}x {size_clean} {st.session_state.wiz_drink} ({st.session_state.wiz_temp})")
            st.write(f"**Customization:** Custom Sugar Level set to *{st.session_state.wiz_sugar}*")
            st.markdown(f"## Total Balance Due: :green[₱{total_bill:,.2f}]")
            
        st.markdown("### Service Details")
        c1, c2 = st.columns(2)
        with c1:
            st.selectbox("Collection Method:", ["In-Store", "Drive-Thru", "Mobile App"], key="wiz_channel")
        with c2:
            st.checkbox("Apply My Starbucks Rewards Member Status", key="wiz_rewards")
            
        st.markdown("---")
        btn_col1, btn_col2 = st.columns([1, 4])
        if btn_col1.button("⬅️ Back to Customizations"):
            st.session_state.order_step = 2
            st.rerun()
            
        if btn_col2.button("🚀 Confirm and Place Order", type="primary"):
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                rewards_val = 1 if st.session_state.wiz_rewards else 0
                cursor.execute(
                    "INSERT INTO orders (order_channel, is_rewards_member) VALUES (?, ?);",
                    (st.session_state.wiz_channel, rewards_val)
                )
                last_id = cursor.lastrowid
                
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, size, temperature, sugar_level, quantity, item_total) 
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (last_id, int(drink_info["product_id"]), size_clean, st.session_state.wiz_temp, st.session_state.wiz_sugar, st.session_state.wiz_qty, total_bill))
                conn.commit()
                
            st.success("🎉 Transaction complete! Enjoy your coffee.")
            st.balloons()
            
            st.session_state.order_step = 1
            st.session_state.wiz_drink = None
            st.rerun()

# ==========================================
# ANALYTICS DASHBOARDS
# ==========================================
with tab_ops:
    df_metrics = run_query("SELECT SUM(item_total) as rev, COUNT(DISTINCT order_id) as orders FROM order_items;")
    gross_rev = df_metrics["rev"].iloc[0] or 0.0
    total_orders = df_metrics["orders"].iloc[0] or 0
    
    st.columns(2)[0].metric("Live Gross Store Revenue", f"₱{gross_rev:,.2f}")
    st.columns(2)[1].metric("Total Tickets Processed", f"{total_orders} transactions")
    
    st.write("### Channel Sales Workload Breakdown")
    df_channels = run_query("""
        SELECT strftime('%H', o.created_at) || ':00' AS Hour, o.order_channel AS Channel, SUM(oi.quantity) AS "Cups Sold"
        FROM orders o JOIN order_items oi ON o.order_id = oi.order_id GROUP BY Hour, Channel;
    """)
    if not df_channels.empty:
        st.plotly_chart(px.bar(df_channels, x="Hour", y="Cups Sold", color="Channel", barmode="group"), use_container_width=True)

with tab_custom:
    st.subheader("Customer Modification Logs")
    cust_col1, cust_col2 = st.columns(2)
    with cust_col1:
        df_temp = run_query("SELECT temperature AS Temp, SUM(quantity) AS Total FROM order_items GROUP BY Temp;")
        if not df_temp.empty:
            st.plotly_chart(px.pie(df_temp, values="Total", names="Temp", hole=0.3, color_discrete_sequence=["#FF4B4B", "#1C83E1"]), use_container_width=True)
    with cust_col2:
        df_sugar = run_query("SELECT sugar_level AS Sugar, SUM(quantity) AS Total FROM order_items GROUP BY Sugar;")
        if not df_sugar.empty:
            st.plotly_chart(px.bar(df_sugar, x="Sugar", y="Total", text_auto=True, color_discrete_sequence=["#006241"]), use_container_width=True)