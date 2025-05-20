from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import pickle
import numpy as np




app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database Setup
def init_db():
    with sqlite3.connect("churn.db") as con:
        cur = con.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT,
            churn_status TEXT DEFAULT 'Active'
        )
        """)
        cur.execute("""CREATE TABLE IF NOT EXISTS customerss (
            name TEXT,
            satisfaction_score REAL,
            -- Add other fields as necessary
            PRIMARY KEY (name)
        )
        """)

        con.commit()

init_db()

# Admin Routes
@app.route("/admin_register", methods=["GET", "POST"])
def admin_register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with sqlite3.connect("churn.db") as con:
            cur = con.cursor()
            cur.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (username, password))
            con.commit()
        return redirect(url_for("admin_login"))
    return render_template("admin_register.html")

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        with sqlite3.connect("churn.db") as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
            admin = cur.fetchone()
            if admin:
                session["admin"] = username
                return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")

@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" in session:
        with sqlite3.connect("churn.db") as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM customers")
            customers = cur.fetchall()
        return render_template("admin_dashboard.html", customers=customers)
    return redirect(url_for("admin_login"))


with open('model.pkl', 'rb') as f:
    churn_model = pickle.load(f)

# Database helper function to get customer details by satisfaction score
def get_customer_by_satisfaction_score(satisfaction_score):
    connection = sqlite3.connect('customers.db')  # Replace with your actual SQLite DB
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM customers WHERE satisfaction_score = ?", (satisfaction_score,))
    customer = cursor.fetchone()
    connection.close()
    return customer

# Customer Routes
@app.route("/customer_register", methods=["GET", "POST"])
def customer_register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        with sqlite3.connect("churn.db") as con:
            cur = con.cursor()
            cur.execute("INSERT INTO customers (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            con.commit()
        return redirect(url_for("customer_login"))
    return render_template("customer_register.html")

@app.route("/customer_login", methods=["GET", "POST"])
def customer_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        with sqlite3.connect("churn.db") as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM customers WHERE email=? AND password=?", (email, password))
            customer = cur.fetchone()
            if customer:
                session["customer"] = email
                return redirect(url_for("customer_dashboard"))
    return render_template("customer_login.html")

@app.route("/customer_dashboard")
def customer_dashboard():
    if "customer" in session:
        email = session["customer"]
        customer = get_customer_by_email(email)
        if customer:
            customer_data = {
                "name": customer[1],  
                "email": customer[2],  
                "satisfaction_score": customer[3],
                "churn_status": customer[4] if len(customer) > 4 else "Unknown"
            }
            return render_template("customer_dashboard.html", customer=customer_data)
    return redirect(url_for("customer_login"))


def get_customer_by_email(email):
    connection = sqlite3.connect('churn.db')
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM customers WHERE email=?", (email,))
    customer = cursor.fetchone()
    connection.close()
    return customer

@app.route("/predict_churn", methods=["POST"])
def predict_churn():
    if "customer" in session:
        email = session["customer"]

        # Collect 13 input values from the form
        customer_inputs = [
            request.form.get("age"),
            request.form.get("gender"),
            request.form.get("annual_income"),
            request.form.get("total_spend"),
            request.form.get("years_as_customer"),
            request.form.get("num_of_purchases"),
            request.form.get("average_transaction_amount"),
            request.form.get("num_of_returns"),
            request.form.get("num_of_support_contacts"),
            request.form.get("satisfaction_score"),
            request.form.get("last_purchase_days_ago"),
            request.form.get("email_opt_in"),
            request.form.get("promotion_response"),
        ]

        # Convert to float values
        try:
            customer_features = np.array([list(map(float, customer_inputs))])  # Shape (1, 13)
        except ValueError:
            return "Invalid input. Please enter valid numbers.", 400

        # Predict churn probability
        prediction = churn_model.predict(customer_features)[0]
        churn_status = "Churn" if prediction == 1 else "Active"

        # Update churn status in database
        connection = sqlite3.connect("churn.db")
        cursor = connection.cursor()
        cursor.execute("UPDATE customers SET churn_status=? WHERE email=?", 
               (churn_status, session["customer"]))
        connection.commit()
        connection.close()

        return redirect(url_for("customer_dashboard", prediction=churn_status))

    return redirect(url_for("customer_login"))



@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=False)
