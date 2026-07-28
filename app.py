import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import urllib.parse
import hashlib

# ---------------------------------------------------------
# 1. Page Configuration & Custom Styling
# ---------------------------------------------------------
st.set_page_config(page_title="NIKA - Multi-Service & Grocery Portal", layout="wide")

st.markdown("""
    <style>
    .main { 
        background: linear-gradient(135deg, #fff8f5 0%, #fff3ed 50%, #fce4ec 100%); 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    }
    h1, h2, h3 { color: #d84315 !important; font-weight: 700; }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #ffe0b2; }
    .stButton>button {
        background: linear-gradient(90deg, #f4511e 0%, #d32f2f 100%);
        color: white; border-radius: 8px; border: none; padding: 10px 24px; font-weight: bold;
        box-shadow: 0 4px 10px rgba(244, 81, 30, 0.25); transition: 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #e64a19 0%, #c62828 100%);
        box-shadow: 0 6px 14px rgba(244, 81, 30, 0.35);
    }
    .stLinkButton>a {
        background: linear-gradient(90deg, #f4511e 0%, #d32f2f 100%) !important;
        color: white !important; border-radius: 8px !important; font-weight: bold !important;
    }
    input, textarea, select { border-color: #ffccbc !important; background-color: #ffffff !important; border-radius: 6px !important; }
    .stAlert { background-color: #fff3e0 !important; border: 1px solid #ffccbc !important; color: #bf360c !important; border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #ffffff; border-radius: 6px 6px 0px 0px; padding: 10px 16px; color: #4e342e; border: 1px solid #ffe0b2; }
    .stTabs [aria-selected="true"] { background-color: #fbe9e7 !important; color: #d84315 !important; border-bottom: 2px solid #d84315 !important; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. Security & Password Utilities
# ---------------------------------------------------------
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# ---------------------------------------------------------
# 3. Database Initialization
# ---------------------------------------------------------
DB_FILE = 'nika_clients_v8.db'

def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # User Table (Note: plain_pass stores password for Admin view)
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE,
                        password TEXT,
                        plain_pass TEXT,
                        role TEXT,
                        client_id INTEGER,
                        is_approved INTEGER DEFAULT 1)''')
        
        # Client Table
        c.execute('''CREATE TABLE IF NOT EXISTS clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        unique_client_id TEXT,
                        name TEXT,
                        father_name TEXT,
                        pan_number TEXT,
                        mobile TEXT,
                        address TEXT,
                        itr_username TEXT,
                        itr_password TEXT,
                        created_date TEXT,
                        latitude TEXT,
                        longitude TEXT)''')

        # Categories
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_name TEXT UNIQUE)''')

        # Sub-Categories
        c.execute('''CREATE TABLE IF NOT EXISTS subcategories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        main_category_id INTEGER,
                        sub_category_name TEXT,
                        FOREIGN KEY(main_category_id) REFERENCES categories(id) ON DELETE CASCADE)''')

        # Items Table
        c.execute('''CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT,
                        sub_category TEXT DEFAULT 'सामान्य',
                        service_name TEXT,
                        unit TEXT DEFAULT 'Kg',
                        price_rate REAL,
                        description TEXT,
                        is_active INTEGER DEFAULT 1)''')

        # Persistent Cart Table
        c.execute('''CREATE TABLE IF NOT EXISTS cart_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER,
                        category TEXT,
                        sub_category TEXT,
                        item_name TEXT,
                        unit TEXT,
                        qty REAL,
                        rate REAL,
                        total REAL,
                        FOREIGN KEY(client_id) REFERENCES clients(id))''')

        # Orders Table
        c.execute('''CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER,
                        items_summary TEXT,
                        total_price REAL,
                        order_date TEXT,
                        delivery_address TEXT,
                        order_status TEXT DEFAULT 'Pending',
                        remarks TEXT,
                        FOREIGN KEY(client_id) REFERENCES clients(id))''')

        # Admin Settings
        c.execute('''CREATE TABLE IF NOT EXISTS admin_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        setting_key TEXT UNIQUE,
                        setting_value TEXT)''')

        # Seed Default Admin User
        c.execute("SELECT id FROM users WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("INSERT INTO users (username, password, plain_pass, role, is_approved) VALUES (?, ?, ?, ?, ?)",
                      ('admin', make_hashes('admin123'), 'admin123', 'Admin', 1))
        conn.commit()

init_db()

# ---------------------------------------------------------
# 4. Helper Functions
# ---------------------------------------------------------
MY_CONTACT = "8358013017"

def generate_auto_client_id():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT MAX(id) FROM clients")
        res = c.fetchone()
        last_id = res[0] if res and res[0] is not None else 0
        return f"NIKA-{last_id + 1001}"

def create_whatsapp_link(client_mobile, message):
    if not client_mobile:
        return None
    clean_mobile = "".join(filter(str.isdigit, str(client_mobile)))
    if len(clean_mobile) == 10:
        clean_mobile = "91" + clean_mobile
    encoded_msg = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?phone={clean_mobile}&text={encoded_msg}"

def get_setting(key):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT setting_value FROM admin_settings WHERE setting_key = ?", (key,))
        res = c.fetchone()
        return res[0] if res else ""

def get_main_categories():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT category_name FROM categories ORDER BY category_name ASC")
        return [r[0] for r in c.fetchall()]

def get_subcategories_by_main(main_cat_name):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            SELECT sc.sub_category_name 
            FROM subcategories sc
            JOIN categories c ON sc.main_category_id = c.id
            WHERE c.category_name = ?
            ORDER BY sc.sub_category_name ASC
        ''', (main_cat_name,))
        res = [r[0] for r in c.fetchall()]
        return res if res else ["सामान्य"]

# Cart Operations
def add_to_db_cart(client_id, category, sub_category, item_name, unit, qty, rate, total):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''
            INSERT INTO cart_items (client_id, category, sub_category, item_name, unit, qty, rate, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (client_id, category, sub_category, item_name, unit, qty, rate, total))
        conn.commit()

def get_db_cart(client_id):
    with get_db_connection() as conn:
        return pd.read_sql_query('''
            SELECT id, category, sub_category, item_name, unit, qty, rate, total 
            FROM cart_items WHERE client_id = ?
        ''', conn, params=(client_id,))

def clear_db_cart(client_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM cart_items WHERE client_id = ?", (client_id,))
        conn.commit()

def delete_cart_item(cart_id):
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM cart_items WHERE id = ?", (cart_id,))
        conn.commit()

# Session State Setup
for key in ["logged_in", "username", "user_role", "client_id"]:
    if key not in st.session_state:
        st.session_state[key] = False if key == "logged_in" else None

# ---------------------------------------------------------
# 5. Header & Branding Setup
# ---------------------------------------------------------
app_logo = get_setting("logo_url")
app_banner = get_setting("banner_url")
global_tax_info = get_setting("tax_info")

if app_banner:
    st.image(app_banner, use_container_width=True)

if app_logo:
    col_l1, col_l2 = st.columns([1, 6])
    with col_l1:
        st.image(app_logo, width=90)
    with col_l2:
        st.title("🛒 NIKA - Kirana & Superstore Portal")
else:
    st.title("🛒 NIKA - Kirana & Superstore Portal")

if global_tax_info:
    st.markdown(f"""
        <div style="background-color: #fbe9e7; padding: 12px; border-radius: 8px; border-left: 5px solid #d84315; margin-bottom: 15px;">
            <strong style="color: #d84315;">📢 Store Notice:</strong> {global_tax_info}
        </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. Login & Registration
# ---------------------------------------------------------
if not st.session_state.logged_in:
    login_choice = st.sidebar.selectbox("📌 Navigation", ["🔐 Admin Login", "👤 Customer Login", "📝 New Registration", "🔄 Reset Password"])

    if login_choice == "🔐 Admin Login":
        st.subheader("👨‍💼 Master Admin Login")
        user = st.text_input("👤 Admin Username")
        passwd = st.text_input("🔑 Admin Password", type="password")
        if st.button("🚀 Master Login"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE username = ? AND role = 'Admin'", (user,))
                res = c.fetchone()
                if res and check_hashes(passwd, res[0]):
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.user_role = "Admin"
                    st.success("Welcome Admin!")
                    st.rerun()
                else:
                    st.error("Invalid Admin Credentials")

    elif login_choice == "👤 Customer Login":
        st.subheader("👤 Customer Portal Login")
        user = st.text_input("🆔 User ID / Username")
        passwd = st.text_input("🔑 Password", type="password")
        if st.button("🚀 Customer Login"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT password, client_id, is_approved FROM users WHERE username = ? AND role = 'Customer'", (user,))
                res = c.fetchone()
                if res:
                    if res[2] == 0:
                        st.warning("⚠️ आपका अकाउंट अभी अप्रूव नहीं हुआ है।")
                        w_msg = f"नमस्ते एडमिन, मैंने रजिस्ट्रेशन किया है। कृपया मेरा यूजर आईडी ({user}) अप्रूव कर दें।"
                        st.link_button("💬 Send Approval Request on WhatsApp", create_whatsapp_link(MY_CONTACT, w_msg))
                    elif check_hashes(passwd, res[0]):
                        st.session_state.logged_in = True
                        st.session_state.username = user
                        st.session_state.user_role = "Customer"
                        st.session_state.client_id = res[1]
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Password")
                else:
                    st.error("User ID not found!")

    elif login_choice == "📝 New Registration":
        st.subheader("📝 Customer Registration")
        auto_id = generate_auto_client_id()
        
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("👤 Full Name *")
            c_father = st.text_input("👨‍👦 Father's Name")
            c_mobile = st.text_input("📱 Mobile Number *")
            c_address = st.text_area("🏠 Delivery / Home Address *")
        with col2:
            c_unique = st.text_input("🆔 Unique Client ID (Auto) *", value=auto_id)
            c_userid = st.text_input("🧑‍💻 Create User ID *")
            c_pass = st.text_input("🔑 Create Password *", type="password")

        st.markdown("---")
        st.subheader("📍 लोकेशन विवरण")
        lat_input = st.text_input("🌐 Latitude", value="23.2599")
        lon_input = st.text_input("🌐 Longitude", value="77.4126")

        if st.button("✨ Register & Submit"):
            if not all([c_name, c_userid, c_pass, c_mobile, c_address, c_unique]):
                st.error("कृपया सभी आवश्यक (*) फ़ील्ड भरें!")
            else:
                try:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        today = datetime.now().strftime("%Y-%m-%d")
                        c.execute("""
                            INSERT INTO clients (unique_client_id, name, father_name, mobile, address, created_date, latitude, longitude) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (c_unique.upper(), c_name, c_father, c_mobile, c_address, today, lat_input, lon_input))
                        
                        new_client_id = c.lastrowid
                        c.execute("INSERT INTO users (username, password, plain_pass, role, client_id, is_approved) VALUES (?, ?, ?, 'Customer', ?, 0)",
                                  (c_userid, make_hashes(c_pass), c_pass, new_client_id))
                        conn.commit()
                        st.success(f"✅ रजिस्ट्रेशन सफल हुआ! आपकी यूनिक आईडी: **{c_unique.upper()}**")
                        
                        wa_text = f"नमस्ते एडमिन, नया रजिस्ट्रेशन हुआ है।\nनाम: {c_name}\nयूजर आईडी: {c_userid}\nयूनिक आईडी: {c_unique.upper()}"
                        st.link_button("💬 Send Approval Request", create_whatsapp_link(MY_CONTACT, wa_text))
                except sqlite3.IntegrityError:
                    st.error("⚠️ यह Username पहले से मौजूद है!")

    elif login_choice == "🔄 Reset Password":
        st.subheader("🔄 Reset Password")
        f_user = st.text_input("🆔 User ID")
        f_mobile = st.text_input("📱 Registered Mobile Number")
        f_unique = st.text_input("🏷️ Unique Client ID")
        new_pass = st.text_input("🔑 New Password", type="password")

        if st.button("🔄 Reset Password"):
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('''
                    SELECT u.id, c.mobile, c.unique_client_id 
                    FROM users u JOIN clients c ON u.client_id = c.id 
                    WHERE u.username = ? AND u.role = 'Customer'
                ''', (f_user,))
                r = c.fetchone()
                if r and r[1] == f_mobile and str(r[2]).upper() == f_unique.upper():
                    c.execute("UPDATE users SET password = ?, plain_pass = ? WHERE username = ?", (make_hashes(new_pass), new_pass, f_user))
                    conn.commit()
                    st.success("✅ पासवर्ड सफलतापूर्वक बदल दिया गया!")
                else:
                    st.error("❌ विवरण मेल नहीं खा रहे हैं।")

# ---------------------------------------------------------
# 7. Dashboard Sections
# ---------------------------------------------------------
else:
    st.sidebar.write(f"👤 **{st.session_state.username}** ({st.session_state.user_role})")
    
    if st.sidebar.button("🔴 Logout"):
        st.session_state.clear()
        st.rerun()

    # ==================== ADMIN DASHBOARD ====================
    if st.session_state.user_role == "Admin":
        st.title("👨‍💼 Master Admin Dashboard")
        choice = st.sidebar.radio("📌 Admin Menu", [
            "📂 Categories & Items Management", 
            "📦 Customer Orders", 
            "👑 Manage Customers (Full Access)", 
            "👥 Approve Users", 
            "🖼️ Branding & Settings"
        ])

        if choice == "📂 Categories & Items Management":
            st.subheader("🏬 श्रेणी, उप-श्रेणी (Sub-Category) एवं सामान (Items) प्रबंधित करें")
            
            tab_main, tab_sub, tab_item, tab_excel, tab_view = st.tabs([
                "1️⃣ Main Category जोड़ें", 
                "2️⃣ Sub-Category जोड़ें", 
                "3️⃣ Single Item जोड़ें", 
                "4️⃣ Excel/CSV से Import करें 📊",
                "📋 सभी Items की लिस्ट"
            ])

            with tab_main:
                st.write("### 1️⃣ Main Category जोड़ें")
                new_cat = st.text_input("नई Main Category का नाम लिखें:")
                if st.button("➕ Main Category सहेजें"):
                    if new_cat.strip():
                        try:
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("INSERT INTO categories (category_name) VALUES (?)", (new_cat.strip(),))
                                conn.commit()
                                st.success(f"✅ Main Category '{new_cat.strip()}' सफलतापूर्वक जोड़ी गई!")
                                st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("⚠️ यह Main Category पहले से मौजूद है!")

            with tab_sub:
                st.write("### 2️⃣ Sub-Category (उप-श्रेणी) जोड़ें")
                main_cats = get_main_categories()
                if not main_cats:
                    st.warning("पहले कम से कम एक Main Category बनाएं!")
                else:
                    sel_main = st.selectbox("किस Main Category के अंदर Sub-Category जोड़नी है?", main_cats, key="sub_main_sel")
                    new_sub_name = st.text_input("Sub-Category का नाम लिखें:")
                    
                    if st.button("➕ Sub-Category सहेजें"):
                        if new_sub_name.strip():
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("SELECT id FROM categories WHERE category_name = ?", (sel_main,))
                                m_id = c.fetchone()[0]
                                c.execute("INSERT INTO subcategories (main_category_id, sub_category_name) VALUES (?, ?)", (m_id, new_sub_name.strip()))
                                conn.commit()
                                st.success(f"✅ Sub-Category '{new_sub_name.strip()}' को '{sel_main}' में जोड़ दिया गया!")
                                st.rerun()

            with tab_item:
                st.write("### 3️⃣ सिंगल सामान (Item) जोड़ें")
                main_cats = get_main_categories()
                if not main_cats:
                    st.warning("पहले Main Category और Sub-Category बनाएं!")
                else:
                    col1, col2 = st.columns(2)
                    with col1:
                        i_main = st.selectbox("Main Category चुनें:", main_cats, key="item_main_sel")
                    
                    sub_list = get_subcategories_by_main(i_main)
                    with col2:
                        i_sub = st.selectbox("Sub-Category चुनें:", sub_list, key="item_sub_sel")

                    i_name = st.text_input("सामान का नाम (Item Name):")
                    col_u, col_p = st.columns(2)
                    with col_u:
                        i_unit = st.selectbox("इकाई (Unit):", ["Kg", "Gram", "Ltr", "Packet", "Pc / Piece", "Box", "Meter"])
                    with col_p:
                        i_price = st.number_input("कीमत / Rate (₹):", min_value=0.0, step=5.0)

                    if st.button("💾 Item सुरक्षित करें"):
                        if i_name.strip():
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("INSERT INTO services (category, sub_category, service_name, unit, price_rate) VALUES (?, ?, ?, ?, ?)",
                                          (i_main, i_sub, i_name.strip(), i_unit, i_price))
                                conn.commit()
                                st.success(f"✅ '{i_name.strip()}' सफलतापूर्वक जोड़ा गया!")
                                st.rerun()

            with tab_excel:
                st.write("### 📊 Excel या CSV फ़ाइल से एक साथ सामान व रेट अपलोड करें")
                sample_df = pd.DataFrame([
                    {"category": "किराना", "sub_category": "दाल", "service_name": "अरहर दाल (Tur Dal)", "unit": "Kg", "price_rate": 160.0},
                    {"category": "किराना", "sub_category": "तेल", "service_name": "सरसों तेल (Mustard Oil)", "unit": "Ltr", "price_rate": 145.0}
                ])
                csv_sample = sample_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Sample Excel/CSV Template डाउनलोड करें", csv_sample, "nika_items_template.csv", "text/csv")
                
                st.markdown("---")
                uploaded_file = st.file_uploader("📂 अपनी Excel (.xlsx) या CSV (.csv) फ़ाइल चुनें", type=["csv", "xlsx"])

                if uploaded_file is not None:
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df_upload = pd.read_csv(uploaded_file)
                        else:
                            df_upload = pd.read_excel(uploaded_file)

                        st.write("👀 Uploaded Data Preview:")
                        st.dataframe(df_upload.head(10), use_container_width=True)

                        req_cols = {'category', 'sub_category', 'service_name', 'unit', 'price_rate'}
                        if not req_cols.issubset(set(df_upload.columns)):
                            st.error(f"❌ फ़ाइल में आवश्यक Columns नहीं हैं!")
                        else:
                            if st.button("🚀 डेटाबेस में Import करें"):
                                success_count = 0
                                with get_db_connection() as conn:
                                    c = conn.cursor()
                                    for idx, row in df_upload.iterrows():
                                        cat = str(row['category']).strip()
                                        sub_cat = str(row['sub_category']).strip()
                                        s_name = str(row['service_name']).strip()
                                        unit = str(row['unit']).strip()
                                        rate = float(row['price_rate'])

                                        c.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (cat,))
                                        c.execute("SELECT id FROM categories WHERE category_name = ?", (cat,))
                                        m_id = c.fetchone()[0]

                                        c.execute("SELECT id FROM subcategories WHERE main_category_id = ? AND sub_category_name = ?", (m_id, sub_cat))
                                        if not c.fetchone():
                                            c.execute("INSERT INTO subcategories (main_category_id, sub_category_name) VALUES (?, ?)", (m_id, sub_cat))

                                        c.execute("INSERT INTO services (category, sub_category, service_name, unit, price_rate) VALUES (?, ?, ?, ?, ?)",
                                                  (cat, sub_cat, s_name, unit, rate))
                                        success_count += 1
                                    
                                    conn.commit()
                                st.success(f"🎉 कुल **{success_count}** सामान सफलतापूर्वक अपलोड हो गए!")
                                st.rerun()

                    except Exception as e:
                        st.error(f"⚠️ त्रुटि: {str(e)}")

            with tab_view:
                st.write("### 📋 स्टोर के सभी सामान की सूची")
                filter_main = st.selectbox("Main Category के अनुसार देखें:", ["सभी"] + get_main_categories())
                with get_db_connection() as conn:
                    if filter_main == "सभी":
                        df_items = pd.read_sql_query("SELECT id as ID, category as 'Main Category', sub_category as 'Sub Category', service_name as 'Item Name', unit as 'Unit', price_rate as 'Rate (₹)' FROM services WHERE is_active = 1 ORDER BY category, sub_category, service_name", conn)
                    else:
                        df_items = pd.read_sql_query("SELECT id as ID, category as 'Main Category', sub_category as 'Sub Category', service_name as 'Item Name', unit as 'Unit', price_rate as 'Rate (₹)' FROM services WHERE is_active = 1 AND category = ? ORDER BY sub_category, service_name", conn, params=(filter_main,))
                    
                    st.dataframe(df_items, use_container_width=True)

        elif choice == "📦 Customer Orders":
            st.subheader("📦 ग्राहकों के ऑर्डर्स")
            with get_db_connection() as conn:
                df_orders = pd.read_sql_query('''
                    SELECT o.id as 'Order ID', COALESCE(c.unique_client_id, 'N/A') as 'Client ID', COALESCE(c.name, 'N/A') as 'Name',
                           o.items_summary as 'Order Items', o.total_price as 'Total (₹)', o.order_date as 'Date', o.order_status as 'Status'
                    FROM orders o LEFT JOIN clients c ON o.client_id = c.id ORDER BY o.id DESC
                ''', conn)
                if not df_orders.empty:
                    st.dataframe(df_orders, use_container_width=True)
                    ord_id = st.number_input("🆔 Order ID चुनें status अपडेट के लिए:", min_value=1, step=1)
                    new_status = st.selectbox("🔄 New Status:", ["Pending", "Processing", "Out for Delivery", "Completed", "Cancelled"])
                    if st.button("✨ Update Order Status"):
                        c = conn.cursor()
                        c.execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_status, ord_id))
                        conn.commit()
                        st.success("Status Updated!")
                        st.rerun()

        # ==================== FULL ACCESS CUSTOMER MANAGEMENT ====================
        elif choice == "👑 Manage Customers (Full Access)":
            st.subheader("👑 ग्राहकों का पूर्ण एक्सेस (Full Customer Access)")
            st.info("यहाँ आप ग्राहकों के User ID, Password देख सकते हैं और उसमें बदलाव कर सकते हैं।")

            tab_view_cust, tab_edit_cust = st.tabs(["👁️ सभी ग्राहकों की पूरी जानकारी (User ID & Password)", "✏️ ग्राहक विवरण या Password बदलें"])

            # 1. View All Details
            with tab_view_cust:
                with get_db_connection() as conn:
                    df_full_cust = pd.read_sql_query('''
                        SELECT 
                            c.id as 'DB ID',
                            c.unique_client_id as 'Client ID',
                            c.name as 'Customer Name',
                            c.mobile as 'Mobile',
                            u.username as 'User ID',
                            COALESCE(u.plain_pass, '****') as 'Password',
                            c.address as 'Address',
                            c.created_date as 'Registered Date',
                            CASE WHEN u.is_approved = 1 THEN 'Approved' ELSE 'Pending' END as 'Status'
                        FROM clients c
                        JOIN users u ON c.id = u.client_id
                        WHERE u.role = 'Customer'
                        ORDER BY c.id DESC
                    ''', conn)
                    
                    if not df_full_cust.empty:
                        st.dataframe(df_full_cust, use_container_width=True)
                    else:
                        st.warning("कोई Customer नहीं मिला।")

            # 2. Modify Credentials & Information
            with tab_edit_cust:
                st.write("### ✏️ किसी भी ग्राहक का Password या Detail अपडेट करें")
                with get_db_connection() as conn:
                    c = conn.cursor()
                    c.execute('''
                        SELECT c.id, c.name, u.username, c.unique_client_id 
                        FROM clients c JOIN users u ON c.id = u.client_id 
                        WHERE u.role = 'Customer'
                    ''')
                    cust_list = c.fetchall()

                if not cust_list:
                    st.warning("कोई Customer उपलब्ध नहीं है।")
                else:
                    cust_dict = {f"{item[1]} (User ID: {item[2]} | Client ID: {item[3]})": item[0] for item in cust_list}
                    selected_cust_label = st.selectbox("🎯 ग्राहक चुनें जिसे अपडेट करना है:", list(cust_dict.keys()))
                    selected_db_id = cust_dict[selected_cust_label]

                    # Fetch current details
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute('''
                            SELECT c.unique_client_id, c.name, c.mobile, c.address, u.username, u.plain_pass
                            FROM clients c JOIN users u ON c.id = u.client_id
                            WHERE c.id = ?
                        ''', (selected_db_id,))
                        cd = c.fetchone()

                    st.markdown("---")
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        e_uid = st.text_input("🆔 Unique Client ID:", value=cd[0])
                        e_name = st.text_input("👤 Customer Name:", value=cd[1])
                        e_mobile = st.text_input("📱 Mobile Number:", value=cd[2])
                        e_address = st.text_area("🏠 Address:", value=cd[3])

                    with col_e2:
                        e_username = st.text_input("🧑‍💻 User ID (Login Username):", value=cd[4])
                        e_pass = st.text_input("🔑 New Password (नया पासवर्ड सेट करें):", value=cd[5] if cd[5] else "")

                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        if st.button("💾 अपडेट करें (Save Changes)"):
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                # Update Client Table
                                c.execute('''
                                    UPDATE clients 
                                    SET unique_client_id = ?, name = ?, mobile = ?, address = ? 
                                    WHERE id = ?
                                ''', (e_uid, e_name, e_mobile, e_address, selected_db_id))

                                # Update User Table (Credentials)
                                new_hash = make_hashes(e_pass)
                                c.execute('''
                                    UPDATE users 
                                    SET username = ?, password = ?, plain_pass = ? 
                                    WHERE client_id = ?
                                ''', (e_username, new_hash, e_pass, selected_db_id))
                                conn.commit()

                                st.success(f"✅ Customer '{e_name}' की जानकारी और पासवर्ड सफलतापूर्वक अपडेट हो गए!")
                                st.rerun()

                    with col_b2:
                        if st.button("🗑️ Customer डिलीट करें", type="primary"):
                            with get_db_connection() as conn:
                                c = conn.cursor()
                                c.execute("DELETE FROM users WHERE client_id = ?", (selected_db_id,))
                                c.execute("DELETE FROM clients WHERE id = ?", (selected_db_id,))
                                c.execute("DELETE FROM cart_items WHERE client_id = ?", (selected_db_id,))
                                conn.commit()
                                st.success("❌ ग्राहक का पूरा खाता डिलीट कर दिया गया!")
                                st.rerun()

        elif choice == "👥 Approve Users":
            st.subheader("👥 पेंडिंग अप्रूवल")
            with get_db_connection() as conn:
                df_pend = pd.read_sql_query('''
                    SELECT u.id as 'User ID', c.unique_client_id as 'Unique ID', c.name as 'Name', u.username as 'Username', c.mobile as 'Mobile'
                    FROM users u JOIN clients c ON u.client_id = c.id WHERE u.role = 'Customer' AND u.is_approved = 0
                ''', conn)
                if not df_pend.empty:
                    st.dataframe(df_pend, use_container_width=True)
                    app_uid = st.number_input("Approved करने के लिए User ID डालें:", min_value=1, step=1)
                    if st.button("✅ Approve Customer"):
                        c = conn.cursor()
                        c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (app_uid,))
                        conn.commit()
                        st.success("Approved!")
                        st.rerun()
                else:
                    st.info("कोई पेंडिंग रिक्वेस्ट नहीं है।")

        elif choice == "🖼️ Branding & Settings":
            st.subheader("🖼️ ब्रांडिंग व बैनर सेटिंग्स")
            with st.form("b_form"):
                b_url = st.text_input("Banner Image URL:", value=get_setting("banner_url"))
                l_url = st.text_input("Logo Image URL:", value=get_setting("logo_url"))
                t_info = st.text_area("Notice Info:", value=get_setting("tax_info"))
                if st.form_submit_button("💾 Save Settings"):
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        for k, v in [("banner_url", b_url), ("logo_url", l_url), ("tax_info", t_info)]:
                            c.execute("INSERT OR REPLACE INTO admin_settings (setting_key, setting_value) VALUES (?, ?)", (k, v))
                        conn.commit()
                        st.success("सहेजा गया!")
                        st.rerun()

    # ==================== CUSTOMER DASHBOARD ====================
    elif st.session_state.user_role == "Customer":
        st.title("🛍️ Shopping Portal")
        cid = st.session_state.client_id

        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT unique_client_id, name, mobile, address FROM clients WHERE id = ?", (cid,))
            client_info = c.fetchone()
            
        c_uid = client_info[0] if client_info and client_info[0] else "N/A"
        c_name = client_info[1] if client_info and client_info[1] else "Customer"
        c_mob = client_info[2] if client_info and client_info[2] else "N/A"
        c_addr = client_info[3] if client_info and client_info[3] else ""

        st.info(f"👤 **{c_name}** | 🆔 **Client ID:** `{c_uid}`")

        tab_order, tab_cart, tab_my_orders = st.tabs(["🛒 Browse & Add Items", "🛍️ My Cart", "📦 My Orders"])

        with tab_order:
            st.subheader("🛒 3-Step Selection: Main Category ➔ Sub-Category ➔ Item")
            
            main_cats = get_main_categories()
            if not main_cats:
                st.warning("कोई Category उपलब्ध नहीं है।")
            else:
                col_m, col_s = st.columns(2)
                with col_m:
                    sel_main_cat = st.selectbox("1️⃣ Main Category चुनें (उदा: किराना):", main_cats)

                sub_cats = get_subcategories_by_main(sel_main_cat)
                with col_s:
                    sel_sub_cat = st.selectbox("2️⃣ Sub-Category (उप-श्रेणी) चुनें:", ["सभी Sub-Categories"] + sub_cats)

                with get_db_connection() as conn:
                    c = conn.cursor()
                    if sel_sub_cat == "सभी Sub-Categories":
                        c.execute("SELECT id, service_name, unit, price_rate, sub_category FROM services WHERE is_active = 1 AND category = ?", (sel_main_cat,))
                    else:
                        c.execute("SELECT id, service_name, unit, price_rate, sub_category FROM services WHERE is_active = 1 AND category = ? AND sub_category = ?", (sel_main_cat, sel_sub_cat))
                    cat_items = c.fetchall()

                if not cat_items:
                    st.info("⚠️ इस उप-श्रेणी में अभी कोई सामान नहीं जोड़ा गया है।")
                else:
                    item_dict = {f"[{item[4]}] {item[1]} — (इकाई: {item[2] if item[2] else 'Kg'}, दर: ₹{item[3]})": item for item in cat_items}
                    
                    st.markdown("---")
                    selected_item_label = st.selectbox("3️⃣ सामान (Item) चुनें:", list(item_dict.keys()))
                    chosen_item = item_dict[selected_item_label]
                    item_unit = chosen_item[2] if chosen_item[2] else "Kg"

                    c_qty, c_unit, c_rate = st.columns(3)
                    with c_qty:
                        qty = st.number_input("🔢 मात्रा (Quantity):", min_value=0.25, value=1.0, step=0.5)
                    with c_unit:
                        st.text_input("📏 इकाई (Unit):", value=item_unit, disabled=True)
                    with c_rate:
                        rate = st.number_input("💵 दर / Rate (₹):", value=float(chosen_item[3]), step=1.0)
                    
                    if st.button("➕ कार्ट में जोड़ें (Add to Cart)"):
                        item_total = qty * rate
                        add_to_db_cart(cid, sel_main_cat, chosen_item[4], chosen_item[1], item_unit, qty, rate, item_total)
                        st.success(f"✅ '{chosen_item[1]}' कार्ट में सफलतापूर्वक जोड़ा गया!")

        with tab_cart:
            st.subheader("🛍️ आपकी कार्ट (Persistent Cart)")
            
            df_cart_db = get_db_cart(cid)
            
            if not df_cart_db.empty:
                df_cart_display = df_cart_db[['category', 'sub_category', 'item_name', 'unit', 'qty', 'rate', 'total']].copy()
                df_cart_display.columns = ['Main Category', 'Sub Category', 'Item Name', 'Unit', 'Quantity', 'Rate (₹)', 'Total Amount (₹)']
                
                st.dataframe(df_cart_display, use_container_width=True)
                
                grand_total = df_cart_db['total'].sum()
                st.markdown(f"### 💵 कुल योग (Grand Total): **₹{grand_total:,.2f}**")
                
                c_del1, c_del2 = st.columns([3, 1])
                with c_del1:
                    del_item_id = st.selectbox("🗑️ कार्ट से सामान हटाने के लिए चुनें:", df_cart_db['id'].tolist(), format_func=lambda x: df_cart_db[df_cart_db['id']==x]['item_name'].values[0])
                with c_del2:
                    if st.button("❌ Item हटाएं"):
                        delete_cart_item(del_item_id)
                        st.rerun()

                st.markdown("---")
                del_addr = st.text_area("🏠 डिलीवरी का पता:", value=c_addr)
                
                if st.button("🚀 आर्डर बुक करें"):
                    summary_lines = []
                    for _, row in df_cart_db.iterrows():
                        sub_info = f" ({row['sub_category']})" if row['sub_category'] else ""
                        summary_lines.append(f"• {row['item_name']}{sub_info} | Qty: {row['qty']} {row['unit']} | Rate: ₹{row['rate']} | Total: ₹{row['total']}")
                    
                    summary_str = "\n".join(summary_lines)
                    today_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute('''
                            INSERT INTO orders (client_id, items_summary, total_price, order_date, delivery_address)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (cid, summary_str, grand_total, today_dt, del_addr))
                        conn.commit()
                    
                    clear_db_cart(cid)
                    
                    st.success("🎉 आपका आर्डर बुक हो गया है!")
                    bill_msg = f"🧾 *NIKA GROCERY BILL* 🧾\n👤 *Customer:* {c_name} ({c_uid})\n📅 *Date:* {today_dt}\n\n*ITEMS:* \n{summary_str}\n\n💰 *Total: ₹{grand_total:,.2f}*\n🏠 *Address:* {del_addr}"
                    st.link_button("💬 व्हाट्सएप पर आर्डर भेजें", create_whatsapp_link(MY_CONTACT, bill_msg), use_container_width=True)
                    st.rerun()
            else:
                st.info("🛒 आपकी कार्ट खाली है। रिफ्रेश करने पर भी कार्ट का सामान डिलीट नहीं होगा!")

        with tab_my_orders:
            st.subheader("📦 मेरे पिछले ऑर्डर्स")
            with get_db_connection() as conn:
                df_my = pd.read_sql_query("SELECT id as 'Order ID', items_summary as 'Order Items', total_price as 'Total (₹)', order_date as 'Date', order_status as 'Status' FROM orders WHERE client_id = ? ORDER BY id DESC", conn, params=(cid,))
                if not df_my.empty:
                    st.dataframe(df_my, use_container_width=True)
                else:
                    st.info("अभी कोई पुराना आर्डर नहीं है।")
