
import yt_dlp
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_extraction(url):
    print(f"Testing URL: {url}")
    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"Title: {info.get('title')}")
            print(f"Direct URL found: {'Yes' if info.get('url') else 'No'}")
            if info.get('requested_formats'):
                print("Formats: Merged (Video+Audio)")
            else:
                print("Formats: Single File")
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=BaW_jenozKc" # Standard test video
    success = test_extraction(test_url)
    if success:
        print("yt-dlp is working correctly.")
    else:
        print("yt-dlp failed.")
