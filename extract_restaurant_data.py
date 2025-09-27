# Google Maps and Yelp API restaurant extractor for Georgia Tech & Tech Square
import requests
import json

# Insert your API keys here
GOOGLE_API_KEY = 'AIzaSyDd82arIooHw1KLGIZ4pmPmsVJiesXbzis'
YELP_API_KEY = 'Zm8RifCKGYByWiO_kIUwoOkE53N-nHTXrSRLz53eVURoLPn9pZaKo7N-kEVfq52siohd48DBA__Q8Ql187XI1PGcFLyTHpOxV4IL-e_a3UEYGlTzHFiUsMYV6ufXaHYx'

# Georgia Tech/Tech Square coordinates
LOCATION = {'lat': 33.7770706, 'lng': -84.3902668}  # Georgia Tech/ Tech Square
RADIUS_METERS = 1000  # 1km radius

def get_google_restaurants():
	url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
	params = {
		'location': f"{LOCATION['lat']},{LOCATION['lng']}",
		'radius': RADIUS_METERS,
		'type': 'restaurant',
		'key': GOOGLE_API_KEY
	}
	restaurants = []
	next_page_token = None
	while True:
		if next_page_token:
			params['pagetoken'] = next_page_token
		response = requests.get(url, params=params)
		data = response.json()
		results = data.get('results', [])
		for r in results:
			place_id = r.get('place_id')
			details = get_place_details(place_id)
			if details:
				restaurants.append(details)
		next_page_token = data.get('next_page_token')
		if not next_page_token or len(restaurants) >= 60:
			break
		import time
		time.sleep(2)
	return restaurants

def get_place_details(place_id):
	url = 'https://maps.googleapis.com/maps/api/place/details/json'
	fields = [
		'name', 'formatted_address', 'rating', 'user_ratings_total', 'opening_hours', 'photos',
		'types', 'price_level', 'website', 'formatted_phone_number', 'business_status', 'reviews', 'url'
	]
	params = {
		'place_id': place_id,
		'fields': ','.join(fields),
		'key': GOOGLE_API_KEY
	}
	response = requests.get(url, params=params)
	result = response.json().get('result', {})
	if not result:
		return None
	# Extract photo URLs if available
	photos = []
	for p in result.get('photos', []):
		photos.append(f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={p.get('photo_reference')}&key={GOOGLE_API_KEY}")
	# Extract reviews
	reviews = []
	for rev in result.get('reviews', []):
		reviews.append({
			'author_name': rev.get('author_name'),
			'rating': rev.get('rating'),
			'text': rev.get('text'),
			'time': rev.get('relative_time_description')
		})
	return {
		'name': result.get('name'),
		'address': result.get('formatted_address'),
		'rating': result.get('rating'),
		'user_ratings_count': result.get('user_ratings_total'),
		'opening_hours': result.get('opening_hours', {}).get('weekday_text'),
		'photos': photos,
		'types': result.get('types'),
		'price_level': result.get('price_level'),
		'website': result.get('website'),
		'phone_number': result.get('formatted_phone_number'),
		'business_status': result.get('business_status'),
		'reviews': reviews,
		'google_maps_url': result.get('url')
	}

# def get_yelp_restaurants():
# 	url = 'https://api.yelp.com/v3/businesses/search'
# 	headers = {
# 		'Authorization': f'Bearer {YELP_API_KEY}'
# 	}
# 	params = {
# 		'latitude': LOCATION['lat'],
# 		'longitude': LOCATION['lng'],
# 		'radius': RADIUS_METERS,
# 		'categories': 'restaurants',
# 		'limit': 50
# 	}
# 	response = requests.get(url, headers=headers, params=params)
# 	results = response.json().get('businesses', [])
# 	restaurants = []
# 	for r in results:
# 		restaurants.append({
# 			'name': r.get('name'),
# 			'address': r.get('location', {}).get('address1'),
# 			'rating': r.get('rating'),
# 			'source': 'Yelp'
# 		})
# 	return restaurants

def main():
	print('Fetching Google Maps restaurants...')
	google_restaurants = get_google_restaurants()
	print(f'Found {len(google_restaurants)} restaurants from Google Maps.')
	# for r in google_restaurants:
	# 	print(r)

	# print('\nFetching Yelp restaurants...')
	# yelp_restaurants = get_yelp_restaurants()
	# print(f'Found {len(yelp_restaurants)} restaurants from Yelp.')
	# for r in yelp_restaurants:
	# 	print(r)

	print('Fetching Google Maps restaurants...')
	google_restaurants = get_google_restaurants()
	print(f'Found {len(google_restaurants)} restaurants from Google Maps.')
	# Save to JSON file
	with open('restaurants_google_maps.json', 'w', encoding='utf-8') as f:
		json.dump(google_restaurants, f, ensure_ascii=False, indent=2)
	print('Saved all restaurant data to restaurants_google_maps.json')

if __name__ == '__main__':
	main()
