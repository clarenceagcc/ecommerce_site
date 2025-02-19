from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from extensions import db, login_manager 
from config import Config
from models import User, Product, Order 
from forms import LoginForm, RegistrationForm
from flask_login import login_required, current_user, logout_user, login_user
from seed import seed_database
import requests
import multiprocessing
import time

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)  # Load configuration from config.py

# Initialize extensions with the app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = form.password.data  # In production, hash the password
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.password == form.password.data:  # In production, compare hashed passwords
            login_user(user)
            return redirect(url_for('products'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/products')
@login_required
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    # Get the product
    product = Product.query.get_or_404(product_id)
    # Get the quantity from the form
    quantity = int(request.form.get('quantity', 1))
    if quantity <= 0:
        flash('Quantity must be greater than zero.', 'danger')
        return redirect(url_for('products'))

    # Check if the product is already in the cart
    order = Order.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if order:
        # Update the quantity if the product is already in the cart
        order.quantity += quantity
    else:
        # Add a new order entry
        order = Order(user_id=current_user.id, product_id=product.id, quantity=quantity)
        db.session.add(order)

    db.session.commit()
    flash(f'Added {quantity} of {product.name} to your cart!', 'success')
    return redirect(url_for('products'))

@app.route('/cart')
@login_required
def cart():
    # Get all orders for the current user
    orders = Order.query.filter_by(user_id=current_user.id).all()
    # Calculate the total price
    total_price = sum(order.product.price * order.quantity for order in orders)
    return render_template('cart.html', orders=orders, total_price=total_price)

@app.route('/remove_from_cart/<int:order_id>', methods=['POST'])
@login_required
def remove_from_cart(order_id):
    # Find the order by ID
    order = Order.query.get_or_404(order_id)
    # Ensure the order belongs to the current user
    if order.user_id != current_user.id:
        flash('You do not have permission to remove this item.', 'danger')
        return redirect(url_for('cart'))

    # Delete the order
    db.session.delete(order)
    db.session.commit()
    flash('Item removed from your cart.', 'success')
    return redirect(url_for('cart'))

@app.route('/admin')
@login_required
def admin():
    # Ensure only admins can access this page
    if current_user.username != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('home'))

    # Fetch all products
    products = Product.query.all()
    return render_template('admin.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    if current_user.username != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        image_path = request.form['image_path']

        product = Product(name=name, description=description, price=price, stock=stock, image_path=image_path)
        db.session.add(product)
        db.session.commit()

        flash('Product added successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('add_product.html')

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    if current_user.username != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('home'))

    product = Product.query.get_or_404(product_id)

    if request.method == 'POST':
        product.name = request.form['name']
        product.description = request.form['description']
        product.price = float(request.form['price'])
        product.stock = int(request.form['stock'])
        product.image_path = request.form['image_path']

        db.session.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin'))

    return render_template('edit_product.html', product=product)

@app.route('/admin/delete_product/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.username != 'admin':
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('home'))

    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()

    flash('Product deleted successfully!', 'success')
    return redirect(url_for('admin'))

@app.route('/checkout', methods=['GET'])
def checkout():
    return render_template('checkout.html')

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    card_name = request.form.get('card_name')
    card_number = request.form.get('card_number')
    expiry_date = request.form.get('expiry_date')
    cvv = request.form.get('cvv')

    if not (card_name and card_number and expiry_date and cvv):
        flash("All fields are required!", "danger")
        return redirect(url_for('checkout'))

    # Get cart items from session or database
    cart_items = Order.query.all()  # Fetch all cart items for the user

    # Check stock availability before proceeding
    for item in cart_items:
        if item.product.stock < item.quantity:
            flash(f"Not enough stock for {item.product.name}. Available: {item.product.stock}", "danger")
            return redirect(url_for('cart'))  # Redirect back to cart if stock is insufficient

    # Reduce stock for each product in the cart
    for item in cart_items:
        product = item.product
        product.stock -= item.quantity
        db.session.add(product)

    # Clear the cart after purchase
    Order.query.delete()  # Assuming CartItem stores the cart contents
    db.session.commit()

    flash("Payment successful! Your order has been placed.", "success")
    return redirect(url_for('home'))  # Redirect to homepage after purchase

# CPU Stress Test Function
def stress_cpu(duration):
    end_time = time.time() + duration
    while time.time() < end_time:
        _ = [x**2 for x in range(10000)]  # Heavy computation

# Network Stress Test Function
def stress_network(url, requests_count):
    for _ in range(requests_count):
        try:
            requests.get(url)
        except requests.exceptions.RequestException:
            pass  # Ignore failures

@app.route('/stress_test', methods=['POST'])
def stress_test():
    test_type = request.form.get('test_type')
    duration = int(request.form.get('duration', 10))  # Default 10 seconds

    if test_type == "cpu":
        process = multiprocessing.Process(target=stress_cpu, args=(duration,))
        process.start()
    elif test_type == "network":
        target_url = request.form.get('target_url', 'http://localhost:5000')  # Default URL
        requests_count = int(request.form.get('requests_count', 100))  # Default 100 requests
        process = multiprocessing.Process(target=stress_network, args=(target_url, requests_count))
        process.start()
    else:
        return jsonify({"error": "Invalid test type"}), 400

    return jsonify({"message": f"{test_type.capitalize()} stress test started!"})

# Fetch AWS instance metadata (IMPORTANT THAT THIS ONLY WORKS ON EC2!!!)
# AWS provides instance metadata via http://169.254.169.254
# Check https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html
def get_server_info():
    try:
        # First get IMDSv2 token
        token_response = requests.put(
            'http://169.254.169.254/latest/api/token',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
            timeout=1
        )
        token = token_response.text
        
        # Add token to headers for subsequent requests
        headers = {'X-aws-ec2-metadata-token': token}
        
        # Get private IP
        private_ip = requests.get(
            'http://169.254.169.254/latest/meta-data/local-ipv4',
            headers=headers,
            timeout=1
        ).text
        
        # Get availability zone
        availability_zone = requests.get(
            'http://169.254.169.254/latest/meta-data/placement/availability-zone',
            headers=headers,
            timeout=1
        ).text
        
        # Extract region from availability zone
        region = availability_zone[:-1]
        
        return {
            "ip": private_ip,
            "az": availability_zone,
            "region": region
        }
    except requests.exceptions.RequestException as e:
        # Log the specific error for debugging
        print(f"Metadata service error: {str(e)}")
        # Fallback for local testing
        return {
            "ip": "127.0.0.1",
            "az": "local",
            "region": "local"
        }
     
# Template Context Processor
@app.context_processor
def inject_server_info():
    return {"server": get_server_info()} 

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
        seed_database()  # Seed the database with default products
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True)