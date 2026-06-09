from app import create_app, db
from app.models import Product

app = create_app()

def seed_products():
    parody_items = [
        {
            "name": "Rickroll Premium Subscription",
            "price": 199.00,
            "description": "Never gonna give you up, never gonna let you down. We'll text you a hidden Rick Astley link once a week when you least expect it."
        },
        {
            "name": "Invisibility Cloak (Batteries Not Included)",
            "price": 4999.00,
            "description": "Completely transparent technology. You can't see it, neither can we. Shipped as an empty cardboard box to save shipping weight."
        },
        {
            "name": "Diploma in Useless Knowledge",
            "price": 9999.00,
            "description": "Become an overnight certified expert in nothing. PDF certificate generated instantly. Looks extremely prestigious on a wall, completely useless on a CV."
        },
        {
            "name": "Nuclear Energy Drink",
            "price": 299.00,
            "description": "Glow-in-the-dark sticker included. Formulated with 500% your daily dose of caffeine. May cause fictional superpowers or immediate naps."
        },
        {
            "name": "Student's Exam Motivation",
            "price": 49.00,
            "description": "Highly volatile. Lasts approximately 3 hours before dissolving into procrastination. Strictly no refunds if you open social media."
        },
        {
            "name": "ChatGPT's Unsolicited Opinion",
            "price": 5.00,
            "description": "We will ask an AI what it thinks about your life choices and send you a highly structured, bulleted response that sounds polite but hurts your feelings."
        },
        {
            "name": "Premium Authentic Potato NFT",
            "price": 12499.00,
            "description": "Own the hyper-link to a JPEG of an organic potato. You don't get the potato. You don't even get the rights to the picture. You just own the receipt. Pure status symbol."
        },
        {
            "name": "Genuinely Broken USB Cable",
            "price": 99.00,
            "description": "Tired of things working? This cable is guaranteed to fail from day one. Perfect for practicing your patience or making excuses to your boss."
        }
    ]

    print("🌱 Seeding parody products into Neon Database...")
    
    for item in parody_items:
        # Check if product already exists so we don't duplicate
        existing = Product.query.filter_by(name=item['name']).first()
        if not existing:
            # Generate a robot image using the product name as the unique seed
            img_url = f"https://robohash.org/{item['name'].replace(' ', '')}.png?size=300x300"
            
            p = Product(
                name=item['name'],
                price=item['price'],
                description=item['description'],
                image_url=img_url
            )
            db.session.add(p)
            
    db.session.commit()
    print("✨ Database successfully populated with comedy gold!")

if __name__ == "__main__":
    with app.app_context():
        # First make sure tables exist
        db.create_all()
        # Seed them
        seed_products()