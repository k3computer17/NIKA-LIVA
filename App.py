import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import urllib.parse
import hashlib

# Page Configuration
st.set_page_config(page_title="NIKA - Multi-Service & Tax Portal", layout="wide")

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #f4f6f9; font-family: 'Segoe UI', sans-serif; }
    h1, h2, h3 { color: #1a237e !important; }
    .stButton>button {
        background: linear-gradient(90deg, #1e88e5 0%, #1565c0 100%);
        color: white; border-radius: 8px; border: none; padding: 10px 24px; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to hash passwords
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return hashed_text
    return False

# Database Connection
conn = sqlite3.connect('nika_clients_v2.db', check_same_thread=False)
c = conn.cursor()

# ----------------- DATABASE TABLES SETUP -----------------
c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        client_id INTEGER
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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

# New Table: Admin Offered Services (किराना, कपड़ा प्रेस, आदि)
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

# New Table: Customer Orders
c.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        service_id INTEGER,
        service_name TEXT,
        quantity INTEGER,
        total_price REAL,
        order_date TEXT,
        delivery_address TEXT,
        order_status TEXT DEFAULT 'Pending',
        remarks TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(service_id) REFERENCES services(id)
    )
''')

# Create Default Admin User if not exists
c.execute("SELECT * FROM users WHERE username = 'admin'")
if not c.fetchone():
    c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
              ('admin', make_hashes('admin123'), 'Admin'))
conn.commit()

FY_LIST = ["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026", "2026-2027"]
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

# ================= LOGIN & SIGNUP PORTAL =================
if not st.session_state.logged_in:
    st.title("🏢 NIKA Multi-Service & Tax Portal")
    login_menu = ["🔐 Admin Login", "👤 Customer Login", "📝 New Customer Self-Registration"]
    login_choice = st.sidebar.selectbox("Navigation", login_menu)

    # 1. ADMIN LOGIN
    if login_choice == "🔐 Admin Login":
        st.subheader("👨‍💼 Master Admin Login")
        user = st.text_input("Admin Username")
        passwd = st.text_input("Admin Password", type="password")
        if st.button("Master Login"):
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

    # 2. CUSTOMER LOGIN
    elif login_choice == "👤 Customer Login":
        st.subheader("👤 Customer Portal Login")
        user = st.text_input("User ID / Username")
        passwd = st.text_input("Password", type="password")
        if st.button("Customer Login"):
            c.execute("SELECT password, client_id FROM users WHERE username = ? AND role = 'Customer'", (user,))
            res = c.fetchone()
            if res and check_hashes(passwd, res[0]):
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.user_role = "Customer"
                st.session_state.client_id = res[1]
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid User ID or Password")

    # 3. NEW CUSTOMER SELF-REGISTRATION
    elif login_choice == "📝 New Customer Self-Registration":
        st.subheader("📝 Self Register as New Customer")
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("Full Name *")
            c_father = st.text_input("Father's Name")
            c_mobile = st.text_input("Mobile Number *")
            c_address = st.text_area("Delivery / Home Address *")
        with col2:
            c_pan = st.text_input("PAN Number (Optional)")
            c_userid = st.text_input("Create User ID / Username *")
            c_pass = st.text_input("Create Password *", type="password")

        if st.button("Create Account & Register"):
            if not c_name or not c_userid or not c_pass or not c_mobile or not c_address:
                st.error("Please fill all required fields (*)")
            else:
                try:
                    today = datetime.now().strftime("%Y-%m-%d")
                    c.execute("INSERT INTO clients (name, father_name, pan_number, mobile, address, created_date) VALUES (?, ?, ?, ?, ?, ?)",
                              (c_name, c_father, c_pan.upper(), c_mobile, c_address, today))
                    new_client_id = c.lastrowid
                    
                    c.execute("INSERT INTO users (username, password, role, client_id) VALUES (?, ?, 'Customer', ?)",
                              (c_userid, make_hashes(c_pass), new_client_id))
                    conn.commit()
                    st.success("✅ Account created successfully! Please go to 'Customer Login' tab to sign in.")
                except sqlite3.IntegrityError:
                    st.error("⚠️ Username already taken! Choose a different User ID.")

# ================= LOGGED IN DASHBOARD =================
else:
    st.sidebar.write(f"Logged in as: **{st.session_state.username}** ({st.session_state.user_role})")
    if st.sidebar.button("🔴 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_role = ""
        st.session_state.client_id = None
        st.rerun()

    # --------------- ADMIN MENU ---------------
    if st.session_state.user_role == "Admin":
        st.title("👨‍💼 Master Admin Control Center")
        menu = [
            "🛍️ Manage Services & Rates",
            "📦 View & Manage Customer Orders",
            "➕ Add New Client Profile", 
            "✏️ Edit Client Profile",
            "📅 Add / Update Financial Year Fee",
            "💵 Receive Payment",
            "🔍 Client Ledger & Credentials", 
            "📊 Overall Business Report"
        ]
        choice = st.sidebar.radio("Admin Menu", menu)

        # 1. Manage Services Offered by Admin
        if choice == "🛍️ Manage Services & Rates":
            st.subheader("🛍️ Add & Manage Offered Services (Grocery, Laundry, Tax, etc.)")
            
            with st.expander("➕ Add New Service Option", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    s_cat = st.selectbox("Category:", ["किराना (Grocery)", "कपड़ा प्रेस / ड्राई क्लीन", "टैक्स व अकाउंटिंग", "अन्य सेवा (Other Services)"])
                    s_name = st.text_input("Service / Item Name (e.g. Rice 10kg, Shirt Ironing, ITR Filing)")
                with col2:
                    s_price = st.number_input("Rate / Price (₹ per unit):", min_value=0.0, step=10.0)
                    s_desc = st.text_area("Description / Details:")
                
                if st.button("💾 Add Service"):
                    if s_name.strip():
                        c.execute("INSERT INTO services (category, service_name, price_rate, description) VALUES (?, ?, ?, ?)",
                                  (s_cat, s_name.strip(), s_price, s_desc))
                        conn.commit()
                        st.success(f"✅ Service '{s_name}' added successfully!")
                        st.rerun()
                    else:
                        st.error("Please enter Service Name!")

            st.markdown("---")
            st.markdown("### 📋 Active Offered Services")
            df_serv = pd.read_sql_query("SELECT id as ID, category as Category, service_name as 'Service Name', price_rate as 'Rate (₹)', description as Details FROM services WHERE is_active = 1", conn)
            if not df_serv.empty:
                st.dataframe(df_serv, use_container_width=True)
                
                del_s_id = st.number_input("Enter Service ID to Delete:", min_value=1, step=1)
                if st.button("❌ Remove Service"):
                    c.execute("UPDATE services SET is_active = 0 WHERE id = ?", (del_s_id,))
                    conn.commit()
                    st.success("Service removed!")
                    st.rerun()
            else:
                st.info("No services added yet.")

        # 2. View and Manage Customer Orders
        elif choice == "📦 View & Manage Customer Orders":
            st.subheader("📦 Customer Orders Dashboard")
            
            df_orders = pd.read_sql_query('''
                SELECT 
                    o.id as 'Order ID',
                    c.name as 'Customer Name',
                    c.mobile as 'Mobile',
                    o.service_name as 'Service / Item',
                    o.quantity as 'Qty',
                    o.total_price as 'Total (₹)',
                    o.order_date as 'Order Date',
                    o.delivery_address as 'Address',
                    o.order_status as 'Status',
                    o.remarks as 'Customer Note'
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                ORDER BY o.id DESC
            ''', conn)
            
            if not df_orders.empty:
                st.dataframe(df_orders, use_container_width=True)
                
                st.markdown("---")
                st.markdown("### ✏️ Update Order Status")
                col_o1, col_o2 = st.columns(2)
                with col_o1:
                    ord_id = st.number_input("Select Order ID to Update:", min_value=1, step=1)
                with col_o2:
                    new_status = st.selectbox("Change Status To:", ["Pending", "Accepted / In Progress", "Out for Delivery / Processing", "Completed", "Cancelled"])
                
                if st.button("💾 Update Order Status"):
                    c.execute("UPDATE orders SET order_status = ? WHERE id = ?", (new_status, ord_id))
                    conn.commit()
                    st.success(f"Order #{ord_id} status updated to '{new_status}'!")
                    st.rerun()
            else:
                st.warning("No orders placed yet.")

        elif choice == "➕ Add New Client Profile":
            st.subheader("📝 Add Client Profile (Admin)")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Client Full Name *")
                father = st.text_input("Father's Name")
                mobile = st.text_input("Mobile Number")
                address = st.text_area("Address")
            with col2:
                pan = st.text_input("PAN Card Number")
                itr_u = st.text_input("ITR Portal User ID")
                itr_p = st.text_input("ITR Portal Password", type="password")

            if st.button("Save Client"):
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute("INSERT INTO clients (name, father_name, pan_number, mobile, address, itr_username, itr_password, created_date) VALUES (?,?,?,?,?,?,?,?)",
                          (name, father, pan.upper(), mobile, address, itr_u, itr_p, today))
                conn.commit()
                st.success("Client Added!")

        elif choice == "🔍 Client Ledger & Credentials":
            st.subheader("🔍 Client Statement & Master Ledger")
            c.execute("SELECT id, name, pan_number, mobile FROM clients ORDER BY name ASC")
            clients = c.fetchall()
            if clients:
                opts = {f"{r[1]} | PAN: {r[2]}": r[0] for r in clients}
                sel = st.selectbox("Select Client:", list(opts.keys()))
                cid = opts[sel]

                fy = st.selectbox("Select Financial Year:", FY_LIST, index=4)
                c.execute("SELECT annual_fee FROM client_years WHERE client_id = ? AND financial_year = ?", (cid, fy))
                fee_r = c.fetchone()
                fee = fee_r[0] if fee_r else 0.0

                df_p = pd.read_sql_query("SELECT payment_date as Date, amount_paid as Paid, payment_mode as Mode, remarks as Remarks FROM payments WHERE client_id = ? AND financial_year = ?", conn, params=(cid, fy))
                tot_p = df_p['Paid'].sum() if not df_p.empty else 0.0
                due = fee - tot_p

                m1, m2, m3 = st.columns(3)
                m1.metric("Fee", f"₹{fee}")
                m2.metric("Received", f"₹{tot_p}")
                m3.metric("Due", f"₹{due}")

                st.dataframe(df_p)

        elif choice == "📊 Overall Business Report":
            st.subheader("📊 Business Financial Report")
            df = pd.read_sql_query("SELECT c.name, c.pan_number, c.mobile FROM clients c", conn)
            st.dataframe(df, use_container_width=True)

    # --------------- CUSTOMER MENU ---------------
    elif st.session_state.user_role == "Customer":
        st.title("👤 Customer Service Portal")
        cid = st.session_state.client_id

        c.execute("SELECT name, pan_number, mobile, address, itr_username, itr_password FROM clients WHERE id = ?", (cid,))
        client_info = c.fetchone()

        st.info(f"👤 **Welcome, {client_info[0]}!** | 📱 **Mobile:** {client_info[2]} | 🏠 **Address:** {client_info[3]}")

        # Customer Tabs
        tab_order, tab_my_orders, tab_ledger, tab_cred = st.tabs([
            "🛒 Place Order (किराना, कपड़ा प्रेस, आदि)", 
            "📦 My Orders Status", 
            "📊 My Tax & Fee Ledger", 
            "🔑 My Credentials"
        ])

        # TAB 1: PLACE NEW ORDER
        with tab_order:
            st.subheader("🛍️ Choose Service & Place Order")
            
            c.execute("SELECT id, category, service_name, price_rate, description FROM services WHERE is_active = 1")
            services_list = c.fetchall()
            
            if not services_list:
                st.warning("Currently no services are available for order.")
            else:
                service_dict = {f"[{s[1]}] {s[2]} - ₹{s[3]}/unit": s for s in services_list}
                selected_s_label = st.selectbox("Select Service / Item:", list(service_dict.keys()))
                s_data = service_dict[selected_s_label]
                
                s_id, s_cat, s_name, s_price, s_desc = s_data
                
                st.info(f"📌 **Details:** {s_desc if s_desc else 'N/A'}")
                
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    qty = st.number_input("Quantity / Units:", min_value=1, value=1, step=1)
                    del_addr = st.text_area("Delivery / Pick-up Address:", value=client_info[3] if client_info[3] else "")
                with col_p2:
                    total_amount = qty * s_price
                    st.metric("Total Amount to Pay", f"₹{total_amount:,.2f}")
                    user_note = st.text_input("Special Note / Instruction (Optional):")
                
                if st.button("🛒 Confirm & Place Order"):
                    today = datetime.now().strftime("%Y-%m-%d %H:%M")
                    c.execute('''
                        INSERT INTO orders (client_id, service_id, service_name, quantity, total_price, order_date, delivery_address, remarks)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (cid, s_id, s_name, qty, total_amount, today, del_addr, user_note))
                    conn.commit()
                    
                    st.success("🎉 Order Placed Successfully!")
                    
                    # WhatsApp Notification to Admin
                    msg_order = f"नमस्ते, नया ऑर्डर प्राप्त हुआ है!\n\n👤 **कस्टमर:** {client_info[0]}\n📱 **मोबाइल:** {client_info[2]}\n🛍️ **सर्विस:** {s_name}\n🔢 **मात्रा:** {qty}\n💰 **कुल राशि:** ₹{total_amount}\n🏠 **पता:** {del_addr}\n📝 **नोट:** {user_note}"
                    wa_url = create_whatsapp_link(MY_CONTACT, msg_order)
                    st.link_button("💬 Send Order Details to Admin on WhatsApp", wa_url, use_container_width=True)

        # TAB 2: MY ORDERS STATUS
        with tab_my_orders:
            st.subheader("📦 My Placed Orders & Live Status")
            df_my_ord = pd.read_sql_query('''
                SELECT 
                    id as 'Order ID',
                    service_name as 'Service / Item',
                    quantity as 'Qty',
                    total_price as 'Total (₹)',
                    order_date as 'Date',
                    order_status as 'Status',
                    delivery_address as 'Address'
                FROM orders WHERE client_id = ? ORDER BY id DESC
            ''', conn, params=(cid,))
            
            if not df_my_ord.empty:
                st.dataframe(df_my_ord, use_container_width=True)
            else:
                st.info("You haven't placed any orders yet.")

        # TAB 3: TAX & FEE LEDGER
        with tab_ledger:
            st.subheader("📅 Financial Year Ledger")
            sel_fy = st.selectbox("Select Financial Year:", FY_LIST, index=4)

            c.execute("SELECT annual_fee, return_type, income_tax_status, gst_status FROM client_years WHERE client_id = ? AND financial_year = ?", (cid, sel_fy))
            y_data = c.fetchone()

            fee = y_data[0] if y_data else 0.0
            itr_st = y_data[2] if y_data else "N/A"
            gst_st = y_data[3] if y_data else "N/A"

            df_p = pd.read_sql_query("SELECT payment_date as Date, amount_paid as 'Amount Paid (₹)', payment_mode as Mode, remarks as Remarks FROM payments WHERE client_id = ? AND financial_year = ?", conn, params=(cid, sel_fy))
            paid = df_p['Amount Paid (₹)'].sum() if not df_p.empty else 0.0
            due = fee - paid

            c1, c2, c3 = st.columns(3)
            c1.metric("Agreed Tax Fee", f"₹{fee:,.2f}")
            c2.metric("Total Paid Amount", f"₹{paid:,.2f}")
            c3.metric("Current Due", f"₹{due:,.2f}")

            st.markdown(f"**ITR Filing Status:** `{itr_st}` | **GST Filing Status:** `{gst_st}`")
            st.dataframe(df_p, use_container_width=True)

        # TAB 4: MY CREDENTIALS
        with tab_cred:
            st.subheader("🔑 Saved Credentials")
            st.write(f"**ITR Username:** `{client_info[4]}`")
            st.write(f"**ITR Password:** `{client_info[5]}`")

            c.execute("SELECT gst_number, gst_username, gst_password, trade_name FROM client_gst WHERE client_id = ?", (cid,))
            gsts = c.fetchall()
            if gsts:
                st.markdown("#### 🏬 GST Credentials")
                for g in gsts:
                    st.info(f"**Trade:** {g[3]} | **GSTIN:** `{g[0]}` | **User:** `{g[1]}` | **Pass:** `{g[2]}`")
