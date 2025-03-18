import yt_dlp
import urllib.parse
import time
import re
from typing import Optional
import argparse


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract the video ID from a YouTube URL.
    
    Args:
        url (str): The YouTube video URL
        
    Returns:
        str: The YouTube video ID or None if not found
    """
    # Handle various YouTube URL formats
    if 'youtu.be/' in url:
        # Short URL format: https://youtu.be/VIDEO_ID
        return url.split('youtu.be/')[1].split('?')[0].split('&')[0]
    elif 'youtube.com/watch' in url:
        # Standard URL format: https://www.youtube.com/watch?v=VIDEO_ID
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        return query_params.get('v', [None])[0]
    elif 'youtube.com/embed/' in url:
        # Embed URL format: https://www.youtube.com/embed/VIDEO_ID
        return url.split('youtube.com/embed/')[1].split('?')[0].split('&')[0]
    elif 'youtube.com/v/' in url:
        # Old embed URL format: https://www.youtube.com/v/VIDEO_ID
        return url.split('youtube.com/v/')[1].split('?')[0].split('&')[0]
    
    # If no match found
    return None

def get_video_info(youtube_url):
    """
    Get information about a YouTube video without downloading it
    
    Args:
        youtube_url: URL of the YouTube video
    
    Returns:
        dict: Information about the video, or None if extraction failed
    """
    try:
        # Setup yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'ignoreerrors': False,
            'noplaylist': True,
        }
        
        # Extract video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return info
    
    except Exception as e:
        print(f"Error extracting video info: {str(e)}")
        return None
    
def get_video_title(youtube_url: str) -> str:
    """
    Get the title of a YouTube video.
    
    Args:
        youtube_url (str): The YouTube video URL
        
    Returns:
        str: The video title sanitized for use as a folder name
    """
    video_id = extract_video_id(youtube_url)
    if not video_id:
        print(f"Could not extract video ID from URL: {youtube_url}")
        return f"youtube_video_{int(time.time())}"
    
    try:
        # Use yt_video_downloader's functionality to get video info
        video_info = get_video_info(youtube_url)
        if video_info and 'title' in video_info:
            title = video_info['title']
        else:
            return f"youtube_video_{video_id}"
        
        # Sanitize title for use as folder name
        sanitized_title = re.sub(r'[^\w\s-]', '_', title)  # Replace non-alphanumeric chars except whitespace and dash
        sanitized_title = re.sub(r'\s+', '_', sanitized_title)  # Replace whitespace with underscore
        
        return sanitized_title
    
    except Exception as e:
        print(f"Error getting video title: {str(e)}")
        return f"youtube_video_{video_id}"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("link", type=str, help="The YouTube video link")
    parser.add_argument("--title", action="store_true", help="Print the title of the video")
    args = parser.parse_args()

    if args.title:
        print(get_video_title(args.link))
