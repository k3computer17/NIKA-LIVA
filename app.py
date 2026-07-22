import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import urllib.parse
import hashlib

# Page Configuration
st.set_page_config(page_title="NIKA - Multi-Service & Tax Portal", layout="wide")

# Custom Styling (Soft Orange, Ice Red & Clean Theme)
st.markdown("""
    <style>
    /* Main Background (Soft Orange & Ice Tone Gradient) */
    .main { 
        background: linear-gradient(135deg, #fff8f5 0%, #fff3ed 50%, #fce4ec 100%); 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    }
    
    /* Headings Styling */
    h1, h2, h3 { 
        color: #d84315 !important; 
        font-weight: 700;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #ffe0b2;
    }

    /* Buttons Styling (Orange & Red Gradient) */
    .stButton>button {
        background: linear-gradient(90deg, #f4511e 0%, #d32f2f 100%);
        color: white; 
        border-radius: 8px; 
        border: none; 
        padding: 10px 24px; 
        font-weight: bold;
        box-shadow: 0 4px 10px rgba(244, 81, 30, 0.25);
        transition: 0.3s;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #e64a19 0%, #c62828 100%);
        box-shadow: 0 6px 14px rgba(244, 81, 30, 0.35);
    }

    /* Link Buttons */
    .stLinkButton>a {
        background: linear-gradient(90deg, #f4511e 0%, #d32f2f 100%) !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
    }

    /* Input Fields Border Focus & Background */
    input, textarea, select {
        border-color: #ffccbc !important;
        background-color: #ffffff !important;
        border-radius: 6px !important;
    }

    /* Success / Info Boxes */
    .stAlert {
        background-color: #fff3e0 !important;
        border: 1px solid #ffccbc !important;
        color: #bf360c !important;
        border-radius: 8px;
    }
    
    /* Tabs Customization */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 6px 6px 0px 0px;
        padding: 10px 16px;
        color: #4e342e;
        border: 1px solid #ffe0b2;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fbe9e7 !important;
        color: #d84315 !important;
        border-bottom: 2px solid #d84315 !important;
    }
    </style>
""", unsafe_allow_html=True)

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database Connection
db_file = 'nika_clients_v2.db'
conn = sqlite3.connect(db_file, check_same_thread=False)
c = conn.cursor()

# ----------------- DATABASE TABLES SETUP -----------------
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        client_id INTEGER,
        is_approved INTEGER DEFAULT 1
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        unique_client_id TEXT,
        name TEXT,
        father_name TEXT,
        pan_number TEXT,
        mobile TEXT,
        address TEXT,
        itr_username TEXT,
        itr_password TEXT,
        created_date TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS client_gst (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        gst_number TEXT,
        gst_username TEXT,
        gst_password TEXT,
        trade_name TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS client_years (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        financial_year TEXT,
        annual_fee REAL DEFAULT 0,
        return_type TEXT,
        income_tax_status TEXT,
        gst_status TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        financial_year TEXT,
        payment_date TEXT,
        amount_paid REAL,
        payment_mode TEXT,
        remarks TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        service_name TEXT,
        price_rate REAL,
        description TEXT,
        is_active INTEGER DEFAULT 1
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        items_summary TEXT,
        total_price REAL,
        order_date TEXT,
        delivery_address TEXT,
        order_status TEXT DEFAULT 'Pending',
        remarks TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )
''')
conn.commit()

# --- SAFE MIGRATION ---
def add_column_safe(table_name, column_name, column_definition):
    try:
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        conn.commit()
    except sqlite3.OperationalError:
        pass

add_column_safe("orders", "order_status", "TEXT DEFAULT 'Pending'")
add_column_safe("orders", "delivery_address", "TEXT")
add_column_safe("orders", "remarks", "TEXT")
add_column_safe("users", "is_approved", "INTEGER DEFAULT 1")
add_column_safe("clients", "unique_client_id", "TEXT")

# Create Default Admin User if not exists
c.execute("SELECT * FROM users WHERE username = 'admin'")
if not c.fetchone():
    c.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)", 
              ('admin', make_hashes('admin123'), 'Admin', 1))
conn.commit()

# ----------------- FUNCTIONS -----------------
def generate_auto_client_id():
    c.execute("SELECT MAX(id) FROM clients")
    res = c.fetchone()
    last_id = res[0] if res and res[0] is not None else 0
    next_id = last_id + 1001
    return f"NIKA-{next_id}"

MY_CONTACT = "8358013017"

def create_whatsapp_link(client_mobile, message):
    if not client_mobile:
        return None
    clean_mobile = "".join(filter(str.isdigit, str(client_mobile)))
    if len(clean_mobile) == 10:
        clean_mobile = "91" + clean_mobile
    encoded_msg = urllib.parse.quote(message)
    return f"https://api.whatsapp.com/send?phone={clean_mobile}&text={encoded_msg}"

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_role" not in st.session_state:
    st.session_state.user_role = ""
if "client_id" not in st.session_state:
    st.session_state.client_id = None
if "cart" not in st.session_state:
    st.session_state.cart = []

# ================= LOGIN, SIGNUP & FORGOT PORTAL =================
if not st.session_state.logged_in:
    st.title("🏢 NIKA Multi-Service & Tax Portal")
    
    # Icons options for Login menu
    login_menu = ["🔐 Admin Login", "👤 Customer Login", "📝 New Registration", "🔄 Reset Password"]
    login_choice = st.sidebar.selectbox("📌 Navigation", login_menu)

    if login_choice == "🔐 Admin Login":
        st.subheader("👨‍💼 Master Admin Login")
        user = st.text_input("👤 Admin Username")
        passwd = st.text_input("🔑 Admin Password", type="password")
        if st.button("🚀 Master Login"):
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
            c.execute("SELECT password, client_id, is_approved FROM users WHERE username = ? AND role = 'Customer'", (user,))
            res = c.fetchone()
            if res:
                if res[2] == 0:
                    st.warning("⚠️ आपका अकाउंट अभी एडमिन द्वारा अप्रूव नहीं किया गया है।")
                    w_msg = f"नमस्ते एडमिन, मैंने नया रजिस्ट्रेशन किया है। कृपया मेरा यूजर आईडी ({user}) अप्रूव कर दें।"
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
        st.subheader("📝 Self Register as New Customer")
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

        if st.button("✨ Register & Send Approval Request"):
            if not c_name or not c_userid or not c_pass or not c_mobile or not c_address or not c_unique:
                st.error("कृपया सभी आवश्यक (*) फ़ील्ड भरें!")
            else:
                try:
                    today = datetime.now().strftime("%Y-%m-%d")
                    c.execute("INSERT INTO clients (unique_client_id, name, father_name, mobile, address, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                              (c_unique.upper(), c_name, c_father, c_mobile, c_address, today))
                    new_client_id = c.lastrowid
                    
                    c.execute("INSERT INTO users (username, password, role, client_id, is_approved) VALUES (?, ?, 'Customer', ?, 0)",
                              (c_userid, make_hashes(c_pass), new_client_id))
                    conn.commit()
                    st.success(f"✅ रजिस्ट्रेशन सफल हुआ! आपकी यूनिक आईडी है: **{c_unique.upper()}**")
                    
                    wa_text = f"नमस्ते एडमिन, मैंने नया रजिस्ट्रेशन किया है।\n\nनाम: {c_name}\nयूजर आईडी: {c_userid}\nयूनिक आईडी: {c_unique.upper()}\nमोबाइल: {c_mobile}\n\nकृपया मेरा अकाउंट अप्रूव करें।"
                    st.link_button("💬 Send Approval SMS/WhatsApp to Admin", create_whatsapp_link(MY_CONTACT, wa_text))
                except sqlite3.IntegrityError:
                    st.error("⚠️ यह Username पहले से मौजूद है। कृपया दूसरा चुनें।")

    elif login_choice == "🔄 Reset Password":
        st.subheader("🔄 Reset Your Password")
        f_user = st.text_input("🆔 Enter Your User ID / Username")
        f_mobile = st.text_input("📱 Enter Registered Mobile Number")
        f_unique = st.text_input("🏷️ Enter Unique Client ID")
        new_pass = st.text_input("🔑 Enter New Password", type="password")

        if st.button("🔄 Reset Password"):
            c.execute('''
                SELECT u.id, c.mobile, c.unique_client_id 
                FROM users u 
                JOIN clients c ON u.client_id = c.id 
                WHERE u.username = ? AND u.role = 'Customer'
            ''', (f_user,))
            r = c.fetchone()
            if r and r[1] == f_mobile and str(r[2]).upper() == f_unique.upper():
                c.execute("UPDATE users SET password = ? WHERE username = ?", (make_hashes(new_pass), f_user))
                conn.commit()
                st.success("✅ पासवर्ड सफलतापूर्वक बदल दिया गया है!")
            else:
                st.error("❌ विवरण (Details) मेल नहीं खा रहे हैं।")

# ================= LOGGED IN DASHBOARD =================
else:
    st.sidebar.write(f"👤 **{st.session_state.username}** ({st.session_state.user_role})")
    if st.sidebar.button("🔴 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_role = ""
        st.session_state.client_id = None
        st.session_state.cart = []
        st.rerun()

    if st.session_state.user_role == "Admin":
        st.title("👨‍💼 Master Admin Control Center")
        menu = [
            "⚙️ Manage Customers",
            "👥 Approve New Users",
            "🛍️ Manage Services",
            "📦 Customer Orders",
            "📊 Business Report"
        ]
        choice = st.sidebar.radio("📌 Admin Menu", menu)

        if choice == "⚙️ Manage Customers":
            st.subheader("⚙️ कस्टमर आईडी और डेटा अपडेट या डिलीट करें")
            c.execute("SELECT id, name, unique_client_id, mobile FROM clients ORDER BY id DESC")
            all_clients = c.fetchall()
            
            if not all_clients:
                st.info("कोई कस्टमर डेटा उपलब्ध नहीं है।")
            else:
                c_dict = {f"[{r[2] if r[2] else 'NO ID'}] {r[1]} - Mob: {r[3]}": r[0] for r in all_clients}
                selected_label = st.selectbox("🔍 कस्टमर चुनें:", list(c_dict.keys()))
                sel_cid = c_dict[selected_label]

                c.execute("SELECT unique_client_id, name, father_name, pan_number, mobile, address FROM clients WHERE id = ?", (sel_cid,))
                c_data = c.fetchone()

                tab_update, tab_delete = st.tabs(["✏️ अपडेट करें", "🗑️ डिलीट करें"])
                with tab_update:
                    up_unique = st.text_input("🆔 Unique Client ID", value=c_data[0] if c_data[0] else "")
                    up_name = st.text_input("👤 Full Name", value=c_data[1] if c_data[1] else "")
                    up_mobile = st.text_input("📱 Mobile Number", value=c_data[4] if c_data[4] else "")
                    up_address = st.text_area("🏠 Address", value=c_data[5] if c_data[5] else "")
                    
                    if st.button("💾 अपडेट सहेजें"):
                        c.execute("UPDATE clients SET unique_client_id = ?, name = ?, mobile = ?, address = ? WHERE id = ?",
                                  (up_unique.upper(), up_name, up_mobile, up_address, sel_cid))
                        conn.commit()
                        st.success("✅ अपडेट सफल रहा!")
                        st.rerun()

                with tab_delete:
                    if st.button("🗑️ डिलीट करें"):
                        c.execute("DELETE FROM clients WHERE id = ?", (sel_cid,))
                        conn.commit()
                        st.success("🗑️ डिलीट कर दिया गया!")
                        st.rerun()

        elif choice == "👥 Approve New Users":
            st.subheader("👥 Pending Customer Approvals")
            df_pend = pd.read_sql_query('''
                SELECT u.id as 'User Table ID', c.unique_client_id as 'Unique ID', c.name as 'Name', u.username as 'Username', c.mobile as 'Mobile'
                FROM users u
                JOIN clients c ON u.client_id = c.id
                WHERE u.role = 'Customer' AND u.is_approved = 0
            ''', conn)
            if not df_pend.empty:
                st.dataframe(df_pend, use_container_width=True)
                app_uid = st.number_input("🆔 Enter User Table ID to Approve:", min_value=1, step=1)
                if st.button("✅ Approve Customer"):
                    c.execute("UPDATE users SET is_approved = 1 WHERE id = ?", (app_uid,))
                    conn.commit()
                    st.success("Approved!")
                    st.rerun()
            else:
                st.info("No pending approvals.")

        elif choice == "🛍️ Manage Services":
            st.subheader("🛍️ Add Services & Rates")
            with st.form("service_form"):
                s_cat = st.selectbox("📂 Category:", ["किराना (Grocery)", "कपड़ा प्रेस / ड्राई क्लीन", "टैक्स व अकाउंटिंग"])
                s_name = st.text_input("🏷️ Service / Item Name")
                s_price = st.number_input("💵 Rate (₹):", min_value=0.0, step=10.0)
                if st.form_submit_button("💾 Add Service") and s_name.strip():
                    c.execute("INSERT INTO services (category, service_name, price_rate) VALUES (?, ?, ?)", (s_cat, s_name.strip(), s_price))
                    conn.commit()
                    st.success("Added!")
                    st.rerun()
            df_serv = pd.read_sql_query("SELECT id as ID, category as Category, service_name as 'Service', price_rate as 'Rate (₹)' FROM services WHERE is_active = 1", conn)
            st.dataframe(df_serv, use_container_width=True)

        elif choice == "📦 Customer Orders":
            st.subheader("📦 Customer Orders Management")
            df_orders = pd.read_sql_query('''
                SELECT 
                    o.id as 'Order ID',
                    COALESCE(c.unique_client_id, 'N/A') as 'Unique ID',
                    COALESCE(c.name, 'N/A') as 'Customer Name',
                    o.items_summary as 'Items',
                    o.total_price as 'Total (₹)',
                    o.order_date as 'Date',
                    o.order_status as 'Status'
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                ORDER BY o.id DESC
            ''', conn)
            if not df_orders.empty:
                st.dataframe(df_orders, use_container_width=True)
                ord_id = st.number_input("🆔 Order ID to Update Status:", min_value=1, step=1)
                new_status = st.selectbox("🔄 Status:", ["Pending", "Processing", "Out for Delivery", "Completed", "Cancelled"])
                if st.button("✨ Update Status"):
                    c.execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_status, ord_id))
                    conn.commit()
                    st.success("Status Updated!")
                    st.rerun()
            else:
                st.info("No orders found.")

        elif choice == "📊 Business Report":
            st.subheader("📊 Business Overview Report")
            df = pd.read_sql_query("SELECT unique_client_id as 'Unique ID', name, mobile, address FROM clients", conn)
            st.dataframe(df, use_container_width=True)

    elif st.session_state.user_role == "Customer":
        st.title("👤 Customer Service Portal & Cart")
        cid = st.session_state.client_id

        c.execute("SELECT unique_client_id, name, mobile, address FROM clients WHERE id = ?", (cid,))
        client_info = c.fetchone()
        c_uid = client_info[0] if client_info and client_info[0] else "N/A"
        c_name = client_info[1] if client_info and client_info[1] else "Customer"
        c_mob = client_info[2] if client_info and client_info[2] else "N/A"
        c_addr = client_info[3] if client_info and client_info[3] else ""

        st.info(f"👤 **{c_name}** | 🆔 **ID:** `{c_uid}`")

        tab_order, tab_cart, tab_my_orders = st.tabs(["🛒 Browse & Add", "🛍️ My Cart", "📦 My Orders"])

        with tab_order:
            st.subheader("🛍️ Select Items & Services")
            c.execute("SELECT id, category, service_name, price_rate FROM services WHERE is_active = 1")
            services_list = c.fetchall()
            if services_list:
                s_dict = {f"[{s[1]}] {s[2]} (₹{s[3]})": s for s in services_list}
                sel_label = st.selectbox("🔍 चुनें:", list(s_dict.keys()))
                s_item = s_dict[sel_label]
                qty = st.number_input("🔢 मात्रा (Quantity):", min_value=1, value=1, step=1)
                
                if st.button("➕ कार्ट में जोड़ें"):
                    st.session_state.cart.append({
                        "id": s_item[0], "name": s_item[2], "price": s_item[3], "qty": qty, "total": qty * s_item[3]
                    })
                    st.success("✅ कार्ट में जुड़ गया!")

        with tab_cart:
            st.subheader("🛍️ आपकी कार्ट")
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                st.dataframe(df_cart[['name', 'price', 'qty', 'total']], use_container_width=True)
                grand_total = df_cart['total'].sum()
                st.markdown(f"### 💵 कुल योग: **₹{grand_total:,.2f}**")
                
                del_addr = st.text_area("🏠 डिलिवरी पता:", value=c_addr)
                if st.button("🚀 आर्डर फाइनल करें"):
                    summary_str = ", ".join([f"{i['name']} (x{i['qty']})" for i in st.session_state.cart])
                    today_dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    c.execute('''
                        INSERT INTO orders (client_id, items_summary, total_price, order_date, delivery_address)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (cid, summary_str, grand_total, today_dt, del_addr))
                    conn.commit()
                    
                    st.success("🎉 ऑर्डर दर्ज हो गया!")
                    bill_msg = f"🧾 *NIKA STORE BILL* 🧾\n👤 {c_name} ({c_uid})\n\n{summary_str}\n\n💰 *Total: ₹{grand_total:,.2f}*\n🏠 {del_addr}"
                    st.link_button("💬 व्हाट्सएप पर बिल भेजें", create_whatsapp_link(MY_CONTACT, bill_msg), use_container_width=True)
                    st.session_state.cart = []
            else:
                st.info("🛒 कार्ट खाली है।")

        with tab_my_orders:
            st.subheader("📦 मेरे ऑर्डर्स")
            df_my = pd.read_sql_query("SELECT id as 'Order ID', items_summary as 'Items', total_price as 'Total (₹)', order_date as 'Date', order_status as 'Status' FROM orders WHERE client_id = ? ORDER BY id DESC", conn, params=(cid,))
            if not df_my.empty:
                st.dataframe(df_my, use_container_width=True)
            else:
                st.info("कोई आर्डर नहीं मिला।")
