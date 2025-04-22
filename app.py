# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.security import generate_password_hash as _generate_password_hash
from werkzeug.security import check_password_hash as _check_password_hash
import hashlib
# Custom password hash generator compatible with Python 3.13
def generate_password_hash(password, method='pbkdf2:sha256', salt_length=16):
    # Ensure we're always using pbkdf2:sha256 which is supported in Python 3.13
    # The scrypt method is no longer supported in Python 3.13
    return _generate_password_hash(password, method='pbkdf2:sha256', salt_length=salt_length)
from werkzeug.utils import secure_filename
import os
from datetime import datetime
# from flask_ngrok import run_with_ngrok

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mandibhavv_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mandibhavv.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# run_with_ngrok(app)
# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class State(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    cities = db.relationship('City', backref='state', lazy=True)

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    state_id = db.Column(db.Integer, db.ForeignKey('state.id'), nullable=False)
    markets = db.relationship('Market', backref='city', lazy=True)

class Market(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city_id = db.Column(db.Integer, db.ForeignKey('city.id'), nullable=False)
    produce_listings = db.relationship('ProduceListing', backref='market', lazy=True)

class ProduceType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(20), nullable=False)  # vegetable or fruit
    listings = db.relationship('ProduceListing', backref='produce_type', lazy=True)

class ProduceListing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('market.id'), nullable=False)
    produce_id = db.Column(db.Integer, db.ForeignKey('produce_type.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False, default='kg')
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class NewsUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Advertisement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200), nullable=False)
    link_url = db.Column(db.String(255), nullable=True)
    position = db.Column(db.String(50), default='homepage')  # homepage, sidebar, etc
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Helper functions - UNIFIED VERSIONS
def get_states():
    return State.query.all()

def get_cities(state_id):
    cities = City.query.filter_by(state_id=state_id).all()
    # Sort cities alphabetically by name
    cities.sort(key=lambda c: c.name)
    return cities

def get_markets(city_id):
    markets = Market.query.filter_by(city_id=city_id).all()
    # Sort markets alphabetically by name
    markets.sort(key=lambda m: m.name)
    return markets



def get_produce_listings(market_id=None, search_term=None):
    query = ProduceListing.query.join(ProduceType)
    
    if market_id:
        query = query.filter(ProduceListing.market_id == market_id)
    
    if search_term:
        query = query.filter(ProduceType.name.ilike(f'%{search_term}%'))
    
    return query.all()

def check_password_hash(pwhash, password):
    try:
        return _check_password_hash(pwhash, password)
    except ValueError:
        # Log the error (for debugging)
        print(f"Error with hash format: {pwhash}")
        return False
# Routes
@app.route('/')
def index():
    states = get_states()
    default_state = State.query.filter_by(name='Rajasthan').first()
    
    state_id = request.args.get('state_id', default_state.id if default_state else None, type=int)
    city_id = request.args.get('city_id', None, type=int)
    market_id = request.args.get('market_id', None, type=int)
    search_term = request.args.get('search', None)
    
    cities = get_cities(state_id) if state_id else []
    markets = get_markets(city_id) if city_id else []
    
    news_updates = NewsUpdate.query.filter_by(is_active=True).order_by(NewsUpdate.date_posted.desc()).limit(3).all()
    
    listings = get_produce_listings(market_id, search_term) if market_id else []
    homepage_ads = Advertisement.query.filter(
        Advertisement.is_active == True,
        Advertisement.position == 'homepage',
        (Advertisement.end_date == None) | (Advertisement.end_date >= datetime.utcnow())
    ).all()
    
    return render_template('index.html', 
                          states=states, 
                          cities=cities, 
                          markets=markets,
                          selected_state=state_id,
                          selected_city=city_id,
                          selected_market=market_id,
                          search_term=search_term,
                          listings=listings,
                          news_updates=news_updates,
                          homepage_ads=homepage_ads)

@app.route('/get_cities/<int:state_id>')
def get_cities_api(state_id):
    cities = get_cities(state_id)
    return {'cities': [{'id': city.id, 'name': city.name} for city in cities]}

@app.route('/get_markets/<int:city_id>')
def get_markets_api(city_id):
    markets = get_markets(city_id)
    return {'markets': [{'id': market.id, 'name': market.name} for market in markets]}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/work-with-us')
def work_with_us():
    return render_template('workwithus.html')

@app.route('/krishi-help')
def krishi_help():
    return render_template('krishihelp.html')

@app.route('/news')
def all_news():
    news_updates = NewsUpdate.query.filter_by(is_active=True).order_by(NewsUpdate.date_posted.desc()).all()
    return render_template('news.html', news_updates=news_updates)


@app.route('/admin')
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    markets = Market.query.all()
    produce_types = ProduceType.query.all()
    # Pass the City model to the template
    cities = City.query.all()
    states = State.query.all()
    news_updates = NewsUpdate.query.order_by(NewsUpdate.date_posted.desc()).all()
    
    return render_template('admin/dashboard.html', 
                          markets=markets, 
                          produce_types=produce_types,
                          cities=cities,
                          states=states,
                          news_updates=news_updates)

@app.route('/admin/update_price', methods=['POST'])
@login_required
def update_price():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    market_id = request.form.get('market_id', type=int)
    produce_id = request.form.get('produce_id', type=int)
    price = request.form.get('price', type=float)
    
    listing = ProduceListing.query.filter_by(market_id=market_id, produce_id=produce_id).first()
    
    if listing:
        listing.price = price
        listing.last_updated = datetime.utcnow()
    else:
        new_listing = ProduceListing(
            market_id=market_id,
            produce_id=produce_id,
            price=price
        )
        db.session.add(new_listing)
    
    db.session.commit()
    flash('Price updated successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_produce', methods=['POST'])
@login_required
def add_produce():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    category = request.form.get('category')
    
    if 'image' not in request.files:
        flash('No image file')
        return redirect(url_for('admin_dashboard'))
    
    file = request.files['image']
    
    if file.filename == '':
        flash('No selected image file')
        return redirect(url_for('admin_dashboard'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        new_produce = ProduceType(
            name=name,
            image=filename,
            category=category
        )
        
        db.session.add(new_produce)
        db.session.commit()
        
        flash('New produce added successfully')
    else:
        flash('Invalid file format')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_market', methods=['POST'])
@login_required
def add_market():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    city_id = request.form.get('city_id', type=int)
    
    new_market = Market(name=name, city_id=city_id)
    db.session.add(new_market)
    db.session.commit()
    
    flash('New market added successfully')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add_state', methods=['POST'])
@login_required
def add_state():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    
    new_state = State(name=name)
    db.session.add(new_state)
    db.session.commit()
    
    flash('New state added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/add_city', methods=['POST'])
@login_required
def add_city():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    name = request.form.get('name')
    state_id = request.form.get('state_id', type=int)
    
    new_city = City(name=name, state_id=state_id)
    db.session.add(new_city)
    db.session.commit()
    
    flash('New city added successfully')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add_news', methods=['POST'])
@login_required
def admin_add_news():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    title = request.form.get('title')
    content = request.form.get('content')
    
    new_update = NewsUpdate(
        title=title,
        content=content
    )
    
    db.session.add(new_update)
    db.session.commit()
    
    flash('News update added successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_news/<int:news_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_news(news_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    news_item = NewsUpdate.query.get_or_404(news_id)
    
    if request.method == 'POST':
        news_item.title = request.form.get('title')
        news_item.content = request.form.get('content')
        db.session.commit()
        
        flash('News update edited successfully')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_news.html', news=news_item)

@app.route('/admin/toggle_news/<int:news_id>', methods=['POST'])
@login_required
def admin_toggle_news(news_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    news_item = NewsUpdate.query.get_or_404(news_id)
    news_item.is_active = not news_item.is_active
    db.session.commit()
    
    status = "activated" if news_item.is_active else "deactivated"
    flash(f'News update {status} successfully')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/delete_state/<int:state_id>', methods=['POST'])
@login_required
def delete_state(state_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Check if state has associated cities
    state = State.query.get_or_404(state_id)
    if state.cities:
        flash('Cannot delete state: Please delete all associated cities first')
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(state)
    db.session.commit()
    
    flash('State deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_city/<int:city_id>', methods=['POST'])
@login_required
def delete_city(city_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Check if city has associated markets
    city = City.query.get_or_404(city_id)
    if city.markets:
        flash('Cannot delete city: Please delete all associated markets first')
        return redirect(url_for('admin_dashboard'))
    
    db.session.delete(city)
    db.session.commit()
    
    flash('City deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_market/<int:market_id>', methods=['POST'])
@login_required
def delete_market(market_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Check if market has associated produce listings
    market = Market.query.get_or_404(market_id)
    if market.produce_listings:
        # Delete associated produce listings first
        for listing in market.produce_listings:
            db.session.delete(listing)
    
    db.session.delete(market)
    db.session.commit()
    
    flash('Market deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_produce/<int:produce_id>', methods=['POST'])
@login_required
def delete_produce(produce_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    # Check if produce has associated listings
    produce = ProduceType.query.get_or_404(produce_id)
    if produce.listings:
        # Delete associated listings first
        for listing in produce.listings:
            db.session.delete(listing)
    
    # Delete produce image file if exists
    if produce.image and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], produce.image)):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], produce.image))
    
    db.session.delete(produce)
    db.session.commit()
    
    flash('Produce deleted successfully')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/edit_produce/<int:produce_id>', methods=['GET', 'POST'])
@login_required
def edit_produce(produce_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    produce = ProduceType.query.get_or_404(produce_id)
    
    if request.method == 'POST':
        produce.name = request.form.get('name')
        produce.category = request.form.get('category')
        
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Delete old image if exists
                if produce.image and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], produce.image)):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], produce.image))
                
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                produce.image = filename
        
        db.session.commit()
        flash('Produce updated successfully')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_produce.html', produce=produce)

@app.route('/admin/delete_listing/<int:market_id>/<int:produce_id>', methods=['POST'])
@login_required
def delete_listing(market_id, produce_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    listing = ProduceListing.query.filter_by(market_id=market_id, produce_id=produce_id).first_or_404()
    db.session.delete(listing)
    db.session.commit()
    
    flash('Produce listing deleted from market successfully')
    return redirect(url_for('admin_dashboard'))


@app.route('/api/price_listings')
@login_required
def api_price_listings():
    market_id = request.args.get('market_id', type=int)
    produce_id = request.args.get('produce_id', type=int)
    
    query = ProduceListing.query.join(Market).join(ProduceType)
    
    if market_id:
        query = query.filter(ProduceListing.market_id == market_id)
    
    if produce_id:
        query = query.filter(ProduceListing.produce_id == produce_id)
    
    listings = query.all()
    result = []
    
    for listing in listings:
        result.append({
            'market_id': listing.market_id,
            'market_name': listing.market.name,
            'produce_id': listing.produce_id,
            'produce_name': listing.produce_type.name,
            'price': listing.price,
            'last_updated': listing.last_updated.isoformat()
        })
    
    return jsonify({'listings': result})


#ad section 

@app.route('/admin/ads')
@login_required
def admin_ads():
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('index'))
    
    ads = Advertisement.query.order_by(Advertisement.date_created.desc()).all()
    return render_template('admin/ads.html', ads=ads)

@app.route('/admin/add_ad', methods=['POST'])
@login_required
def admin_add_ad():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    title = request.form.get('title')
    link_url = request.form.get('link_url')
    position = request.form.get('position', 'homepage')
    
    if 'image' not in request.files:
        flash('No image file')
        return redirect(url_for('admin_ads'))
    
    file = request.files['image']
    
    if file.filename == '':
        flash('No selected image file')
        return redirect(url_for('admin_ads'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Handle dates
        start_date = datetime.utcnow()
        end_date_str = request.form.get('end_date')
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            except ValueError:
                pass
        
        new_ad = Advertisement(
            title=title,
            image=filename,
            link_url=link_url,
            position=position,
            start_date=start_date,
            end_date=end_date
        )
        
        db.session.add(new_ad)
        db.session.commit()
        
        flash('New advertisement added successfully')
    else:
        flash('Invalid file format')
    
    return redirect(url_for('admin_ads'))

@app.route('/admin/toggle_ad/<int:ad_id>', methods=['POST'])
@login_required
def admin_toggle_ad(ad_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    ad = Advertisement.query.get_or_404(ad_id)
    ad.is_active = not ad.is_active
    db.session.commit()
    
    status = "activated" if ad.is_active else "deactivated"
    flash(f'Advertisement {status} successfully')
    return redirect(url_for('admin_ads'))

@app.route('/admin/delete_ad/<int:ad_id>', methods=['POST'])
@login_required
def admin_delete_ad(ad_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    ad = Advertisement.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    
    flash('Advertisement deleted successfully')
    return redirect(url_for('admin_ads'))


# Initialize the database with some sample data
@app.cli.command('init-db')
def init_db_command():
    db.create_all()
    
    # Check if we already have data
    if User.query.count() > 0:
        return
    
    # Create admin user
   # In your init_db_command function
    admin = User(
        username='admin',
        password=generate_password_hash('mandibhavv123', method='sha256'),  # Changed from pbkdf2:sha256
        is_admin=True
    )
    db.session.add(admin)
    
    sample_news = [
        {
            'title': 'MandiBhavv Launch',
            'content': 'We are excited to announce the launch of MandiBhavv, your source for real-time agricultural market prices across Rajasthan!'
        },
        {
            'title': 'New Markets Added',
            'content': 'We have added 5 new markets in Jaipur region. Now get price updates from Muhana, Lal Kothi, and more mandis.'
        },
        {
            'title': 'Seasonal Price Report: Onions',
            'content': 'Our latest analysis shows onion prices are expected to stabilize in the coming weeks as new crop arrives in the markets.'
        }
    ]
    
    for news in sample_news:
        update = NewsUpdate(title=news['title'], content=news['content'])
        db.session.add(update)
    
    # Add sample ads
    sample_ads = [
        {
            'title': 'Farming Equipment Sale',
            'image': '/static/images/hero.png',
            'link_url': 'https://example.com/farm-equipment',
            'position': 'homepage'
        },
        {
            'title': 'Organic Fertilizers',
            'image': '/static/images/hero.png',
            'link_url': 'https://example.com/fertilizers',
            'position': 'homepage'
        }
    ]
    
    for ad_data in sample_ads:
        ad = Advertisement(
            title=ad_data['title'],
            image=ad_data['image'],
            link_url=ad_data['link_url'],
            position=ad_data['position']
        )
        db.session.add(ad)
    
    db.session.commit()

    # Add states
    rajasthan = State(name='Rajasthan')
    db.session.add(rajasthan)
    db.session.commit()
    
    # Add cities in Rajasthan
    cities = ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Ajmer', 'Bikaner']
    for city_name in cities:
        city = City(name=city_name, state_id=rajasthan.id)
        db.session.add(city)
    db.session.commit()
    
    # Add markets
    markets = {
        'Jaipur': ['Muhana Mandi', 'Lal Kothi Mandi', 'Chomu Mandi'],
        'Jodhpur': ['Jodhpur Mandi', 'Phalodi Mandi'],
        'Udaipur': ['Udaipur Mandi', 'Fatehsagar Mandi'],
        'Kota': ['Kota Mandi', 'Baran Mandi'],
        'Ajmer': ['Ajmer Mandi', 'Beawar Mandi'],
        'Bikaner': ['Bikaner Mandi', 'Nohar Mandi']
    }
    
    for city_name, market_names in markets.items():
        city = City.query.filter_by(name=city_name).first()
        for market_name in market_names:
            market = Market(name=market_name, city_id=city.id)
            db.session.add(market)
    db.session.commit()
    
    # Add produce types
    vegetables = [
        {'name': 'Tomato', 'category': 'vegetable', 'image': 'tomato.jpg'},
        {'name': 'Potato', 'category': 'vegetable', 'image': 'potato.jpg'},
        {'name': 'Onion', 'category': 'vegetable', 'image': 'onion.jpg'},
        {'name': 'Cauliflower', 'category': 'vegetable', 'image': 'cauliflower.jpg'},
        {'name': 'Carrot', 'category': 'vegetable', 'image': 'carrot.jpg'},
        {'name': 'Lady Finger', 'category': 'vegetable', 'image': 'ladyfinger.jpg'},
        {'name': 'Brinjal', 'category': 'vegetable', 'image': 'brinjal.jpg'},
        {'name': 'Cabbage', 'category': 'vegetable', 'image': 'cabbage.jpg'}
    ]
    
    fruits = [
        {'name': 'Apple', 'category': 'fruit', 'image': 'apple.jpg'},
        {'name': 'Banana', 'category': 'fruit', 'image': 'banana.jpg'},
        {'name': 'Orange', 'category': 'fruit', 'image': 'orange.jpg'},
        {'name': 'Mango', 'category': 'fruit', 'image': 'mango.jpg'},
        {'name': 'Papaya', 'category': 'fruit', 'image': 'papaya.jpg'},
        {'name': 'Watermelon', 'category': 'fruit', 'image': 'watermelon.jpg'}
    ]
    
    for veg in vegetables:
        produce = ProduceType(name=veg['name'], category=veg['category'], image=veg['image'])
        db.session.add(produce)
    
    for fruit in fruits:
        produce = ProduceType(name=fruit['name'], category=fruit['category'], image=fruit['image'])
        db.session.add(produce)
    
    db.session.commit()


    # Add sample prices
    all_markets = Market.query.all()
    all_produce = ProduceType.query.all()
    
    import random
    for market in all_markets:
        for produce in all_produce:
            # Generate random price between 20 and 100
            price = round(random.uniform(20, 100), 2)
            listing = ProduceListing(
                market_id=market.id,
                produce_id=produce.id,
                price=price,
                unit='kg'
            )
            db.session.add(listing)
    
    db.session.commit()
    print('Database initialized with sample data!')

if __name__ == '__main__':
    app.run()
    # app.run(debug=True)