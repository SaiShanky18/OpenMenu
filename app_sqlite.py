import sqlite3
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = "restaurants.db"

app = Flask(__name__)

def get_restaurants_nearby(lat, lng, radius_km=2):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Simple haversine formula for proximity (for demo, not optimized)
    query = '''SELECT id, name, address, lat, lng, phone, website, rating, user_ratings_count, business_status FROM restaurants'''
    c.execute(query)
    results = []
    for row in c.fetchall():
        rid, name, address, rlat, rlng, phone, website, rating, user_ratings_count, business_status = row
        # Calculate distance (rough)
        from math import radians, cos, sin, asin, sqrt
        def haversine(lat1, lon1, lat2, lon2):
            # Earth radius in km
            R = 6371.0
            dlat = radians(lat2 - lat1)
            dlon = radians(lon2 - lon1)
            a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            return R * c
        dist = haversine(lat, lng, rlat, rlng)
        if dist <= radius_km:
            results.append({
                "id": rid,
                "name": name,
                "address": address,
                "lat": rlat,
                "lng": rlng,
                "phone": phone,
                "website": website,
                "rating": rating,
                "user_ratings_count": user_ratings_count,
                "business_status": business_status
            })
    conn.close()
    return results

def get_menu_items_for_restaurant(restaurant_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, description, price, calories, tags FROM menu_items WHERE restaurant_id=?', (restaurant_id,))
    items = []
    for row in c.fetchall():
        name, description, price, calories, tags = row
        items.append({
            "name": name,
            "description": description,
            "price": price,
            "calories": calories,
            "tags": json.loads(tags) if tags else []
        })
    conn.close()
    return items

@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.json
    user_query = data.get('query', '')
    location = data.get('location', None)
    lat = location.get('lat') if location else None
    lng = location.get('lng') if location else None
    if lat is None or lng is None:
        return jsonify({"error": "Location required"}), 400
    nearby_restaurants = get_restaurants_nearby(lat, lng)
    all_menu_items = []
    for rest in nearby_restaurants:
        menu_items = get_menu_items_for_restaurant(rest['id'])
        for item in menu_items:
            item['restaurant'] = rest
            all_menu_items.append(item)
    # Use Gemini for semantic search
    prompt = (
        f"You are a food recommendation engine. Given the following user request, recommend the top 10 dishes from the menu items below. "
        f"Only return dishes that best match the user's request. For each dish, return its name, description, tags, and all data about the restaurant (as restaurant).\n\n"
        f"User request: {user_query}\n\n"
        f"Menu items: {json.dumps(all_menu_items)}\n\n"
        f"If many dishes match, randomize the top 10 each time so users get new recommendations. "
        f"Return a JSON array of the top 10 recommended dishes, each including all restaurant data."
    )
    messages = [
        {"role": "user", "content": prompt}
    ]
    response = completion(
        model="gemini/gemini-2.5-pro",
        api_key=GEMINI_API_KEY,
        messages=messages,
        response_format={"type": "json_object"}
    )
    try:
        recommendations = json.loads(response.choices[0].message.content)
    except Exception as e:
        print("Error parsing Gemini response:", e)
        recommendations = []
    return jsonify({"recommendations": recommendations})

if __name__ == '__main__':
    app.run(debug=True)
