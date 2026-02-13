
import requests
import json

def test_invidious_instance(instance_url, video_id):
    print(f"Testing instance: {instance_url}")
    try:
        api_url = f"{instance_url}/api/v1/videos/{video_id}"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Title: {data.get('title')}")
            
            # Check for format streams
            if 'formatStreams' in data:
                print(f"Found {len(data['formatStreams'])} streams.")
                # Print first one
                print(f"Sample Stream URL: {data['formatStreams'][0]['url'][:50]}...")
                return True
            else:
                print("No formatStreams found.")
        else:
            print(f"Failed. Status: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False

if __name__ == "__main__":
    test_video_id = "BaW_jenozKc" # YouTube Rewind 2018 (Popular, likely cached)
    
    instances = [
        "https://inv.tux.pizza",
        "https://invidious.projectsegfau.lt",
        "https://invidious.fdn.fr",
        "https://vid.uff.ink"
    ]
    
    working_instances = []
    
    for instance in instances:
        if test_invidious_instance(instance, test_video_id):
            working_instances.append(instance)
            break # Found one working
            
    if working_instances:
        print(f"\nWorking instance found: {working_instances[0]}")
    else:
        print("\nNo working instances found in test list.")
