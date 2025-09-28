import os
import json
import sqlite3

DB_PATH = "restaurants.db"
JSON_PATH = "data\\restaurant_list\\restaurants_google_maps.json"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lat REAL,
    lng REAL,
    name TEXT,
    address TEXT,
    rating REAL,
    user_ratings_count INTEGER,
    opening_hours TEXT,
    photo_url TEXT,
    price_level INTEGER,
    phone TEXT,
    website TEXT,
    business_status TEXT,
    google_maps_url TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS menu_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER,
    name TEXT,
    description TEXT,
    price REAL,
    calories INTEGER,
    tags TEXT,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
)''')

# Load JSON and insert data
with open(JSON_PATH, encoding='utf-8') as f:
    restaurants = json.load(f)

for r in restaurants:
    c.execute('''INSERT INTO restaurants (lat, lng, name, address, rating, user_ratings_count, opening_hours, phone, website, photo_url, price_level, business_status, google_maps_url)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                (r.get('lat'), r.get('lng'), r.get('name'), r.get('address'), r.get('rating'), r.get('user_ratings_count'), json.dumps(r.get('opening_hours', [])), r.get('phone_number'), r.get('website'), json.dumps(r.get('photos', [])), r.get('price_level'), r.get('business_status'), r.get('google_maps_url')))
    restaurant_id = c.lastrowid
    for item in r.get('menu_items', []):
        c.execute('''INSERT INTO menu_items (restaurant_id, name, description, price, calories, tags)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (restaurant_id, item.get('name'), item.get('description'), item.get('price'), item.get('calories'), json.dumps(item.get('tags', []))))

conn.commit()
conn.close()
print("Database setup complete.")
