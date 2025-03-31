#!/usr/bin/env python3
import os
import argparse
import time
import subprocess

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
    
    start_time = time.time()
    yt_dlp_downloader_command = f"yt-dlp -f \"bestvideo[height<=1080]+bestaudio/best[height<=1080]\" -o {output_file} {youtube_url}"
    print(f"Downloading video with yt-dlp: {yt_dlp_downloader_command}")
    subprocess.run(yt_dlp_downloader_command, shell=True)
    duration = time.time() - start_time
    print(f"Total download time: {duration:.2f} seconds")

    return True

def process_video(youtube_url, output_file=None):
    """
    Main function to process a YouTube video download request
    
    Args:
        youtube_url: URL of the YouTube video to download
        output_file: Path to save the downloaded video (optional)
        
    Returns:
        bool: True if download was successful, False otherwise
    """
    # Set default output path if not provided
    if not output_file:
        os.makedirs("output/video_output", exist_ok=True)
        output_file = os.path.join("output/video_output", "video.mp4")
    
    # Download the video
    return download_video(youtube_url, output_file)

def main():
    parser = argparse.ArgumentParser(description="Download YouTube videos in best quality")
    parser.add_argument("--youtube-url", required=True, help="URL of the YouTube video to download")
    parser.add_argument("--output-file", required=False, help="Path to save the downloaded video")
    
    args = parser.parse_args()
    
    # Process the video
    process_video(args.youtube_url, args.output_file)

if __name__ == "__main__":
    main()
