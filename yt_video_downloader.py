#!/usr/bin/env python3
import os
import sys
import argparse
import time
import yt_dlp

def format_bytes(bytes):
    """
    Format bytes to human-readable format
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} PB"

class DownloadLogger:
    """
    Logger for yt-dlp to track download progress
    """
    def __init__(self):
        self.start_time = time.time()
        self.last_downloaded_bytes = 0
        
    def debug(self, msg):
        # For debugging purposes, uncomment if needed
        # print(f"DEBUG: {msg}")
        pass
        
    def info(self, msg):
        # For info messages, uncomment if needed
        # print(f"INFO: {msg}")
        pass
        
    def warning(self, msg):
        print(f"WARNING: {msg}")
        
    def error(self, msg):
        print(f"ERROR: {msg}")

def progress_hook(d):
    """
    Progress hook for yt-dlp
    """
    if d['status'] == 'downloading':
        # Calculate download speed and ETA
        current_time = time.time()
        elapsed = current_time - progress_hook.start_time
        
        # Extract info from status
        downloaded_bytes = d.get('downloaded_bytes', 0)
        total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        
        if total_bytes > 0:
            # Calculate percentage if total is known
            percentage = (downloaded_bytes / total_bytes) * 100
            
            # Calculate speed
            if elapsed > 0:
                speed = downloaded_bytes / elapsed
                speed_str = format_bytes(speed) + '/s'
            else:
                speed_str = "N/A"
            
            # Calculate ETA
            if speed > 0:
                eta = (total_bytes - downloaded_bytes) / speed
                # Format eta as MM:SS
                eta_min, eta_sec = divmod(int(eta), 60)
                eta_str = f"{eta_min:02d}:{eta_sec:02d}"
            else:
                eta_str = "N/A"
            
            # Format progress bar
            progress_bar = f"Downloading: {percentage:.2f}% | "
            progress_bar += f"{format_bytes(downloaded_bytes)} of {format_bytes(total_bytes)} | "
            progress_bar += f"Speed: {speed_str} | ETA: {eta_str}"
            
            # Print progress
            sys.stdout.write(f"\r{progress_bar}")
            sys.stdout.flush()
    
    elif d['status'] == 'finished':
        # Download finished
        elapsed = time.time() - progress_hook.start_time
        sys.stdout.write("\n")
        print(f"Download completed in {elapsed:.2f} seconds")

# Initialize start_time
progress_hook.start_time = time.time()

def download_video(youtube_url, output_file):
    """
    Download a YouTube video in the best quality using yt-dlp
    
    Args:
        youtube_url: URL of the YouTube video
        output_file: Path to save the downloaded video
    
    Returns:
        bool: True if download successful or file exists, False otherwise
    """
    # Check if file already exists
    if os.path.exists(output_file):
        print(f"Video already downloaded: {output_file}")
        return True
    
    try:
        # Create directory for output file if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        
        print(f"Fetching video information from: {youtube_url}")
        
        # Setup yt-dlp options
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',  # Best quality video and audio
            'outtmpl': output_file,  # Output file template
            'logger': DownloadLogger(),
            'progress_hooks': [progress_hook],
            'quiet': True,  # Suppress standard output
            'no_warnings': True,  # Suppress warnings
            'ignoreerrors': False,
            'noplaylist': True,  # Download single video, not playlist
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Convert to mp4
            }],
        }
        
        # Reset the start time for speed calculation
        progress_hook.start_time = time.time()
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            print(f"Downloading video: {info.get('title', 'Unknown title')}")
            print(f"Quality: Best available")
            ydl.download([youtube_url])
        
        print("Download completed successfully!")
        return True
    
    except Exception as e:
        print(f"\nError downloading video: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Download YouTube videos in best quality")
    parser.add_argument("--youtube-url", required=True, help="URL of the YouTube video to download")
    parser.add_argument("--output-file", required=False, help="Path to save the downloaded video")
    
    args = parser.parse_args()
    
    # Set default output path if not provided
    output_file = args.output_file
    if not output_file:
        os.makedirs("output/video_output", exist_ok=True)
        output_file = os.path.join("output/video_output", "video.mp4")
    
    # Download the video
    download_video(args.youtube_url, output_file)

if __name__ == "__main__":
    main()
