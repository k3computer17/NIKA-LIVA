import streamlit as st
import pandas as pd
import hashlib
from datetime import datetime
import streamlit.components.v1 as components
from sqlalchemy import create_engine, text

# =========================================================
# 1. PAGE CONFIG & BRANDING
# =========================================================
st.set_page_config(page_title="NIKA Multi-Service & Grocery Portal", page_icon="🛍️", layout="wide")

MY_CONTACT = "919000000000" # आपका व्हाट्सएप नंबर

# =========================================================
# 2. SUPABASE POSTGRESQL DATABASE CONNECTION
# =========================================================
# Streamlit secrets से Postgres URL पढ़ना
try:
    DB_URL = st.secrets["postgres"]["url"]
    engine = create_engine(DB_URL, pool_pre_ping=True)
except Exception as e:
    st.error("⚠️ Database connection error! Please set Secrets correctly in Streamlit Settings.")
    st.stop()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verify_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# =========================================================
# 3. INITIALIZE CLOUD DATABASE TABLES
# =========================================================
def init_db():
    with engine.begin() as conn:
        # Users Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password TEXT NOT NULL,
                plain_pass TEXT,
                role VARCHAR(20) NOT NULL,
                client_id INT,
                is_approved INT DEFAULT 1
            );
        '''))
        
        # Clients / Customers Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS clients (
                id SERIAL PRIMARY KEY,
                unique_client_id VARCHAR(50) UNIQUE,
                name VARCHAR(100),
                father_name VARCHAR(100),
                mobile VARCHAR(15),
                address TEXT,
                created_date VARCHAR(20),
                latitude VARCHAR(50),
                longitude VARCHAR(50)
            );
        '''))

        # Categories Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                category_name VARCHAR(100) UNIQUE NOT NULL
            );
        '''))

        # Subcategories Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS subcategories (
                id SERIAL PRIMARY KEY,
                category_name VARCHAR(100) NOT NULL,
                sub_category_name VARCHAR(100) NOT NULL
            );
        '''))

        # Items / Services Table
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS services (
                id SERIAL PRIMARY KEY,
                category VARCHAR(100),
                sub_category VARCHAR(100) DEFAULT 'General',
                service_name VARCHAR(150),
                unit VARCHAR(20) DEFAULT 'Kg',
                price_rate NUMERIC(10,2),
                is_active INT DEFAULT 1
            );
        '''))

        # Default Admin Account
        res = conn.execute(text("SELECT id FROM users WHERE username = 'admin';")).fetchone()
        if not res:
            # Password: admin123
            conn.execute(text("""
                INSERT INTO users (username, password, plain_pass, role, is_approved) 
                VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin123', 'Admin', 1);
            """))

init_db()

# =========================================================
# 4. HELPER FUNCTIONS
# =========================================================
def generate_auto_client_id():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT COUNT(*) FROM clients")).scalar()
        return f"NK-CUST-{1001 + res}"

def create_whatsapp_link(mobile, text_msg):
    import urllib.parse
    return f"https://wa.me/{mobile}?text={urllib.parse.quote(text_msg)}"

# =========================================================
# 5. AUTHENTICATION (LOGIN & REGISTRATION)
# =========================================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

st.title("🛍️ NIKA Multi-Service & Grocery Portal")

if not st.session_state['logged_in']:
    login_tab, reg_tab = st.tabs(["🔐 Login", "📝 New Registration"])

    # ---------------- LOGIN ----------------
    with login_tab:
        st.subheader("कस्टमर / एडमिन लॉगिन")
        username = st.text_input("User ID")
        password = st.text_input("Password", type="password")
        if st.button("🚀 Login"):
            with engine.connect() as conn:
                query = text("SELECT * FROM users WHERE username = :u")
                user = conn.execute(query, {"u": username}).fetchone()
                
                if user and verify_hashes(password, user.password):
                    if user.is_approved == 1:
                        st.session_state['logged_in'] = True
                        st.session_state['user_info'] = user
                        st.success("✅ लॉगिन सफल हुआ!")
                        st.rerun()
                    else:
                        st.warning("⚠️ आपका खाता अभी स्वीकृत (Approved) नहीं हुआ है। कृपया एडमिन से संपर्क करें।")
                else:
                    st.error("❌ गलत Username या Password!")

    # ---------------- NEW REGISTRATION ----------------
    with reg_tab:
        st.subheader("📝 नया कस्टमर रजिस्ट्रेशन (Live GPS)")
        auto_id = generate_auto_client_id()
        
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("👤 पूरा नाम (Full Name) *")
            c_father = st.text_input("👨‍👦 पिता/पति का नाम")
            c_mobile = st.text_input("📱 मोबाइल नंबर *")
        with col2:
            c_unique = st.text_input("🆔 Client ID (Auto Generated)", value=auto_id, disabled=True)
            c_userid = st.text_input("🧑‍💻 User ID बनाएं *")
            c_pass = st.text_input("🔑 Password बनाएं *", type="password")

        st.markdown("---")
        st.subheader("📍 लाइव जीपीएस लोकेशन (GPS Fetcher)")

        gps_html_code = """
        <div style="font-family: sans-serif; background: #fff3e0; padding: 15px; border-radius: 8px; border: 1px solid #ffccbc;">
            <p style="margin:0 0 10px 0; font-weight: bold; color: #d84315;">📡 ऑटोमेटिक लाइव लोकेशन डिटेक्टर:</p>
            <button onclick="getLiveLocation()" style="background: #f4511e; color: white; border: none; padding: 8px 15px; border-radius: 5px; cursor: pointer; font-weight: bold;">
                📍 GPS से लोकेशन प्राप्त करें
            </button>
            <p id="status" style="margin-top:8px; font-size:13px; color:#555;">बटन दबाएं...</p>
            
            <div style="margin-top: 10px;">
                <label style="font-size: 12px; font-weight: bold;">ऑटो डिटेक्टेड एड्रेस:</label><br>
                <textarea id="fetched_address" rows="2" style="width: 100%; border-radius: 5px; border: 1px solid #ccc; padding: 5px;" readonly></textarea>
            </div>
            <div style="display: flex; gap: 10px; margin-top: 5px;">
                <div><small>Latitude:</small> <input type="text" id="lat" style="width: 100%;" readonly></div>
                <div><small>Longitude:</small> <input type="text" id="lng" style="width: 100%;" readonly></div>
            </div>
        </div>

        <script>
        function getLiveLocation() {
            var status = document.getElementById('status');
            if (navigator.geolocation) {
                status.innerText = "लोकेशन फेच हो रही है...";
                navigator.geolocation.getCurrentPosition(showPosition, showError, {enableHighAccuracy: true});
            } else {
                status.innerText = "जीपीएस सपोर्ट उपलब्ध नहीं है।";
            }
        }
        function showPosition(position) {
            var lat = position.coords.latitude;
            var lng = position.coords.longitude;
            document.getElementById('lat').value = lat;
            document.getElementById('lng').value = lng;
            
            fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`)
                .then(response => response.json())
                .then(data => {
                    if (data && data.display_name) {
                        document.getElementById('fetched_address').value = data.display_name;
                        status.innerText = "✅ लोकेशन सफलतापूर्वक मिली!";
                    } else {
                        document.getElementById('fetched_address').value = "Lat: " + lat + ", Lng: " + lng;
                        status.innerText = "Coordinates मिल गए।";
                    }
                }).catch(err => {
                    document.getElementById('fetched_address').value = "Lat: " + lat + ", Lng: " + lng;
                });
        }
        function showError(error) {
            document.getElementById('status').innerText = "⚠️ लोकेशन एरर: " + error.message;
        }
        window.onload = getLiveLocation;
        </script>
        """
        components.html(gps_html_code, height=250)

        c_address = st.text_area("🏠 डिलीवरी का पूरा पता (Manual/Confirm) *", placeholder="ऊपर से देखकर या अपना सही पता यहाँ लिखें...")
        lat_val = st.text_input("Latitude", value="0.0")
        lon_val = st.text_input("Longitude", value="0.0")

        if st.button("✨ Register Account"):
            if not all([c_name, c_userid, c_pass, c_mobile, c_address]):
                st.error("कृपया सभी आवश्यक (*) जानकारी भरें!")
            else:
                try:
                    with engine.begin() as conn:
                        today = datetime.now().strftime("%Y-%m-%d")
                        
                        # 1. Insert Client
                        res = conn.execute(text("""
                            INSERT INTO clients (unique_client_id, name, father_name, mobile, address, created_date, latitude, longitude) 
                            VALUES (:u_id, :name, :f_name, :mob, :addr, :dt, :lat, :lon)
                            RETURNING id;
                        """), {
                            "u_id": auto_id, "name": c_name, "f_name": c_father, "mob": c_mobile, 
                            "addr": c_address, "dt": today, "lat": lat_val, "lon": lon_val
                        })
                        new_client_id = res.fetchone()[0]

                        # 2. Insert User
                        conn.execute(text("""
                            INSERT INTO users (username, password, plain_pass, role, client_id, is_approved)
                            VALUES (:u, :p, :pp, 'Customer', :c_id, 0);
                        """), {
                            "u": c_userid, "p": make_hashes(c_pass), "pp": c_pass, "c_id": new_client_id
                        })
                        
                        st.success(f"✅ रजिस्ट्रेशन सफल हुआ! आपकी यूनिक ID है: **{auto_id}**")
                        wa_msg = f"नमस्ते एडमिन, नया यूजर रजिस्टर हुआ है:\nनाम: {c_name}\nयूजर ID: {c_userid}\nClient ID: {auto_id}"
                        st.link_button("💬 Send Approval Request to Admin", create_whatsapp_link(MY_CONTACT, wa_msg))

                except Exception as ex:
                    st.error(f"⚠️ एरर: यह Username या Client ID पहले से मौजूद हो सकता है। ({ex})")

else:
    # Logout Header
    st.sidebar.write(f"Logged in as: **{st.session_state['user_info'].username}** ({st.session_state['user_info'].role})")
    if st.sidebar.button("🚪 Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_info'] = None
        st.rerun()

    user_role = st.session_state['user_info'].role

    # =========================================================
    # 6. MASTER ADMIN DASHBOARD (PERMANENT STORAGE)
    # =========================================================
    if user_role == "Admin":
        st.sidebar.title("👑 Admin Panel")
        admin_choice = st.sidebar.radio("Navigation", ["🏬 Category & Item Master", "👥 Customers List", "⚙️ Approval Requests"])

        # ------------ 1. CATEGORY & ITEM MASTER ------------
        if admin_choice == "🏬 Category & Item Master":
            st.title("🏬 श्रेणी, उप-श्रेणी एवं सामान प्रबंधन")
            
            t1, t2, t3 = st.tabs(["📁 1. Main Category", "📑 2. Sub-Category", "📦 3. Items / Products"])

            # ---- MAIN CATEGORY ----
            with t1:
                st.subheader("नई श्रेणी जोड़ें")
                with st.form("add_cat_form", clear_on_submit=True):
                    cat_name = st.text_input("Category Name")
                    submit_cat = st.form_submit_button("➕ Safe & Permanent Save")
                    if submit_cat and cat_name:
                        with engine.begin() as conn:
                            conn.execute(text("INSERT INTO categories (category_name) VALUES (:c) ON CONFLICT DO NOTHING;"), {"c": cat_name.strip()})
                            st.success(f"✅ Category '{cat_name}' सुरक्षित हो गई!")

                st.markdown("---")
                st.subheader("📋 वर्तमान श्रेणियाँ (Current Categories)")
                with engine.connect() as conn:
                    df_cats = pd.read_sql_query(text("SELECT * FROM categories ORDER BY id DESC"), conn)
                    st.dataframe(df_cats, use_container_width=True)

            # ---- SUB CATEGORY ----
            with t2:
                st.subheader("नई उप-श्रेणी (Sub-Category) जोड़ें")
                with engine.connect() as conn:
                    cat_list = [row[0] for row in conn.execute(text("SELECT category_name FROM categories")).fetchall()]

                if cat_list:
                    with st.form("add_subcat_form", clear_on_submit=True):
                        sel_cat = st.selectbox("मुख्य श्रेणी चुनें", cat_list)
                        subcat_name = st.text_input("Sub-Category Name")
                        sub_btn = st.form_submit_button("➕ Save Sub-Category")

                        if sub_btn and subcat_name:
                            with engine.begin() as conn:
                                conn.execute(text("INSERT INTO subcategories (category_name, sub_category_name) VALUES (:c, :s);"), 
                                             {"c": sel_cat, "s": subcat_name.strip()})
                                st.success(f"✅ Sub-Category '{subcat_name}' सेव हो गई!")
                else:
                    st.warning("कृपया पहले मेन श्रेणी जोड़ें!")

                st.markdown("---")
                with engine.connect() as conn:
                    df_subcats = pd.read_sql_query(text("SELECT * FROM subcategories ORDER BY id DESC"), conn)
                    st.dataframe(df_subcats, use_container_width=True)

            # ---- ITEMS / PRODUCTS ----
            with t3:
                st.subheader("नया आइटम/सामान जोड़ें")
                with engine.connect() as conn:
                    cats = [row[0] for row in conn.execute(text("SELECT category_name FROM categories")).fetchall()]

                if cats:
                    sel_item_cat = st.selectbox("Category", cats, key="item_cat")
                    
                    # Fetch related subcategories
                    with engine.connect() as conn:
                        subcats = [row[0] for row in conn.execute(text("SELECT sub_category_name FROM subcategories WHERE category_name = :c"), {"c": sel_item_cat}).fetchall()]
                    
                    if not subcats:
                        subcats = ["General"]

                    with st.form("add_item_form", clear_on_submit=True):
                        sel_item_subcat = st.selectbox("Sub-Category", subcats)
                        i_name = st.text_input("Item Name *")
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            i_unit = st.selectbox("Unit", ["Kg", "Gram", "Liter", "Piece", "Packet", "Box"])
                        with col_p2:
                            i_price = st.number_input("Rate / Price (₹)", min_value=0.0, step=1.0)
                        
                        item_btn = st.form_submit_button("📦 Save Item")

                        if item_btn and i_name:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    INSERT INTO services (category, sub_category, service_name, unit, price_rate)
                                    VALUES (:c, :s, :n, :u, :p);
                                """), {"c": sel_item_cat, "s": sel_item_subcat, "n": i_name, "u": i_unit, "p": i_price})
                                st.success(f"✅ Item '{i_name}' हमेशा के लिए डेटाबेस में सेव हो गया!")
                else:
                    st.info("पहले Category जोड़ें।")

                st.markdown("---")
                st.subheader("📦 संपूर्ण सामान सूची (Items Database)")
                with engine.connect() as conn:
                    df_items = pd.read_sql_query(text("SELECT * FROM services ORDER BY id DESC"), conn)
                    st.dataframe(df_items, use_container_width=True)

        # ------------ 2. CUSTOMERS LIST ------------
        elif admin_choice == "👥 Customers List":
            st.title("👥 ग्राहक सूची (Registered Customers)")
            with engine.connect() as conn:
                df_cust = pd.read_sql_query(text("""
                    SELECT c.id, c.unique_client_id, c.name, c.mobile, c.address, u.username, u.plain_pass as password, u.is_approved 
                    FROM clients c
                    LEFT JOIN users u ON c.id = u.client_id;
                """), conn)
                st.dataframe(df_cust, use_container_width=True)

        # ------------ 3. APPROVAL REQUESTS ------------
        elif admin_choice == "⚙️ Approval Requests":
            st.title("⚙️ Pending Customer Approvals")
            with engine.connect() as conn:
                pending_users = pd.read_sql_query(text("SELECT id, username, role, is_approved FROM users WHERE is_approved = 0"), conn)
                
            if not pending_users.empty:
                for idx, row in pending_users.iterrows():
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"🧑‍💻 User: **{row['username']}** | Role: {row['role']}")
                    with col_b:
                        if st.button(f"Approve {row['username']}", key=f"app_{row['id']}"):
                            with engine.begin() as conn:
                                conn.execute(text("UPDATE users SET is_approved = 1 WHERE id = :id"), {"id": row['id']})
                                st.success("Approved!")
                                st.rerun()
            else:
                st.info("कोई पेंडिंग रिक्वेस्ट नहीं है।")

    # =========================================================
    # 7. CUSTOMER DASHBOARD (SHOPPING & PORTAL)
    # =========================================================
    else:
        st.title("🛒 Grocery & Portal Shop")
        st.write("आपका स्वागत है!")
        
        with engine.connect() as conn:
            categories = [r[0] for r in conn.execute(text("SELECT category_name FROM categories")).fetchall()]
        
        if categories:
            selected_cat = st.selectbox("📂 Category चुनें:", categories)
            
            with engine.connect() as conn:
                items_df = pd.read_sql_query(text("SELECT service_name, unit, price_rate FROM services WHERE category = :c AND is_active = 1"), conn, params={"c": selected_cat})
            
            if not items_df.empty:
                st.table(items_df)
            else:
                st.info("इस श्रेणी में अभी कोई आइटम उपलब्ध नहीं हैं।")
        else:
            st.info("दुकान में अभी कोई श्रेणी नहीं जोड़ी गई है।")
