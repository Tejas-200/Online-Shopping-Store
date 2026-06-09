from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app import db
from app.models import User, Product, Cart, WalletTransaction, Order, OrderItem 
from decimal import Decimal

auth_bp = Blueprint('auth', __name__)

from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("You must be logged in to view that resource.", "error")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function



@auth_bp.route('/')
def home():
    search_query = request.args.get('search', '').strip()
    
    if search_query:
        # Case-insensitive partial matching search using SQLAlchemy ILIKE
        products = Product.query.filter(Product.name.ilike(f"%{search_query}%"), Product.is_active == True).all()
    else:
        products = Product.query.filter_by(is_active=True).all()
        
    return render_template('home.html', products=products, search_query=search_query)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        email = request.form.get('email').strip()
        password = request.form.get('password')

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or Email already registered.', 'error')
            return redirect(url_for('auth.register'))

        # Create new user instance
        new_user = User(username=username, email=email)
        new_user.set_password(password) # Hashes the password securely

        # Save to Neon Database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')

        # Find user by email
        user = User.query.filter_by(email=email).first()

        # Check if user exists and password hash matches
        if user and user.check_password(password):
            # Store session variables
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('auth.home'))
        else:
            flash('Invalid email or password.', 'error')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    # Clear the session dictionary entirely
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.home'))




# --- WALLET CONTROLLERS ---
@auth_bp.route('/wallet')
@login_required

def wallet_dashboard():
    if not session.get('user_id'):
        flash("Please log in to view your wallet.", "error")
        return redirect(url_for('auth.login'))
    return render_template('wallet.html')

@auth_bp.route('/wallet/add', methods=['POST'])
@login_required
def add_money():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    # FIX HERE: Convert the incoming string to a Decimal instead of a float
    amount = Decimal(request.form.get('amount', '0'))
    
    user = User.query.get(session['user_id'])
    
    # This will now work perfectly because Decimal += Decimal is supported!
    user.wallet_balance += amount
    
    # Log transaction
    txn = WalletTransaction(
        user_id=user.id, 
        amount=amount, 
        type='credit', 
        description=f"Loaded fake funds via dashboard"
    )
    db.session.add(txn)
    db.session.commit()
    
    flash(f"Successfully minted ₹{amount:,.2f} of completely fake monopoly money!", "success")
    return redirect(url_for('auth.wallet_dashboard'))


# --- SHOPPING CART CONTROLLERS ---
@auth_bp.route('/cart')
@login_required
def view_cart():
    if not session.get('user_id'):
        flash("Please log in to view your cart.", "error")
        return redirect(url_for('auth.login'))
    
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    cart_total = sum(item.product.price * item.quantity for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, cart_total=cart_total)

@auth_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    if not session.get('user_id'):
        flash("You must be logged in to add items to the cart.", "error")
        return redirect(url_for('auth.login'))
    
    # Check if item is already in user's cart
    existing_item = Cart.query.filter_by(user_id=session['user_id'], product_id=product_id).first()
    
    if existing_item:
        existing_item.quantity += 1
    else:
        new_cart_item = Cart(user_id=session['user_id'], product_id=product_id, quantity=1)
        db.session.add(new_cart_item)
        
    db.session.commit()
    flash("Item packed into your parody cart!", "success")
    return redirect(url_for('auth.home'))

@auth_bp.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
        
    item = Cart.query.filter_by(id=cart_id, user_id=session['user_id']).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        flash("Item removed from cart.", "success")
        
    return redirect(url_for('auth.view_cart'))



@auth_bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    # 1. Fetch user's cart items
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    if not cart_items:
        flash("Your cart is empty!", "error")
        return redirect(url_for('auth.home'))
        
    cart_total = sum(item.product.price * item.quantity for item in cart_items)

    try:
        # 2. Open an explicit atomic database transaction block using pessimistic row locking
        # This prevents race conditions or double spending.
        user = User.query.with_for_update().get(user_id)
        
        # 3. Guard Clause: Verify balance
        if user.wallet_balance < cart_total:
            flash(f"Transaction Rejected: Insufficient Fake Funds. You need ₹{cart_total - user.wallet_balance:,.2f} more play money.", "error")
            return redirect(url_for('auth.view_cart'))
            
        # 4. Deduct the fake balance
        user.wallet_balance -= cart_total
        
        # 5. Create main order record
        new_order = Order(user_id=user_id, total_amount=cart_total, status='Completed')
        db.session.add(new_order)
        db.session.flush() # Flushes order to database to populate new_order.id ahead of commit
        
        # 6. Transfer items from cart table to permanent order_items table
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price_at_time=item.product.price
            )
            db.session.add(order_item)
            # Clear the item out of the cart table
            db.session.delete(item)
            
        # 7. Log the wallet debit audit transaction
        txn = WalletTransaction(
            user_id=user_id, 
            amount=-cart_total, # negative indicates deduction
            type='debit', 
            description=f"Purchased simulated items from order #PM-{new_order.id}"
        )
        db.session.add(txn)
        
        # 8. Commit everything permanently to Neon
        db.session.commit()
        
        flash("🎉 Success! Your transaction went through perfectly. Your items are absolutely not on their way!", "success")
        return redirect(url_for('auth.view_orders'))
        
    except Exception as e:
        db.session.rollback() # Safely undo changes if anything crashes mid-flight
        flash("An internal database error occurred during checkout. Transaction safely rolled back.", "error")
        return redirect(url_for('auth.view_cart'))

@auth_bp.route('/orders')
@login_required
def view_orders():
    if not session.get('user_id'):
        flash("Please log in to view your order history.", "error")
        return redirect(url_for('auth.login'))
        
    # Query user's orders sorted by newest first
    orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=orders)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email').strip()
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a secure random token string
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            db.session.commit()
            
            # Print link directly to your server console instead of sending real email
            print(f"\n🔑 PASSWORD RESET SYSTEM SIMULATION:")
            print(f"Click here to reset for {email}: http://127.0.0.1:5000/reset-password/{token}\n")
            
            flash("Simulation Success: A recovery token has been printed straight to your backend server console logs!", "success")
        else:
            flash("Email address not discovered.", "error")
            
    return render_template('forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first_or_404()
    
    if request.method == 'POST':
        new_password = request.form.get('password')
        user.set_password(new_password)
        user.reset_token = None # Burn token after single use
        db.session.commit()
        
        flash("Password successfully changed! Please log in.", "success")
        return redirect(url_for('auth.login'))
        
    return render_template('reset_password.html', token=token)

