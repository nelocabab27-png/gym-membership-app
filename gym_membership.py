from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)
# Secure secret key required for managing login sessions
app.secret_key = 'super_secure_gym_key_123' 
DATABASE = 'database.db'

def init_db():
    """Initializes the SQLite database with the upgraded table structures."""
    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        
        # 1. Members Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                tier TEXT,
                registration_date TEXT,
                due_date TEXT,
                status TEXT
            )
        ''')
        
        # 2. Daily Attendance Log Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                name TEXT NOT NULL,
                date TEXT NOT NULL,
                sign_in_time TEXT NOT NULL,
                sign_out_time TEXT
            )
        ''')
        
        conn.commit()
def update_membership_statuses():
    """Automatically check and expire delinquent accounts."""
    today = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE members SET status = 'Expired' WHERE due_date < ? AND status = 'Active'", (today,))
        conn.commit()

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handles Owner/Admin login portal."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Simple hardcoded credentials for demonstration/proposal purposes
        if username == 'admin' and password == '032706':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Owner Credentials!", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logs out the Owner and clears the session."""
    session.pop('admin_logged_in', None)
    return redirect(url_for('member_portal'))

# ==================== OWNER / ADMIN PORTAL ====================

@app.route('/admin')
def admin_dashboard():
    """Owner Management Suite Dashboard."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
        
    update_membership_statuses()
    
    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM members ORDER BY id DESC")
        members = cursor.fetchall()
        
        # Today's active gym goers
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("SELECT * FROM attendance WHERE date = ? ORDER BY id DESC", (today,))
        attendance_logs = cursor.fetchall()
        
        # Analytics metrics
        cursor.execute("SELECT COUNT(*) FROM members")
        total_members = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM members WHERE status = 'Active'")
        active_members = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = ? AND sign_out_time IS NULL", (today,))
        currently_inside = cursor.fetchone()[0]
        
    return render_template(
        'admin.html', 
        members=members, 
        attendance=attendance_logs,
        total=total_members, 
        active=active_members, 
        inside=currently_inside
    )

@app.route('/provision_member', methods=['POST'])
def provision_member():
    # 1. Grab the data sent from your HTML form fields
    name = request.form.get('name')
    email = request.form.get('email')
    selected_tier = request.form.get('tier')  # 'daily' or 'monthly'
    
    # 2. Get today's registration date
    registration_date = datetime.now().strftime('%Y-%m-%d')
    
    # Connect to your database
    conn = sqlite3.connect('database.db')
    db = conn.cursor()
    
    # 3. Check if this email already exists in the system
    existing_client = db.execute("SELECT * FROM members WHERE email = ?", (email,)).fetchone()
    
    # 4. Apply your custom pricing logic and dynamic expiration dates
    if not existing_client:
        # BRAND NEW MEMBER: 1-Year subscription required
        # Base Monthly (500) + First-time fee (200) = 700 Pesos
        assigned_tier = "Monthly (₱700)"
        maturity_due_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
        
        # 5a. Save as a brand-new record
        db.execute("""
            INSERT INTO members (name, email, tier, registration_date, due_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, assigned_tier, registration_date, maturity_due_date, 'Active'))
        
    else:
        # RETURNING MEMBER: Calculate standard rates and appropriate expiration periods
        if selected_tier == 'daily':
            assigned_tier = "Daily (₱50)"
            maturity_due_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            assigned_tier = "Monthly (₱500)"
            maturity_due_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            
        # 5b. UPDATE the existing member instead of inserting a duplicate row
        db.execute("""
            UPDATE members 
            SET name = ?, tier = ?, registration_date = ?, due_date = ?, status = ?
            WHERE email = ?
        """, (name, assigned_tier, registration_date, maturity_due_date, 'Active', email))
    
    conn.commit()
    conn.close()
    
    # 6. Return safely back to your central ledger dashboard
    return redirect('/admin')
@app.route('/')
def member_portal():
    """Public kiosk terminal interface for running daily check-ins."""
    return render_template('member_portal.html')

@app.route('/member_action', methods=['POST'])
def member_action():
    """Automated workflow processing daily Sign-In or Sign-Out logs."""
    email = request.form['email'].strip()
    action = request.form['action'] # 'signin' or 'signout'
    today = datetime.now().strftime('%Y-%m-%d')
    current_time = datetime.now().strftime('%I:%M %p')

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Verify membership existence and state status
        cursor.execute("SELECT * FROM members WHERE email = ?", (email,))
        member = cursor.fetchone()
        
        if not member:
            flash("Account access denied: Profile email not found.", "danger")
            return redirect(url_for('member_portal'))
        
        if member['status'] == 'Expired':
            flash(f"Access Denied: {member['name']}, your membership expired on {member['due_date']}. Please see the owner.", "danger")
            return redirect(url_for('member_portal'))

        # 2. Process Actions
        if action == 'signin':
            # Prevent double signing in
            cursor.execute("SELECT * FROM attendance WHERE email = ? AND date = ? AND sign_out_time IS NULL", (email, today))
            already_inside = cursor.fetchone()
            if already_inside:
                flash("You are already signed in to the facility!", "warning")
            else:
                cursor.execute(
                    "INSERT INTO attendance (email, name, date, sign_in_time) VALUES (?, ?, ?, ?)",
                    (email, member['name'], today, current_time)
                )
                flash(f"Welcome, {member['name']}! Signed In successfully at {current_time}.", "success")
                
        elif action == 'signout':
            # Check if there is an active sign-in record to update
            cursor.execute("SELECT * FROM attendance WHERE email = ? AND date = ? AND sign_out_time IS NULL", (email, today))
            active_session = cursor.fetchone()
            if active_session:
                cursor.execute(
                    "UPDATE attendance SET sign_out_time = ? WHERE id = ?",
                    (current_time, active_session['id'])
                )
                flash(f"Goodbye, {member['name']}! Signed Out successfully at {current_time}. Great workout!", "success")
            else:
                flash("No active Sign-In session found for today.", "warning")
                
        conn.commit()
        
    return redirect(url_for('member_portal'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

    