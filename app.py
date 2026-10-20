from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)
import sqlite3
import os
import hashlib
from functools import wraps
from datetime import datetime

app = Flask(__name__)

app.secret_key = "fitmeal_project_secret_key_2026"

DATABASE = "fitmeal.db"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# PASSWORD HASHING
# ==========================================

def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            role TEXT DEFAULT 'customer',
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price REAL NOT NULL,
            image TEXT,
            available INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            address TEXT,
            payment_method TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            food_id INTEGER NOT NULL,
            food_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan_name TEXT NOT NULL,
            duration INTEGER NOT NULL,
            meals_per_day INTEGER DEFAULT 1,
            start_date TEXT,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'Active',
            remaining_meals INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            food_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diet_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            preference TEXT,
            allergies TEXT,
            goal TEXT
        )
    """)

    # Create demo admin account if it doesn't exist.
    admin = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        ("admin@fitmeal.local",)
    ).fetchone()

    if admin is None:
        cursor.execute("""
            INSERT INTO users
            (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "FitMeal Admin",
            "admin@fitmeal.local",
            hash_password("Admin@123"),
            "admin",
            datetime.now().isoformat()
        ))

    # Insert sample foods only when the table is empty.
    count = cursor.execute(
        "SELECT COUNT(*) FROM foods"
    ).fetchone()[0]

    if count == 0:
        foods = [
            (
                "Homemade Veg Thali",
                "Fresh homemade vegetarian meal",
                "Homemade",
                120,
                "",
                1
            ),
            (
                "Chapati Bhaji",
                "Chapati served with fresh bhaji",
                "Homemade",
                80,
                "",
                1
            ),
            (
                "Dal Rice",
                "Healthy dal with steamed rice",
                "Homemade",
                90,
                "",
                1
            ),
            (
                "Paneer Meal",
                "Protein-rich paneer meal",
                "Fitness",
                180,
                "",
                1
            ),
            (
                "Grilled Chicken",
                "Grilled chicken with vegetables",
                "Fitness",
                220,
                "",
                1
            ),
            (
                "Sprouts Salad",
                "Fresh sprouts and vegetable salad",
                "Diet",
                100,
                "",
                1
            ),
            (
                "Oats Breakfast",
                "Healthy oats breakfast",
                "Diet",
                90,
                "",
                1
            ),
            (
                "Fruit Bowl",
                "Seasonal fresh fruit bowl",
                "Diet",
                110,
                "",
                1
            ),
            (
                "Idli Sambar",
                "Soft idli served with sambar",
                "Homemade",
                70,
                "",
                1
            ),
            (
                "Veg Pulao",
                "Rice cooked with vegetables",
                "Homemade",
                110,
                "",
                1
            ),
        ]

        cursor.executemany("""
            INSERT INTO foods
            (name, description, category, price, image, available)
            VALUES (?, ?, ?, ?, ?, ?)
        """, foods)

    conn.commit()
    conn.close()


# ==========================================
# LOGIN REQUIRED DECORATOR
# ==========================================

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# ADMIN REQUIRED DECORATOR
# ==========================================

def admin_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def index():
    conn = get_db()

    foods = conn.execute("""
        SELECT * FROM foods
        WHERE available = 1
        ORDER BY id DESC
        LIMIT 6
    """).fetchall()

    conn.close()

    return render_template(
        "index.html",
        foods=foods
    )


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()

        if not name or not email or not password:
            flash("Please fill all required fields.", "danger")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )
            return redirect(url_for("register"))

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO users
                (name, email, password, phone, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                name,
                email,
                hash_password(password),
                phone,
                "customer",
                datetime.now().isoformat()
            ))

            conn.commit()

            flash(
                "Registration successful. Please login.",
                "success"
            )

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")

        finally:
            conn.close()

    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users
            WHERE email = ? AND password = ?
        """, (
            email,
            hash_password(password)
        )).fetchone()

        conn.close()

        if user:

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            flash("Login successful.", "success")

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("index"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash("You have been logged out.", "info")

    return redirect(url_for("index"))


# ==========================================
# FOOD MENU
# ==========================================

@app.route("/menu")
def menu():

    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    conn = get_db()

    query = """
        SELECT * FROM foods
        WHERE available = 1
    """

    parameters = []

    if category:
        query += " AND category = ?"
        parameters.append(category)

    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        parameters.extend([
            "%" + search + "%",
            "%" + search + "%"
        ])

    query += " ORDER BY name"

    foods = conn.execute(
        query,
        parameters
    ).fetchall()

    conn.close()

    return render_template(
        "menu.html",
        foods=foods,
        category=category,
        search=search
    )


# ==========================================
# FOOD DETAILS
# ==========================================

@app.route("/food/<int:food_id>")
def food_details(food_id):

    conn = get_db()

    food = conn.execute("""
        SELECT * FROM foods
        WHERE id = ? AND available = 1
    """, (food_id,)).fetchone()

    if food is None:
        conn.close()
        flash("Food item not found.", "danger")
        return redirect(url_for("menu"))

    reviews = conn.execute("""
        SELECT reviews.*, users.name
        FROM reviews
        JOIN users ON users.id = reviews.user_id
        WHERE reviews.food_id = ?
        ORDER BY reviews.id DESC
    """, (food_id,)).fetchall()

    conn.close()

    return render_template(
        "food_details.html",
        food=food,
        reviews=reviews
    )


# ==========================================
# ADD TO CART
# ==========================================

@app.route("/add-to-cart/<int:food_id>", methods=["POST"])
@login_required
def add_to_cart(food_id):

    conn = get_db()

    food = conn.execute("""
        SELECT * FROM foods
        WHERE id = ? AND available = 1
    """, (food_id,)).fetchone()

    conn.close()

    if food is None:
        flash("Food item is unavailable.", "danger")
        return redirect(url_for("menu"))

    cart = session.get("cart", {})

    key = str(food_id)

    quantity = cart.get(key, 0)
    cart[key] = min(int(quantity) + 1, 20)

    session["cart"] = cart

    flash("Food added to cart.", "success")

    return redirect(url_for("menu"))


# ==========================================
# VIEW CART
# ==========================================

@app.route("/cart")
@login_required
def cart():

    cart_data = session.get("cart", {})
    items = []
    total = 0

    conn = get_db()

    for food_id, quantity in cart_data.items():

        food = conn.execute("""
            SELECT * FROM foods
            WHERE id = ? AND available = 1
        """, (int(food_id),)).fetchone()

        if food:

            quantity = int(quantity)
            subtotal = food["price"] * quantity

            items.append({
                "food": food,
                "quantity": quantity,
                "subtotal": subtotal
            })

            total += subtotal

    conn.close()

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


# ==========================================
# UPDATE CART
# ==========================================

@app.route("/update-cart/<int:food_id>", methods=["POST"])
@login_required
def update_cart(food_id):

    quantity = request.form.get(
        "quantity", "1"
    )

    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1

    cart = session.get("cart", {})
    key = str(food_id)

    if quantity <= 0:
        cart.pop(key, None)

    elif quantity <= 20:
        cart[key] = quantity

    else:
        cart[key] = 20
        flash("Maximum quantity is 20.", "warning")

    session["cart"] = cart

    return redirect(url_for("cart"))


# ==========================================
# REMOVE CART ITEM
# ==========================================

@app.route("/remove-from-cart/<int:food_id>")
@login_required
def remove_from_cart(food_id):

    cart = session.get("cart", {})

    cart.pop(str(food_id), None)

    session["cart"] = cart

    flash("Item removed from cart.", "info")

    return redirect(url_for("cart"))


# ==========================================
# CHECKOUT
# ==========================================

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():

    cart_data = session.get("cart", {})

    if not cart_data:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("menu"))

    conn = get_db()

    items = []
    total = 0

    for food_id, quantity in cart_data.items():

        food = conn.execute("""
            SELECT * FROM foods
            WHERE id = ? AND available = 1
        """, (int(food_id),)).fetchone()

        if food:
            quantity = int(quantity)
            subtotal = food["price"] * quantity

            items.append({
                "food": food,
                "quantity": quantity,
                "subtotal": subtotal
            })

            total += subtotal

    if not items:
        conn.close()
        session["cart"] = {}
        flash("Your cart contains no available items.", "warning")
        return redirect(url_for("menu"))

    if request.method == "POST":

        address = request.form.get(
            "address", ""
        ).strip()

        payment_method = request.form.get(
            "payment_method", "COD"
        )

        if not address:
            conn.close()
            flash("Please enter your delivery address.", "danger")
            return redirect(url_for("checkout"))

        if payment_method not in ["COD", "DEMO"]:
            conn.close()
            flash("Invalid payment method.", "danger")
            return redirect(url_for("checkout"))

        cursor = conn.execute("""
            INSERT INTO orders
            (user_id, total, address, payment_method,
             status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            total,
            address,
            payment_method,
            "Pending",
            datetime.now().isoformat()
        ))

        order_id = cursor.lastrowid

        for item in items:

            conn.execute("""
                INSERT INTO order_items
                (order_id, food_id, food_name, quantity, price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                order_id,
                item["food"]["id"],
                item["food"]["name"],
                item["quantity"],
                item["food"]["price"]
            ))

        conn.commit()
        conn.close()

        session["cart"] = {}

        flash("Order placed successfully.", "success")

        return redirect(
            url_for("order_details", order_id=order_id)
        )

    conn.close()

    return render_template(
        "checkout.html",
        items=items,
        total=total
    )


# ==========================================
# CUSTOMER ORDERS
# ==========================================

@app.route("/orders")
@login_required
def orders():

    conn = get_db()

    orders_list = conn.execute("""
        SELECT * FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "orders.html",
        orders=orders_list
    )


# ==========================================
# ORDER DETAILS
# ==========================================

@app.route("/order/<int:order_id>")
@login_required
def order_details(order_id):

    conn = get_db()

    order = conn.execute("""
        SELECT * FROM orders
        WHERE id = ? AND user_id = ?
    """, (
        order_id,
        session["user_id"]
    )).fetchone()

    if order is None:
        conn.close()
        flash("Order not found.", "danger")
        return redirect(url_for("orders"))

    items = conn.execute("""
        SELECT * FROM order_items
        WHERE order_id = ?
    """, (order_id,)).fetchall()

    conn.close()

    return render_template(
        "order_details.html",
        order=order,
        items=items
    )


# ==========================================
# TIFFIN SUBSCRIPTION
# ==========================================

@app.route("/subscription", methods=["GET", "POST"])
@login_required
def subscription():

    plans = [
        {
            "name": "Weekly Tiffin",
            "duration": 7,
            "price": 700
        },
        {
            "name": "Monthly Tiffin",
            "duration": 30,
            "price": 2800
        }
    ]

    if request.method == "POST":

        plan_name = request.form.get("plan", "")
        start_date = request.form.get("start_date", "")

        selected_plan = None

        for plan in plans:
            if plan["name"] == plan_name:
                selected_plan = plan
                break

        if selected_plan is None:
            flash("Please select a valid plan.", "danger")
            return redirect(url_for("subscription"))

        try:
            datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            flash("Please select a valid start date.", "danger")
            return redirect(url_for("subscription"))

        conn = get_db()

        conn.execute("""
            INSERT INTO subscriptions
            (user_id, plan_name, duration, meals_per_day,
             start_date, total_price, status, remaining_meals)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            selected_plan["name"],
            selected_plan["duration"],
            1,
            start_date,
            selected_plan["price"],
            "Active",
            selected_plan["duration"]
        ))

        conn.commit()
        conn.close()

        flash("Tiffin subscription booked successfully.", "success")

        return redirect(url_for("my_subscriptions"))

    return render_template(
        "subscription.html",
        plans=plans
    )


# ==========================================
# MY SUBSCRIPTIONS
# ==========================================

@app.route("/my-subscriptions")
@login_required
def my_subscriptions():

    conn = get_db()

    subscriptions = conn.execute("""
        SELECT * FROM subscriptions
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "my_subscriptions.html",
        subscriptions=subscriptions
    )


# ==========================================
# CANCEL SUBSCRIPTION
# ==========================================

@app.route(
    "/cancel-subscription/<int:subscription_id>",
    methods=["POST"]
)
@login_required
def cancel_subscription(subscription_id):

    conn = get_db()

    subscription = conn.execute("""
        SELECT * FROM subscriptions
        WHERE id = ? AND user_id = ?
    """, (
        subscription_id,
        session["user_id"]
    )).fetchone()

    if subscription is None:
        conn.close()
        flash("Subscription not found.", "danger")
        return redirect(url_for("my_subscriptions"))

    conn.execute("""
        UPDATE subscriptions
        SET status = 'Cancelled'
        WHERE id = ?
    """, (subscription_id,))

    conn.commit()
    conn.close()

    flash("Subscription cancelled.", "info")

    return redirect(url_for("my_subscriptions"))


# ==========================================
# SAVE DIET PREFERENCES
# ==========================================

@app.route("/diet-preferences", methods=["GET", "POST"])
@login_required
def diet_preferences():

    conn = get_db()

    if request.method == "POST":

        preference = request.form.get(
            "preference", "Vegetarian"
        )

        allergies = request.form.get(
            "allergies", ""
        ).strip()

        goal = request.form.get(
            "goal", "Healthy Eating"
        )

        conn.execute("""
            INSERT INTO diet_preferences
            (user_id, preference, allergies, goal)
            VALUES (?, ?, ?, ?)
        """, (
            session["user_id"],
            preference,
            allergies,
            goal
        ))

        conn.commit()

        flash("Diet preferences saved.", "success")

    preferences = conn.execute("""
        SELECT * FROM diet_preferences
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "diet_preferences.html",
        preferences=preferences
    )


# ==========================================
# ADD FOOD REVIEW
# ==========================================

@app.route(
    "/review/<int:food_id>",
    methods=["POST"]
)
@login_required
def add_review(food_id):

    try:
        rating = int(request.form.get("rating", "5"))
    except ValueError:
        rating = 0

    comment = request.form.get(
        "comment", ""
    ).strip()

    if rating < 1 or rating > 5:
        flash("Rating must be between 1 and 5.", "danger")
        return redirect(url_for("food_details", food_id=food_id))

    conn = get_db()

    food = conn.execute("""
        SELECT id FROM foods WHERE id = ?
    """, (food_id,)).fetchone()

    if food is None:
        conn.close()
        flash("Food not found.", "danger")
        return redirect(url_for("menu"))

    conn.execute("""
        INSERT INTO reviews
        (user_id, food_id, rating, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        food_id,
        rating,
        comment,
        datetime.now().isoformat()
    ))

    conn.commit()
    conn.close()

    flash("Review submitted.", "success")

    return redirect(
        url_for("food_details", food_id=food_id)
    )


# ==========================================
# CUSTOMER PROFILE
# ==========================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    conn = get_db()

    user = conn.execute("""
        SELECT id, name, email, phone, address
        FROM users WHERE id = ?
    """, (session["user_id"],)).fetchone()

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()

        if not name:
            conn.close()
            flash("Name is required.", "danger")
            return redirect(url_for("profile"))

        conn.execute("""
            UPDATE users
            SET name = ?, phone = ?, address = ?
            WHERE id = ?
        """, (
            name,
            phone,
            address,
            session["user_id"]
        ))

        conn.commit()

        session["name"] = name

        flash("Profile updated successfully.", "success")

        user = conn.execute("""
            SELECT id, name, email, phone, address
            FROM users WHERE id = ?
        """, (session["user_id"],)).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user
    )


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = get_db()

    total_users = conn.execute("""
        SELECT COUNT(*) FROM users
        WHERE role = 'customer'
    """).fetchone()[0]

    total_foods = conn.execute("""
        SELECT COUNT(*) FROM foods
    """).fetchone()[0]

    total_orders = conn.execute("""
        SELECT COUNT(*) FROM orders
    """).fetchone()[0]

    total_revenue = conn.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM orders
        WHERE status != 'Cancelled'
    """).fetchone()[0]

    recent_orders = conn.execute("""
        SELECT orders.*, users.name
        FROM orders
        JOIN users ON users.id = orders.user_id
        ORDER BY orders.id DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total_users=total_users,
        total_foods=total_foods,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_orders=recent_orders
    )


# ==========================================
# ADMIN: MANAGE FOODS
# ==========================================

@app.route("/admin/foods")
@admin_required
def admin_foods():

    conn = get_db()

    foods = conn.execute("""
        SELECT * FROM foods ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_foods.html",
        foods=foods
    )


# ==========================================
# ADMIN: ADD FOOD
# ==========================================

@app.route("/admin/add-food", methods=["GET", "POST"])
@admin_required
def add_food():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        description = request.form.get(
            "description", ""
        ).strip()

        category = request.form.get(
            "category", "Homemade"
        )

        try:
            price = float(request.form.get("price", "0"))
        except ValueError:
            price = 0

        image = request.form.get("image", "").strip()

        if not name or price <= 0:
            flash("Enter a valid name and price.", "danger")
            return redirect(url_for("add_food"))

        if category not in ["Homemade", "Diet", "Fitness"]:
            flash("Invalid category.", "danger")
            return redirect(url_for("add_food"))

        conn = get_db()

        conn.execute("""
            INSERT INTO foods
            (name, description, category, price, image, available)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (
            name,
            description,
            category,
            price,
            image
        ))

        conn.commit()
        conn.close()

        flash("Food added successfully.", "success")

        return redirect(url_for("admin_foods"))

    return render_template("add_food.html")


# ==========================================
# ADMIN: DELETE FOOD
# ==========================================

@app.route(
    "/admin/delete-food/<int:food_id>",
    methods=["POST"]
)
@admin_required
def delete_food(food_id):

    conn = get_db()

    conn.execute("""
        UPDATE foods
        SET available = 0
        WHERE id = ?
    """, (food_id,))

    conn.commit()
    conn.close()

    flash("Food item disabled.", "info")

    return redirect(url_for("admin_foods"))


# ==========================================
# ADMIN: VIEW ALL ORDERS
# ==========================================

@app.route("/admin/orders")
@admin_required
def admin_orders():

    conn = get_db()

    orders_list = conn.execute("""
        SELECT orders.*, users.name, users.email
        FROM orders
        JOIN users ON users.id = orders.user_id
        ORDER BY orders.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_orders.html",
        orders=orders_list
    )


# ==========================================
# ADMIN: UPDATE ORDER STATUS
# ==========================================

@app.route(
    "/admin/update-order/<int:order_id>",
    methods=["POST"]
)
@admin_required
def update_order(order_id):

    status = request.form.get("status", "")

    allowed_statuses = [
        "Pending",
        "Confirmed",
        "Preparing",
        "Out for Delivery",
        "Delivered",
        "Cancelled"
    ]

    if status not in allowed_statuses:
        flash("Invalid order status.", "danger")
        return redirect(url_for("admin_orders"))

    conn = get_db()

    conn.execute("""
        UPDATE orders
        SET status = ?
        WHERE id = ?
    """, (status, order_id))

    conn.commit()
    conn.close()

    flash("Order status updated.", "success")

    return redirect(url_for("admin_orders"))


# ==========================================
# ADMIN: VIEW SUBSCRIPTIONS
# ==========================================

@app.route("/admin/subscriptions")
@admin_required
def admin_subscriptions():

    conn = get_db()

    subscriptions = conn.execute("""
        SELECT subscriptions.*, users.name, users.email
        FROM subscriptions
        JOIN users ON users.id = subscriptions.user_id
        ORDER BY subscriptions.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_subscriptions.html",
        subscriptions=subscriptions
    )


# ==========================================
# ADMIN: CUSTOMERS
# ==========================================

@app.route("/admin/customers")
@admin_required
def admin_customers():

    conn = get_db()

    customers = conn.execute("""
        SELECT id, name, email, phone, created_at
        FROM users
        WHERE role = 'customer'
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin_customers.html",
        customers=customers
    )


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def page_not_found(error):

    return (
        render_template(
            "error.html",
            message="Page not found."
        ),
        404
    )


@app.errorhandler(500)
def internal_server_error(error):

    return (
        render_template(
            "error.html",
            message="Something went wrong."
        ),
        500
    )


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
