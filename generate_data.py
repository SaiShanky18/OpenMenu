import os
import json
import time
from dotenv import load_dotenv
from litellm import completion

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

PROMPT_TEMPLATE = """
Given the following menu item data, fill in any missing fields (description, calories, etc.) with reasonable estimates. If a field is already present, keep it. If you don't know, make a best guess. Do not add any new categories other than name, description, price, calories and tags. If the JSON currently contains any keys other than these, remove them. Ensure that the tags specifies what meat the dish contains, or "Vegetarian" or "Vegan" if it is vegetarian or vegan respectively. Return a JSON object with all fields filled.

Menu item:
{name: "%s", description: %s, price: %s, calories: %s, tags: %s}
"""

def enrich_menu_item(item):
    prompt = PROMPT_TEMPLATE % (
        item.get("name", "null"),
        json.dumps(item.get("description", None)),
        json.dumps(item.get("price", None)),
        json.dumps(item.get("calories", None)),
        json.dumps(item.get("tags", []))
    )
    messages = [
        {"role": "user", "content": prompt}
    ]
    max_attempts = 5
    attempt = 0
    while attempt < max_attempts:
        try:
            response = completion(
                model="gemini/gemini-2.0-flash-lite",
                api_key=GEMINI_API_KEY,
                messages=messages,
                response_format={"type": "json_object"}
            )
            enriched = json.loads(response.choices[0].message.content)
            return enriched
        except Exception as e:
            err_str = str(e)
            if "RateLimitError" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Try to extract suggested retry time from error message
                import re
                match = re.search(r'retryDelay":\s*"(\d+)', err_str)
                if match:
                    wait_time = int(match.group(1))
                else:
                    wait_time = 60  # Default to 60 seconds if not found
                print(f"Rate limit hit. Waiting {wait_time} seconds before retrying...")
                time.sleep(wait_time)
                attempt += 1
            else:
                print(f"Error parsing Gemini response for item '{item.get('name', '')}': {e}")
                return item
    print(f"Max retry attempts reached for item '{item.get('name', '')}'. Returning original item.")
    return item

def main():
    menus_dir = "data/menus"
    enriched_dir = "data/enriched_menus"
    os.makedirs(enriched_dir, exist_ok=True)
    menu_files = [f for f in os.listdir(menus_dir) if f.endswith(".json")]

    for menu_file in menu_files:
        input_path = os.path.join(menus_dir, menu_file)
        output_path = os.path.join(enriched_dir, menu_file.replace(".json", "_enriched.json"))
        print(f"\nProcessing {menu_file}...")
        with open(input_path, "r", encoding="utf-8") as f:
            menu_items = json.load(f)

        enriched_items = []
        for idx, item in enumerate(menu_items, 1):
            print(f"Enriching item {idx}/{len(menu_items)}: {item.get('name', '')}")
            enriched = enrich_menu_item(item)
            print(f"Enriched item: {enriched}\n")
            enriched_items.append(enriched)
            time.sleep(3)  # Sleep 3 seconds between LLM calls to avoid rate limits

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(enriched_items, f, ensure_ascii=False, indent=2)
        print(f"Enriched menu saved to {output_path}")

if __name__ == "__main__":
    main()
