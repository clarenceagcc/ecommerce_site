from flask import Flask, render_template, redirect, url_for, flash, request
from extensions import db, login_manager 
from config import Config
from models import User, Product, Order 
from forms import LoginForm, RegistrationForm
from flask_login import login_required, current_user, logout_user, login_user
from seed import seed_database

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
        seed_database()  # Seed the database with default products
    app.run(debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True)