"""
API routes for the VideoDownloader web application.
"""
from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import logging
import os

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
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status_filter = request.args.get('status')
        search_query = request.args.get('search')
        
        items = database.get_history(limit, offset, status_filter, search_query)
        history_data = [item.to_dict() for item in items]
        
        return jsonify({'history': history_data})
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
        stats = database.get_statistics()
        return jsonify({'statistics': stats.to_dict()})
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
        # Get download item from database or queue
        item = downloader.download_queue.get_by_id(download_id)
        if not item:
            # Try database
            # Note: This requires implementing a get_by_id in database manager if not exists
            # For now, let's search in history if we can, or just rely on queue for active/recent
            # But the user wants history too.
            # Let's assume we can get it from the database via a new method or search.
            # Actually, `downloader.download_queue.history` might have it if loaded.
            item = next((i for i in downloader.download_queue.history if i.id == download_id), None)
        
        if not item:
             return jsonify({'error': 'Download not found'}), 404
             
        if not item.file_path or not os.path.exists(item.file_path):
            return jsonify({'error': 'File not found on server'}), 404
            
        return send_file(
            item.file_path,
            as_attachment=True,
            download_name=os.path.basename(item.file_path)
        )
    except Exception as e:
        logging.error(f"Error serving file: {e}")
        return jsonify({'error': str(e)}), 500
