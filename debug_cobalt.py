
import requests
import json

def test_cobalt():
    url = "https://cobalt-api.kwiatekmiki.pl/api/json" # A public instance
    # accessing public list: https://instances.cobalt.tools/
    # Main api: https://api.cobalt.tools/api/json (often rate limited or requires headers)
    
    # Try a few instances
    instances = [
        "https://api.cobalt.tools/api/json",
        "https://cobalt.kwiatekmiki.pl/api/json",
        "https://co.wuk.sh/api/json"
    ]
    
    test_video = "https://www.youtube.com/watch?v=BaW_jenozKc"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    body = {
        "url": test_video
    }

    for instance in instances:
        print(f"Testing Cobalt instance: {instance}")
        try:
            response = requests.post(instance, json=body, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                print("Success!")
                print(f"Status: {data.get('status')}")
                print(f"URL: {data.get('url')[:50]}...")
                return True
            else:
                print(f"Failed: {response.status_code} - {response.text[:100]}")
        except Exception as e:
            print(f"Error: {e}")
            
    return False

if __name__ == "__main__":
    if test_cobalt():
        print("\nCobalt API works!")
    else:
        print("\nCobalt API failed.")
