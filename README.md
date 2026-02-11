# VideoDownloader Web

A modern, beautiful web application for downloading videos from the internet. Built with Flask, SocketIO, and yt-dlp, featuring real-time download progress updates and a premium glassmorphism UI design.

![VideoDownloader Web](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## ✨ Features

- **🎥 Multi-Platform Support**: Download videos from YouTube, Vimeo, Dailymotion, and 1000+ other sites
- **🎵 Audio Extraction**: Download audio-only in MP3, M4A, WAV, or FLAC formats
- **📊 Real-Time Progress**: Live download progress with speed and ETA via WebSocket
- **⚡ Concurrent Downloads**: Download multiple videos simultaneously (configurable)
- **📁 Download History**: Track all your downloads with searchable history
- **🎨 Modern UI**: Beautiful dark theme with glassmorphism effects
- **📱 Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **⚙️ Quality Selection**: Choose from 4K, 1080p, 720p, 480p, and more
- **🔄 Auto-Retry**: Automatic retry on failed downloads
- **📈 Statistics**: View download statistics and success rates

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd VideoDownloaderWeb
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

That's it! 🎉

## 📖 Usage Guide

### Downloading a Video

1. Navigate to the **Download** tab
2. Paste the video URL into the input field
3. Select download type (Video, Audio, or Playlist)
4. Choose quality (Best Available, 4K, 1080p, etc.)
5. Configure options:
   - ✅ Embed Metadata
   - ✅ Embed Thumbnail
   - ✅ Embed Subtitles (for videos)
6. Click **Add to Queue**

### Managing Queue

1. Navigate to the **Queue** tab
2. View all active and queued downloads
3. Monitor real-time progress with:
   - Progress bar
   - Download speed
   - Estimated time remaining
4. Cancel downloads if needed

### Viewing History

1. Navigate to the **History** tab
2. Search downloads by title, channel, or URL
3. View download statistics including:
   - Total downloads
   - Success rate
   - Total size downloaded
4. Filter by status (Completed, Failed, etc.)

### Configuring Settings

1. Navigate to the **Settings** tab
2. Configure:
   - Download directory path
   - Concurrent downloads (1-5)
   - Default metadata options
3. Click **Save Settings**

## 🛠️ Technical Stack

### Backend
- **Flask**: Web framework
- **Flask-SocketIO**: Real-time WebSocket communication
- **yt-dlp**: Video downloading engine
- **SQLite**: Download history database
- **Threading**: Concurrent download processing

### Frontend
- **HTML5/CSS3**: Modern semantic markup
- **JavaScript (ES6+)**: Client-side logic
- **Socket.IO Client**: Real-time updates
- **Glassmorphism Design**: Premium UI aesthetics

## 📁 Project Structure

```
VideoDownloaderWeb/
├── app.py                    # Flask application entry point
├── requirements.txt          # Python dependencies
├── README.md                 # This file
├── core/                     # Core modules
│   ├── __init__.py
│   ├── models.py            # Data models
│   ├── database.py          # SQLite database manager
│   ├── config.py            # Configuration manager
│   └── web_downloader.py    # Download engine
├── api/                     # API routes
│   ├── __init__.py
│   └── routes.py            # REST API endpoints
├── static/                  # Static assets
│   ├── css/
│   │   └── style.css        # Modern styling
│   └── js/
│       └── app.js           # Client application
├── templates/               # HTML templates
│   └── index.html           # Main application page
└── downloads/               # Default download directory
```

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/download` | Submit new download |
| GET | `/api/queue` | Get current queue |
| GET | `/api/history` | Get download history |
| DELETE | `/api/download/<id>` | Cancel download |
| GET | `/api/statistics` | Get download stats |
| GET | `/api/settings` | Get settings |
| POST | `/api/settings` | Update settings |

## 🎨 Features in Detail

### Real-Time Updates via WebSocket

The application uses Socket.IO to provide real-time updates without polling:
- Download start notifications
- Live progress updates (%, speed, ETA)
- Completion notifications
- Error messages
- Log messages

### Quality Selection

Supports multiple quality options:
- **4K (2160p)**: Ultra HD quality
- **2K (1440p)**: Quad HD
- **Full HD (1080p)**: Standard HD
- **HD (720p)**: Basic HD
- **480p, 360p**: Lower resolutions
- **Best Available**: Automatically selects highest quality

### Audio Formats

Extract audio in various formats:
- **MP3**: Universal compatibility
- **M4A**: High quality
- **WAV**: Lossless
- **FLAC**: Lossless compression

## 🐛 Troubleshooting

### FFmpeg Errors

If you encounter FFmpeg-related errors, the application uses `static-ffmpeg` which automatically downloads and configures FFmpeg. If issues persist:

```bash
pip install --upgrade static-ffmpeg
```

### Download Failures

- Verify the URL is supported
- Check your internet connection
- Some sites may have download restrictions
- Try a different quality setting

### Port Already in Use

If port 5000 is already in use, edit `app.py` and change:
```python
socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```
to a different port number.

## 🔒 Security Note

This application is designed for **local use only**. If deploying to a production environment:
- Change the Flask secret key in `app.py`
- Add authentication
- Use HTTPS
- Configure CORS properly
- Set up a production WSGI server (e.g., Gunicorn)

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- **yt-dlp**: The powerful downloading engine
- **Flask**: The lightweight web framework
- **Socket.IO**: Real-time communication library

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

## 📧 Support

For issues or questions, please check the log in the Download tab for error messages.

---

**Enjoy downloading! 🎉**
