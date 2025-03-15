#!/usr/bin/env python3
import os
import re
import argparse
import urllib.parse
import subprocess
import json
import tempfile
from pathlib import Path


def extract_video_id(url):
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


def download_transcript(video_url, output_folder):
    """
    Download the transcript for a YouTube video using yt-dlp.
    
    Args:
        video_url (str): The YouTube video URL
        output_folder (str): The folder to save the transcript
        
    Returns:
        tuple: (original_path, transcript_text) - Path to original transcript file and the transcript text
    """
    try:
        # Create a temporary directory for the download
        temp_dir = tempfile.mkdtemp()
        
        # Get the video ID for naming the files
        video_id = extract_video_id(video_url)
        if not video_id:
            print(f"Could not extract video ID from URL: {video_url}")
            return None, None
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Path for saving the original transcript
        original_path = os.path.join(output_folder, f"{video_id}_original.vtt")
        
        # Use yt-dlp to download only the subtitles
        # --write-auto-sub: download auto-generated subs
        # --sub-lang en: download English subtitles
        # --skip-download: skip downloading the video
        # --write-sub: download subtitles
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--sub-lang", "en",
            "--skip-download",
            "--write-sub",
            "--sub-format", "vtt",
            "-o", os.path.join(temp_dir, "%(id)s.%(ext)s"),
            video_url
        ]
        
        print(f"Downloading transcript for {video_url}...")
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode != 0:
            print(f"Error downloading transcript: {process.stderr}")
            return None, None
        
        # Find the downloaded subtitle file
        subtitle_file = None
        for file in os.listdir(temp_dir):
            if file.endswith('.en.vtt'):
                subtitle_file = os.path.join(temp_dir, file)
                break
        
        if not subtitle_file:
            print("No English subtitles found for this video.")
            return None, None
        
        # Read the transcript file
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        # Save the original transcript to the output folder
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(transcript_text)
        
        print(f"Original transcript saved to: {original_path}")
        
        return original_path, transcript_text
        
    except Exception as e:
        print(f"Error downloading transcript: {str(e)}")
        return None, None


def clean_transcript(transcript_text):
    """
    Clean up the WebVTT transcript format to a simpler format.
    
    Args:
        transcript_text (str): The original WebVTT transcript text
        
    Returns:
        str: The cleaned transcript text
    """
    # Create a temporary file to store the transcript text
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.vtt', delete=False) as temp_file:
        temp_file.write(transcript_text)
        temp_path = temp_file.name
    
    # Create a temporary file for the output
    output_path = tempfile.NamedTemporaryFile(suffix='.txt', delete=False).name
    
    # Use the clean_transcript_for_llm function to clean the transcript
    clean_transcript_for_llm(temp_path, output_path)
    
    # Read the cleaned transcript
    with open(output_path, 'r', encoding='utf-8') as f:
        cleaned_transcript = f.read()
    
    # Clean up temporary files
    try:
        os.remove(temp_path)
        os.remove(output_path)
    except:
        pass
        
    return cleaned_transcript


def clean_transcript_for_llm(input_file, output_file=None):
    """
    Clean up a VTT transcript file to make it more suitable for LLM analysis
    by reducing token usage and making the content more effective to analyze.
    
    Args:
        input_file (str): Path to the .vtt transcript file
        output_file (str, optional): Path to save the cleaned transcript. If None, will append '_clean' to input filename.
    
    Returns:
        str: Path to the cleaned transcript file
    """
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_clean{ext}"
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        # Try another encoding if utf-8 fails
        with open(input_file, 'r', encoding='latin-1') as f:
            content = f.read()
    
    # Remove WEBVTT header and metadata
    content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
    
    # Process timestamps and content
    # Extract timestamp lines and their content
    timestamp_pattern = r'(\d+:\d+:\d+\.\d+ --> \d+:\d+:\d+\.\d+.*?)\n((?:(?!^\d+:\d+:\d+\.\d+).*\n)+)'
    segments = re.findall(timestamp_pattern, content, re.MULTILINE)
    
    processed_content = []
    prev_text = ""  # To track previously processed text for removing repeats
    
    for timestamp, text in segments:
        # Extract just start-end time without positioning info
        simplified_timestamp = re.search(r'(\d+:\d+:\d+\.\d+ --> \d+:\d+:\d+\.\d+)', timestamp).group(1)
        
        # Clean the text associated with this timestamp
        cleaned_text = text.strip()
        # Remove formatting tags like <c> and timestamps within text
        cleaned_text = re.sub(r'<\d+:\d+:\d+\.\d+><c>(.*?)</c>', r'\1', cleaned_text)
        cleaned_text = re.sub(r'<\d+:\d+:\d+\.\d+>', '', cleaned_text)
        cleaned_text = re.sub(r'</?c>', '', cleaned_text)
        cleaned_text = re.sub(r'align:start position:0%', '', cleaned_text)
        
        # Remove duplicate lines and check for overlapping content with previous segments
        lines = cleaned_text.split('\n')
        unique_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is a substring of the last processed line
            # or if the last processed line is a substring of this line
            if prev_text and (line in prev_text or prev_text in line):
                # If there's overlap, only add the non-overlapping part
                if len(line) > len(prev_text):
                    # Current line is longer, take just the new part
                    unique_part = line[len(prev_text):].strip()
                    if unique_part:
                        unique_lines.append(unique_part)
            else:
                unique_lines.append(line)
                prev_text = line  # Update previous text
        
        # Join cleaned text lines without adding extra space between them
        if unique_lines:
            joined_text = " ".join(unique_lines)
            
            # Add to processed content only if we have meaningful text
            if joined_text.strip():
                processed_content.append(f"[{simplified_timestamp}] {joined_text}")
                prev_text = joined_text  # Update previous text to full joined text
    
    # Join all segments with a single newline instead of double newlines
    text = "\n".join(processed_content)
    
    # Apply final cleanup
    # Remove multiple consecutive spaces
    text = re.sub(r' +', ' ', text)
    
    # Don't add extra newlines, just clean up excessive ones
    text = re.sub(r'\n{3,}', '\n', text)
    
    # Attempt to identify speakers for better context but keep the formatting tight
    text = re.sub(r'([A-Z][a-z]+ ?[A-Z]?[a-z]*): ', r'\1: ', text)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"Cleaned transcript saved to: {output_file}")
    
    return output_file


def time_to_seconds(time_str):
    """
    Convert a time string (HH:MM:SS.mmm) to seconds.
    
    Args:
        time_str (str): Time string in format HH:MM:SS.mmm
        
    Returns:
        float: Total seconds
    """
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def process_youtube_url(yt_url, output_folder):
    """
    Process a YouTube URL to download and clean the transcript.
    
    Args:
        yt_url (str): The YouTube video URL
        output_folder (str): The output folder for transcripts
    """
    print(f"Processing YouTube URL: {yt_url}")
    
    # Extract video ID for naming
    video_id = extract_video_id(yt_url)
    if not video_id:
        print(f"Error: Could not extract video ID from URL: {yt_url}")
        return
    
    # Define file paths
    original_path = os.path.join(output_folder, f"{video_id}_original.vtt")
    cleaned_path = os.path.join(output_folder, f"{video_id}_cleaned.txt")
    
    # Check if transcript files already exist
    original_exists = os.path.exists(original_path)
    cleaned_exists = os.path.exists(cleaned_path)
    
    # Download or use existing transcript
    if original_exists:
        print(f"Original transcript already exists at: {original_path}")
        # Read the existing transcript
        try:
            with open(original_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        except UnicodeDecodeError:
            # Try another encoding if utf-8 fails
            with open(original_path, 'r', encoding='latin-1') as f:
                transcript_text = f.read()
    else:
        # Download the transcript
        downloaded_path, transcript_text = download_transcript(yt_url, output_folder)
        if not transcript_text:
            print("Failed to download transcript.")
            return
    
    # Clean the transcript if needed
    if cleaned_exists:
        print(f"Cleaned transcript already exists at: {cleaned_path}")
    else:
        # Clean the transcript
        print("Cleaning transcript...")
        cleaned_transcript = clean_transcript(transcript_text)
        
        # Save the cleaned transcript
        with open(cleaned_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_transcript)
        
        print(f"Cleaned transcript saved to: {cleaned_path}")
    
    print(f"Transcript processing completed for video ID: {video_id}")


def main():
    parser = argparse.ArgumentParser(description="Download and clean YouTube video transcripts using yt-dlp")
    parser.add_argument("yt_url", help="YouTube video URL")
    parser.add_argument("--output_folder", "-o", 
                        help="Folder to save transcripts (default: 'transcript_output')",
                        default="transcript_output")
    
    args = parser.parse_args()
    
    # Process the YouTube URL
    process_youtube_url(args.yt_url, args.output_folder)


if __name__ == "__main__":
    main()
