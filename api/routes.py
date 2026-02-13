"""
API routes for the VideoDownloader web application.
"""
from flask import Blueprint, request, jsonify, send_file, Response, stream_with_context
from pathlib import Path
import logging
import os
import requests
from core.streamer import Streamer

streamer = Streamer()

api = Blueprint('api', __name__)

# Will be set by main app
downloader = None
config_manager = None
database = None


def init_api(dl, cfg, db):
    """Initialize API with downloader and config instances"""
    global downloader, config_manager, database
    downloader = dl
    config_manager = cfg
    database = db


@api.route('/download', methods=['POST'])
def submit_download():
    """Submit a new download"""
    try:
        data = request.json
        url = data.get('url')
        download_type = data.get('download_type', 'video')
        quality = data.get('quality', 'Best Available')
        
        options = {
            'embed_metadata': data.get('embed_metadata', True),
            'embed_thumbnail': data.get('embed_thumbnail', True),
            'embed_subtitles': data.get('embed_subtitles', False),
            'format_type': data.get('format_type', 'mp3')
        }
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        item = downloader.add_download(url, download_type, quality, options)
        
        return jsonify({
            'success': True,
            'id': item.id,
            'message': 'Download added to queue'
        })
    except Exception as e:
        logging.error(f"Error submitting download: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/queue', methods=['GET'])
def get_queue():
    """Get current download queue"""
    try:
        items = downloader.download_queue.get_all()
        return jsonify({'queue': items})
    except Exception as e:
        logging.error(f"Error getting queue: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/history', methods=['GET'])
def get_history():
    """Get download history"""
    try:
        # Server-side history is disabled for privacy/client-side storage policy
        # Only return empty list or in-memory session history if needed
        return jsonify({'history': []})
    except Exception as e:
        logging.error(f"Error getting history: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/download/<download_id>', methods=['DELETE'])
def cancel_download(download_id):
    """Cancel a download"""
    try:
        success = downloader.cancel_download(download_id)
        if success:
            return jsonify({'success': True, 'message': 'Download cancelled'})
        return jsonify({'error': 'Download not found'}), 404
    except Exception as e:
        logging.error(f"Error cancelling download: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/statistics', methods=['GET'])
def get_statistics():
    """Get download statistics"""
    try:
        # Database statistics disabled
        return jsonify({'statistics': {'total': 0, 'completed': 0, 'failed': 0}})
    except Exception as e:
        logging.error(f"Error getting statistics: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    try:
        return jsonify({
            'download_path': config_manager.get('download_path'),
            'concurrent_downloads': config_manager.get('concurrent_downloads'),
            'embed_metadata': config_manager.get('embed_metadata'),
            'embed_thumbnail': config_manager.get('embed_thumbnail'),
            'embed_subtitles': config_manager.get('embed_subtitles')
        })
    except Exception as e:
        logging.error(f"Error getting settings: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/settings', methods=['POST'])
def update_settings():
    """Update settings"""
    try:
        data = request.json
        
        for key, value in data.items():
            if key in ['download_path', 'concurrent_downloads', 'embed_metadata', 
                      'embed_thumbnail', 'embed_subtitles']:
                config_manager.set(key, value)
        
        # Update concurrent downloads if changed
        if 'concurrent_downloads' in data:
            downloader.max_concurrent = data['concurrent_downloads']
        
        return jsonify({'success': True, 'message': 'Settings updated'})
    except Exception as e:
        logging.error(f"Error updating settings: {e}")
        return jsonify({'error': str(e)}), 500


@api.route('/formats/<path:url>', methods=['GET'])
def get_formats(url):
    """Get available formats for a URL (not implemented yet)"""
    # This would require extracting format info from yt-dlp
    return jsonify({'message': 'Not implemented yet'}), 501


@api.route('/serve_file/<download_id>', methods=['GET'])
def serve_file(download_id):
    """Serve a downloaded file to the client"""
    try:
        # Get download item from queue or active downloads
        # Since we use move_to_history, check history list in memory
        item = downloader.download_queue.get_by_id(download_id)
        if not item:
             # Check in-memory history
             # Note: downloader.download_queue.history is a list of DownloadItem objects
             item = next((i for i in downloader.download_queue.history if i.id == download_id), None)
        
        if not item:
             return jsonify({'error': 'Download not found'}), 404
             
        # Case 1: File exists on server (Merged format or previously downloaded)
        if item.file_path and os.path.exists(item.file_path):
            return send_file(
                item.file_path,
                as_attachment=True,
                download_name=os.path.basename(item.file_path)
            )
        
        # Case 2: Direct URL exists (Single file format) - Proxy Stream
        elif item.direct_url:
            try:
                # Stream the content from the direct URL
                req = requests.get(item.direct_url, stream=True)
                
                # Create a generator to stream chunks
                def generate():
                    for chunk in req.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                
                # Determine filename extension from Content-Type
                content_type = req.headers.get('Content-Type', '')
                ext = '.mp4' # Default
                if 'video/webm' in content_type:
                    ext = '.webm'
                elif 'audio/mpeg' in content_type:
                    ext = '.mp3'
                elif 'audio/mp4' in content_type:
                    ext = '.m4a'
                elif 'video/mp4' in content_type:
                    ext = '.mp4'
                
                # Sanitize title for filename
                safe_title = "".join([c for c in item.title if c.isalpha() or c.isdigit() or c==' ' or c in ('-','_')]).rstrip()
                filename = f"{safe_title}{ext}"
                
                headers = {
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': content_type or 'video/mp4',
                    'Content-Length': req.headers.get('Content-Length')
                }
                
                return Response(stream_with_context(generate()), headers=headers)
            except Exception as e:
                logging.error(f"Proxy stream error: {e}")
                return jsonify({'error': f"Stream failed: {str(e)}"}), 500

        else:
            return jsonify({'error': 'File not found and no direct link available'}), 404
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return jsonify({'error': str(e)}), 500
        return jsonify({'error': str(e)}), 500


@api.route('/stream', methods=['GET'])
def stream_video():
    """Stream video directly to client"""
    try:
        url = request.args.get('url')
        quality = request.args.get('quality', 'Best Available')
        
        if not url:
            return "Error: URL is required", 400
        
        # Log attempts
        logging.info(f"Stream request for: {url} | Quality: {quality}")
        
        # Get direct URLs
        video_url, audio_url, title = streamer.get_direct_urls(url, quality)
        
        if not video_url:
             logging.error(f"Failed to resolve stream URL for {url}")
             return f"Error: Could not resolve stream URL. Please try again or check the URL.", 400
             
        # Sanitize title
        safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c==' ' or c in ('-','_')]).rstrip()
        filename = f"{safe_title}.mkv" # We force mkv container in streamer
        
        generator = streamer.stream_video(url, quality)
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"',
            'Content-Type': 'video/x-matroska',
        }
        
        return Response(stream_with_context(generator), headers=headers)
        
    except Exception as e:
        logging.error(f"Stream route error: {e}")
        return f"Error: {str(e)}", 500
