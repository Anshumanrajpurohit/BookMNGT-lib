# (Special request routes moved below all imports and app initialization)
# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from db_config import get_db_connection
from datetime import datetime
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps


def _ensure_cart_session() -> dict:
    """Guarantee cart exists in the session and return it."""
    cart = session.get('cart')
    if not isinstance(cart, dict):
        cart = {}
        session['cart'] = cart
    return cart


def _notify_order_status_changes(user_id: int) -> None:
    """Flash notifications for orders whose status changed since last login."""
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            '''
            SELECT o.id, o.status, o.total, GROUP_CONCAT(b.title SEPARATOR ', ') AS books
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN books b ON b.id = oi.book_id
            WHERE o.user_id = %s AND o.status IN ('Approved', 'Rejected') AND o.status_notified = 0
            GROUP BY o.id, o.status, o.total
            ORDER BY o.id DESC
            ''',
            (user_id,)
        )
        updates = cursor.fetchall()
        order_ids = [row['id'] for row in updates]

        for row in updates:
            status = row['status']
            books = row['books'] or 'N/A'
            total = row['total']
            if status == 'Approved':
                flash(f"Your Order (Order ID: {row['id']}) has been completed successfully. Books: {books}. Total Amount: ${total}", 'success')
            else:
                flash(f"Your Order (Order ID: {row['id']}) has been rejected. Books: {books}. Total Amount: ${total}", 'danger')

        if order_ids:
            placeholders = ','.join(['%s'] * len(order_ids))
            cursor.execute(
                f"UPDATE orders SET status_notified = 1 WHERE id IN ({placeholders})",
                tuple(order_ids)
            )
            db.commit()

    except Exception as e:
        logging.error(f"Notification check failed: {e}")
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


app = Flask(__name__)
import os
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_default_secret')

logging.basicConfig(level=logging.INFO)


# ---------------- AUTH HELPERS ----------------
def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('user_role') != role:
                flash('Unauthorized access', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_pw = generate_password_hash(password)
        try:
            db = get_db_connection()
            cursor = db.cursor()
            # Only allow first user to be admin, others are users
            cursor.execute('SELECT COUNT(*) AS user_count FROM users')
            user_row = cursor.fetchone()
            user_count = user_row['user_count'] if user_row else 0
            role = 'admin' if user_count == 0 else 'user'
            cursor.execute('INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)',
                           (name, email, hashed_pw, role))
            db.commit()
            cursor.close()
            db.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Register error: {e}")
            flash('Registration failed. Email may already be used.', 'danger')
            return render_template('register.html')
    return render_template('register.html')

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.close()
            db.close()
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['user_role'] = user['role']
                flash('Login successful!', 'success')
                if user['role'] == 'admin':
                    return redirect(url_for('admin'))
                else:
                    _notify_order_status_changes(user['id'])
                    return redirect(url_for('index'))
            else:
                flash('Invalid credentials', 'danger')
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('Login failed.', 'danger')
    return render_template('login.html')

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))
@app.route('/')
def index():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM books ORDER BY id')
        books = cursor.fetchall()   # ✅ DictRow list
        cursor.close()
        db.close()
        return render_template('index.html', books=books)
    except Exception as e:
        logging.error(f"Index error: {e}")
        return f"ERROR: {e}", 500


# ---------------- SEARCH ----------------
@app.route('/search')
def search():
    query = request.args.get('q', '')
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'SELECT * FROM books WHERE title LIKE %s OR author LIKE %s',
            (f'%{query}%', f'%{query}%')
        )
        books = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('index.html', books=books, search=query)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return f"ERROR: {e}", 500


# ---------------- BOOK DETAILS ----------------
@app.route('/book/<int:book_id>')
def book_details(book_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM books WHERE id = %s', (book_id,))
        book = cursor.fetchone()
        cursor.close()
        db.close()

        if not book:
            flash('Book not found', 'danger')
            return redirect(url_for('index'))

        return render_template('book_details.html', book=book)
    except Exception as e:
        logging.error(f"Book details error: {e}")
        return f"ERROR: {e}", 500


# ---------------- CART ----------------
@app.route('/add_to_cart/<int:book_id>')
@login_required(role='user')
def add_to_cart(book_id):
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('SELECT id, title, price, stock FROM books WHERE id = %s', (book_id,))
        book = cursor.fetchone()

        if not book:
            flash('Book not found.', 'danger')
            return redirect(url_for('index'))

        if book['stock'] <= 0:
            flash('This book is currently out of stock.', 'warning')
            return redirect(url_for('index'))

        cart = _ensure_cart_session()
        key = str(book_id)
        item = cart.get(key, {
            'title': book['title'],
            'quantity': 0,
            'rate': float(book['price'])
        })
        item['title'] = book['title']
        item['rate'] = float(book['price'])
        item['quantity'] = item.get('quantity', 0) + 1
        item['subtotal'] = round(item['rate'] * item['quantity'], 2)
        cart[key] = item
        session['cart'] = cart
        session.modified = True
        flash(f"{book['title']} added to cart!", 'success')
        return redirect(url_for('index'))
    except Exception as e:
        logging.error(f"Add to cart error: {e}")
        flash('Unable to add book to cart.', 'danger')
        return redirect(url_for('index'))
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


@app.route('/cart')
@login_required(role='user')
def cart():
    cart_session = _ensure_cart_session()
    cart_items = []
    total = 0.0

    for book_id, item in cart_session.items():
        rate = float(item.get('rate', 0))
        quantity = int(item.get('quantity', 0))
        subtotal = round(rate * quantity, 2)
        total += subtotal
        cart_items.append({
            'id': book_id,
            'title': item.get('title', 'Book'),
            'quantity': quantity,
            'rate': rate,
            'subtotal': subtotal
        })

    return render_template('cart.html', cart_items=cart_items, total=round(total, 2))


# ---------------- PLACE ORDER ----------------
@app.route('/place_order', methods=['POST'])
@login_required(role='user')
def place_order():
    cart = _ensure_cart_session()

    if not cart:
        flash('Cart is empty.', 'warning')
        return redirect(url_for('cart'))

    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()

        total = 0.0
        validated_items = []

        for raw_book_id, item in cart.items():
            book_id = int(raw_book_id)
            quantity = int(item.get('quantity', 0))
            cursor.execute('SELECT title, price, stock FROM books WHERE id = %s', (book_id,))
            book = cursor.fetchone()
            if not book:
                raise ValueError('One of the books in your cart no longer exists.')
            if book['stock'] < quantity:
                raise ValueError(f"Not enough stock available for {book['title']}.")

            rate = float(book['price'])
            subtotal = round(rate * quantity, 2)
            total += subtotal
            validated_items.append({
                'book_id': book_id,
                'quantity': quantity,
                'rate': rate
            })

        total = round(total, 2)
        cursor.execute(
            'INSERT INTO orders (user_id, order_date, total, status, status_notified) VALUES (%s, %s, %s, %s, %s)',
            (session['user_id'], datetime.now(), total, 'Pending', 1)
        )
        order_id = cursor.lastrowid

        for item in validated_items:
            cursor.execute(
                'INSERT INTO order_items (order_id, book_id, quantity, unit_price) VALUES (%s, %s, %s, %s)',
                (order_id, item['book_id'], item['quantity'], item['rate'])
            )
            cursor.execute(
                'UPDATE books SET stock = stock - %s WHERE id = %s',
                (item['quantity'], item['book_id'])
            )

        db.commit()
        session.pop('cart', None)
        flash('Order placed successfully! Track it from the My Orders page.', 'success')
        return redirect(url_for('my_orders'))

    except ValueError as ve:
        if db:
            db.rollback()
        flash(str(ve), 'danger')
        return redirect(url_for('cart'))
    except Exception as e:
        logging.error(f"Place order error: {e}")
        if db:
            db.rollback()
        flash('Order failed. Please try again.', 'danger')
        return redirect(url_for('cart'))
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ---------------- PAYMENT + ORDERS (USER) ----------------
@app.route('/payment')
@login_required(role='user')
def payment():
    cart_session = _ensure_cart_session()
    if not cart_session:
        flash('Add at least one book to cart before proceeding to payment.', 'warning')
        return redirect(url_for('cart'))

    total = round(sum(float(item.get('rate', 0)) * int(item.get('quantity', 0)) for item in cart_session.values()), 2)
    return render_template('payment.html', total=total)


@app.route('/my-orders')
@login_required(role='user')
def my_orders():
    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            '''
            SELECT o.id, o.order_date, o.total, o.status,
                   GROUP_CONCAT(CONCAT(b.title, ' (x', oi.quantity, ')') SEPARATOR ', ') AS books
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            JOIN books b ON b.id = oi.book_id
            WHERE o.user_id = %s
            GROUP BY o.id, o.order_date, o.total, o.status
            ORDER BY o.id DESC
            ''',
            (session['user_id'],)
        )
        orders = cursor.fetchall()
        return render_template('my_orders.html', orders=orders)
    except Exception as e:
        logging.error(f"My orders error: {e}")
        return f"ERROR: {e}", 500
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ---------------- ADMIN ----------------
@app.route('/admin')
@login_required(role='admin')
def admin():
    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute('SELECT * FROM books')
        books = cursor.fetchall()

        cursor.execute(
            '''
            SELECT o.id, u.name, o.total, o.status,
                   GROUP_CONCAT(CONCAT(b.title, ' (x', oi.quantity, ')') SEPARATOR ', ') AS books
            FROM orders o
            JOIN users u ON o.user_id = u.id
            JOIN order_items oi ON oi.order_id = o.id
            JOIN books b ON b.id = oi.book_id
            GROUP BY o.id, u.name, o.total, o.status
            ORDER BY o.id DESC
            '''
        )
        orders = cursor.fetchall()

        cursor.close()
        db.close()
        return render_template('admin.html', books=books, orders=orders)

    except Exception as e:
        logging.error(f"Admin error: {e}")
        return f"ERROR: {e}", 500


# ---------------- ADMIN ORDERS ACTIONS ----------------
@app.route('/admin/orders/<int:order_id>/<string:action>', methods=['POST'])
@login_required(role='admin')
def update_order_status(order_id: int, action: str):
    status_map = {
        'approve': 'Approved',
        'reject': 'Rejected'
    }
    status = status_map.get(action.lower())
    if not status:
        flash('Invalid action.', 'danger')
        return redirect(url_for('admin'))

    db = None
    cursor = None
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'UPDATE orders SET status = %s, status_notified = 0 WHERE id = %s',
            (status, order_id)
        )
        if cursor.rowcount == 0:
            flash('Order not found.', 'warning')
        else:
            db.commit()
            flash(f'Order {order_id} set to {status}.', 'success' if status == 'Approved' else 'info')
        return redirect(url_for('admin'))
    except Exception as e:
        logging.error(f"Order status update error: {e}")
        if db:
            db.rollback()
        flash('Failed to update order status.', 'danger')
        return redirect(url_for('admin'))
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ---------------- ADMIN CRUD ----------------
@app.route('/admin/add_book', methods=['POST'])
@login_required(role='admin')
def add_book():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'INSERT INTO books (title, author, price, category, stock) VALUES (%s, %s, %s, %s, %s)',
            (
                request.form['title'],
                request.form['author'],
                request.form['price'],
                request.form['category'],
                request.form['stock']
            )
        )
        db.commit()
        cursor.close()
        db.close()
        flash('Book added', 'success')
    except Exception as e:
        logging.error(f"Add book error: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        flash('Add failed', 'danger')

    return redirect(url_for('admin'))


@app.route('/admin/update_book/<int:book_id>', methods=['POST'])
@login_required(role='admin')
def update_book(book_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            'UPDATE books SET title=%s, author=%s, price=%s, category=%s, stock=%s WHERE id=%s',
            (
                request.form['title'],
                request.form['author'],
                request.form['price'],
                request.form['category'],
                request.form['stock'],
                book_id
            )
        )
        db.commit()
        cursor.close()
        db.close()
        flash('Book updated', 'success')
    except Exception as e:
        logging.error(f"Update error: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        flash('Update failed', 'danger')

    return redirect(url_for('admin'))


@app.route('/admin/delete_book/<int:book_id>', methods=['POST'])
@login_required(role='admin')
def delete_book(book_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('DELETE FROM books WHERE id=%s', (book_id,))
        db.commit()
        cursor.close()
        db.close()
        flash('Book deleted', 'success')
    except Exception as e:
        logging.error(f"Delete error: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        flash('Delete failed', 'danger')

    return redirect(url_for('admin'))


# ---------------- SPECIAL REQUEST (USER) ----------------
@app.route('/request-book', methods=['GET', 'POST'])
@login_required(role='user')
def request_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        details = request.form.get('details')
        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO special_requests (user_id, title, author, details) VALUES (%s, %s, %s, %s)',
                (session['user_id'], title, author, details)
            )
            db.commit()
            cursor.close()
            db.close()
            flash('Request submitted!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            logging.error(f"Special request error: {e}")
            flash('Failed to submit request.', 'danger')
    return render_template('request_book.html')

# ---------------- SPECIAL REQUESTS (ADMIN PANEL) ----------------
@app.route('/special-requests')
@login_required(role='admin')
def special_requests():
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute(
            '''SELECT sr.*, u.name as user_name FROM special_requests sr JOIN users u ON sr.user_id = u.id ORDER BY sr.id DESC'''
        )
        requests = cursor.fetchall()
        cursor.close()
        db.close()
        return render_template('special_requests.html', requests=requests)
    except Exception as e:
        logging.error(f"Special requests error: {e}")
        return f"ERROR: {e}", 500

# Approve request: add book to store and mark as approved
@app.route('/special-requests/<int:req_id>/approve', methods=['POST'])
@login_required(role='admin')
def approve_special_request(req_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        # Get request details
        cursor.execute('SELECT * FROM special_requests WHERE id = %s', (req_id,))
        req = cursor.fetchone()
        if req and req['status'] == 'pending':
            # Add book to store
            cursor.execute('INSERT INTO books (title, author, category, stock, price) VALUES (%s, %s, %s, %s, %s)',
                (req['title'], req['author'], 'Special Demand', 1, 0))
            # Mark request as approved
            cursor.execute('UPDATE special_requests SET status = %s WHERE id = %s', ('approved', req_id))
            db.commit()
        cursor.close()
        db.close()
        flash('Request approved and book added!', 'success')
    except Exception as e:
        logging.error(f"Approve request error: {e}")
        flash('Failed to approve request.', 'danger')
    return redirect(url_for('special_requests'))

# Decline request
@app.route('/special-requests/<int:req_id>/decline', methods=['POST'])
@login_required(role='admin')
def decline_special_request(req_id):
    try:
        db = get_db_connection()
        cursor = db.cursor()
        cursor.execute('UPDATE special_requests SET status = %s WHERE id = %s', ('declined', req_id))
        db.commit()
        cursor.close()
        db.close()
        flash('Request declined.', 'info')
    except Exception as e:
        logging.error(f"Decline request error: {e}")
        flash('Failed to decline request.', 'danger')
    return redirect(url_for('special_requests'))


if __name__ == '__main__':
    app.run(debug=True)
