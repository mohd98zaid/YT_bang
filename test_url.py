import yt_dlp
import json

# Rick Roll - Never Gonna Give You Up
url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
ydl_opts = {
    'quiet': True,
    'format': 'best',
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        print(f"Format: {info.get('format')}")
        print(f"URL: {info.get('url')}")
        # check requested formats
        req = info.get('requested_formats')
        if req:
            print("Requested Formats exist (Merged):")
            for f in req:
                print(f" - {f['format_id']}: {f['url']}")
        else:
            print("Single File Format")
except Exception as e:
    print(f"Error: {e}")
