import json

with open('data/restaurant_list/restaurants_google_maps.json', 'r', encoding='utf-8') as f:
    restaurants = json.load(f)

for restaurant in restaurants:
    seen = set()
    unique_menu = []
    for item in restaurant.get('menu_items', []):
        key = (item.get('name', '').strip().lower(), item.get('description', '').strip().lower())
        if key not in seen:
            unique_menu.append(item)
            seen.add(key)
    restaurant['menu_items'] = unique_menu

with open('data/restaurant_list/restaurants_google_maps_deduped.json', 'w', encoding='utf-8') as f:
    json.dump(restaurants, f, ensure_ascii=False, indent=2)

print("Deduplication complete. Output: restaurants_google_maps_deduped.json")