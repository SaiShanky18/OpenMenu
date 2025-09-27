import sqlite3
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from litellm import completion
import re
import random
from math import radians, cos, sin, asin, sqrt

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
DB_PATH = "restaurants.db"

app = Flask(__name__)
CORS(app)

# Define comprehensive keyword mappings
SPICY_KEYWORDS = {
    "spicy", "hot", "jalapeno", "sriracha", "chili", "chipotle", 
    "buffalo", "cayenne", "habanero", "ghost", "pepper", "fiery",
    "zesty", "piquant", "wasabi", "horseradish", "gochujang",
    "harissa", "tabasco", "scotch bonnet", "thai chili"
}

VEGETARIAN_KEYWORDS = {
    "vegetarian", "veggie", "veg", "meatless", "plant-based",
    "paneer", "tofu", "tempeh", "seitan", "mushroom", "eggplant",
    "broccoli", "cauliflower", "spinach", "kale", "beans", "lentil",
    "chickpea", "quinoa", "falafel", "hummus", "vegetable", "salad"
}

VEGAN_KEYWORDS = {
    "vegan", "plant-based", "dairy-free", "non-dairy", "animal-free"
}

DRINK_KEYWORDS = {
    "drink", "beverage", "juice", "soda", "tea", "coffee", 
    "smoothie", "cocktail", "milkshake", "beer", "wine", 
    "alcohol", "lemonade", "water", "cola", "pepsi", "coke",
    "latte", "cappuccino", "espresso", "frappe", "mocktail",
    "refreshment", "thirst", "liquid"
}

# Mapping of ingredients/descriptions to tags
INGREDIENT_TAG_MAP = {
    # Spicy mappings
    "jalapeno": ["spicy"],
    "sriracha": ["spicy"],
    "chili": ["spicy"],
    "chipotle": ["spicy"],
    "buffalo": ["spicy"],
    "cayenne": ["spicy"],
    "habanero": ["spicy"],
    "ghost pepper": ["spicy"],
    "hot sauce": ["spicy"],
    "wasabi": ["spicy"],
    "gochujang": ["spicy"],
    
    # Vegetarian mappings
    "paneer": ["vegetarian"],
    "tofu": ["vegetarian", "vegan"],
    "tempeh": ["vegetarian", "vegan"],
    "mushroom": ["vegetarian"],
    "eggplant": ["vegetarian"],
    "broccoli": ["vegetarian"],
    "cauliflower": ["vegetarian"],
    "cheese": ["vegetarian"],
    "beans": ["vegetarian"],
    "lentil": ["vegetarian"],
    "chickpea": ["vegetarian"],
    "quinoa": ["vegetarian"],
    "falafel": ["vegetarian"],
    
    # Vegan mappings
    "plant-based": ["vegan", "vegetarian"],
    "dairy-free": ["vegan"],
    "almond milk": ["vegan"],
    "oat milk": ["vegan"],
    "soy milk": ["vegan"],
}

def haversine(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth in km"""
    R = 6371.0  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

def get_restaurants_nearby(lat=33.7770706, lng=-84.3902668, radius_km=10):
    """Get restaurants within radius of given coordinates"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = '''SELECT id, name, address, rating, user_ratings_count, 
               opening_hours, phone, website, photo_url, price_level, 
               business_status, google_maps_url, lat, lng FROM restaurants'''
    c.execute(query)
    
    results = []
    for row in c.fetchall():
        (rid, name, address, rating, user_ratings_count, opening_hours, 
         phone, website, photo_url, price_level, business_status, 
         google_maps_url, rlat, rlng) = row
        
        dist = haversine(lat, lng, rlat, rlng)
        if dist <= radius_km:
            results.append({
                "id": rid,
                "name": name,
                "address": address,
                "rating": rating,
                "user_ratings_count": user_ratings_count,
                "opening_hours": json.loads(opening_hours) if opening_hours else [],
                "phone": phone,
                "website": website,
                "photo_url": json.loads(photo_url) if photo_url else [],
                "price_level": price_level,
                "business_status": business_status,
                "google_maps_url": google_maps_url,
                "lat": rlat,
                "lng": rlng
            })
    conn.close()
    return results

def get_menu_items_for_restaurant(restaurant_id):
    """Get menu items for a specific restaurant"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, description, price, calories, tags FROM menu_items WHERE restaurant_id=?', 
              (restaurant_id,))
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

def expand_tags_from_content(name, description, existing_tags):
    """Expand tags based on item name and description"""
    content_lower = f"{name} {description}".lower()
    expanded_tags = set([tag.lower() for tag in existing_tags])
    
    # Check for ingredient matches and add corresponding tags
    for ingredient, tags in INGREDIENT_TAG_MAP.items():
        if ingredient in content_lower:
            for tag in tags:
                expanded_tags.add(tag)
    
    # Also check if drink-related words are in the content
    for drink_word in DRINK_KEYWORDS:
        if drink_word in content_lower:
            expanded_tags.add("drink")
            break
    
    return expanded_tags

def parse_query_requirements(query):
    """Parse the query to extract requirements"""
    query_lower = query.lower()
    
    requirements = {
        "spicy": False,
        "vegetarian": False,
        "vegan": False,
        "drinks": False,
        "other_keywords": []
    }
    
    # Check for spicy requirement
    if any(keyword in query_lower for keyword in SPICY_KEYWORDS):
        requirements["spicy"] = True
    
    # Check for vegetarian requirement
    if any(keyword in query_lower for keyword in VEGETARIAN_KEYWORDS):
        requirements["vegetarian"] = True
    
    # Check for vegan requirement (vegan implies vegetarian)
    if any(keyword in query_lower for keyword in VEGAN_KEYWORDS):
        requirements["vegan"] = True
        requirements["vegetarian"] = True  # Vegan is also vegetarian
    
    # Check if specifically asking for drinks (with fuzzy matching for typos)
    drink_patterns = [
        "drink", "beverage", "juice", "soda", "tea", "coffee", 
        "smoothie", "cocktail", "milkshake", "beer", "wine", 
        "alcohol", "lemonade", "water", "cola", "pepsi", "coke",
        "latte", "cappuccino", "espresso", "frappe", "mocktail",
        "refreshment", "thirst", "liquid",
        "refresh", "refreshing", "refresing", "refreshin",  # Common typos for refreshing
        "hydrat", "quench"  # Related concepts
    ]
    
    if any(pattern in query_lower for pattern in drink_patterns):
        requirements["drinks"] = True
    
    # Extract other significant keywords (3+ characters, not common words)
    common_words = {
        "and", "with", "the", "for", "something", "food", "dish", 
        "meal", "item", "want", "need", "like", "get", "find", "give",
        "looking", "would", "could", "please", "thanks", "can"
    }
    all_special_keywords = SPICY_KEYWORDS | VEGETARIAN_KEYWORDS | VEGAN_KEYWORDS | DRINK_KEYWORDS
    
    words = re.findall(r'\b\w{3,}\b', query_lower)
    for word in words:
        # Skip if it's a common word or already categorized
        if word not in common_words and word not in all_special_keywords:
            # Also skip words that are drink-related variations
            if not any(drink_word in word or word in drink_word for drink_word in drink_patterns):
                requirements["other_keywords"].append(word)
    
    return requirements

def item_matches_requirements(item, requirements):
    """Check if a menu item matches all requirements"""
    name = item.get('name', '').lower()
    description = item.get('description', '').lower()
    existing_tags = item.get('tags', [])
    
    # Expand tags based on content
    expanded_tags = expand_tags_from_content(item['name'], item['description'], existing_tags)
    
    # Check if item is a drink
    is_drink = "drink" in expanded_tags or any(
        drink_word in name or drink_word in description 
        for drink_word in DRINK_KEYWORDS
    )
    
    # Rule 1: Exclude drinks unless specifically requested
    if is_drink and not requirements["drinks"]:
        return False
    
    # Rule 2: If asking for drinks, only return drinks
    if requirements["drinks"] and not is_drink:
        return False
    
    # Rule 3: Check spicy requirement (AND condition)
    if requirements["spicy"]:
        has_spicy = "spicy" in expanded_tags or any(
            spicy_word in name or spicy_word in description 
            for spicy_word in SPICY_KEYWORDS
        )
        if not has_spicy:
            return False
    
    # Rule 4: Check vegetarian requirement (AND condition)
    if requirements["vegetarian"]:
        has_vegetarian = "vegetarian" in expanded_tags or any(
            veg_word in name or veg_word in description 
            for veg_word in VEGETARIAN_KEYWORDS
        )
        # Also check if it explicitly contains meat words (exclude if found)
        meat_words = {"chicken", "beef", "pork", "lamb", "fish", "shrimp", "salmon", "tuna", "bacon", "ham", "turkey", "duck", "crab", "lobster", "meat", "steak"}
        has_meat = any(meat in name or meat in description for meat in meat_words)
        
        if not has_vegetarian or has_meat:
            return False
    
    # Rule 5: Check vegan requirement if specified
    if requirements["vegan"]:
        has_vegan = "vegan" in expanded_tags or any(
            vegan_word in name or vegan_word in description 
            for vegan_word in VEGAN_KEYWORDS
        )
        # Check for dairy/egg words that would disqualify vegan items
        non_vegan_words = {"cheese", "milk", "cream", "butter", "egg", "yogurt", "mayo", "mayonnaise", "honey"}
        has_non_vegan = any(word in name or word in description for word in non_vegan_words)
        
        if not has_vegan or has_non_vegan:
            return False
    
    # Rule 6: Check other keywords (AND condition for all)
    for keyword in requirements["other_keywords"]:
        if not (keyword in name or keyword in description or keyword in str(expanded_tags).lower()):
            return False
    
    return True

@app.route('/recommend', methods=['POST'])
def recommend():
    """Main recommendation endpoint"""
    data = request.json
    user_query = data.get('query', '')
    
    # Parse requirements from query
    requirements = parse_query_requirements(user_query)
    
    # Get location (default to Tech Square)
    location = data.get('location', None)
    default_lat = 33.7770706
    default_lng = -84.3902668
    lat = default_lat
    lng = default_lng
    if location:
        lat = location.get('lat', default_lat)
        lng = location.get('lng', default_lng)
    
    # Get nearby restaurants
    nearby_restaurants = get_restaurants_nearby(lat, lng)
    
    # Get all menu items with restaurant info
    all_menu_items = []
    for rest in nearby_restaurants:
        menu_items = get_menu_items_for_restaurant(rest['id'])
        for item in menu_items:
            item['restaurant'] = rest
            all_menu_items.append(item)
    
    # Filter items based on requirements
    filtered_items = []
    for item in all_menu_items:
        if item_matches_requirements(item, requirements):
            filtered_items.append(item)
    
    # Shuffle and ensure unique restaurants
    random.shuffle(filtered_items)
    recommendations = []
    seen_restaurants = set()
    
    for item in filtered_items:
        rest_id = item['restaurant']['id']
        if rest_id not in seen_restaurants:
            recommendations.append(item)
            seen_restaurants.add(rest_id)
        if len(recommendations) >= 10:
            break
    
    return jsonify({
        "recommendations": recommendations,
        "debug_info": {
            "parsed_requirements": requirements,
            "total_items_checked": len(all_menu_items),
            "items_matching_criteria": len(filtered_items),
            "unique_restaurants": len(recommendations)
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)