from extensions import db  # Import db from extensions.py
from models import Product  # Import the Product model

def seed_database():
    """
    Deletes all existing products and seeds the database with default products.
    """
    # Delete all existing products
    db.session.query(Product).delete()
    db.session.commit()

    # Add placeholder products
    products = [
        Product(name="Laptop", description="A high-performance laptop.", price=999.99, image_path="images/laptop.jpg", stock=25),
        Product(name="Smartphone", description="A sleek and modern smartphone.", price=699.99, image_path="images/smartphone.jpg", stock=25),
        Product(name="Headphones", description="Noise-cancelling headphones.", price=199.99, image_path="images/headphones.jpg", stock=25),
        Product(name="Keyboard", description="Mechanical gaming keyboard.", price=129.99, image_path="images/keyboard.jpg", stock=25),
    ]

    db.session.add_all(products)
    db.session.commit()
    print("Database reset and seeded with default products.")
