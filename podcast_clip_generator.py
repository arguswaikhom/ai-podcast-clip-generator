import subprocess
import sys
import os
import time
from datetime import datetime

# Add both root and utils directories to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "utils"))

from utils.output_folder_creator import create_full_directory_structure, OutputFolder
from utils.time_format import format_time

python_path = sys.executable

def execute_command(step_name: str, command: str):
    print(f"\n{'=' * 80}")
    print(f"STEP: {step_name}")
    print(f"Command: {command}")
    print("\n")
    subprocess.run(command, shell=True)
    print(f"{'-' * 80}\n")

def run_podcast_clipper(youtube_urls: list):
    total_start_time = time.time()
    print(f"\nStarting processing of {len(youtube_urls)} videos at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for i, youtube_url in enumerate(youtube_urls, 1):
        video_start_time = time.time()
        print(f"\nProcessing video {i}/{len(youtube_urls)}: {youtube_url}")
        print("=" * 80)
        
        # Create the full directory structure
        folders = create_full_directory_structure(youtube_url)

        # Run the transcript downloader
        yt_transcript_downloader_command = f"{python_path} yt_transcript_downloader.py {youtube_url} --output_folder {folders[OutputFolder.BASE]}"
        execute_command(f"(Video {i} - 1/7) Downloading transcript", yt_transcript_downloader_command)

        # Run the AI suggestion generator
        api_key = os.getenv('DEEPSEEK_API_KEY')
        suggestion_json_file = os.path.join(folders[OutputFolder.SEGMENTS_RESPONSE], "suggestions.json")
        prompt_file = os.path.join(current_dir, "prompt", "short_podcast.txt")
        segment_generator_command = f"{python_path} ai_suggestion_generator.py --segment-folder {folders[OutputFolder.SEGMENTS_INPUT]} --system-prompt-file {prompt_file} --output-folder {folders[OutputFolder.SEGMENTS_RESPONSE]} --suggestion-output {suggestion_json_file} --api-key {api_key}"
        execute_command(f"(Video {i} - 2/7) Generating segment suggestions", segment_generator_command)

        # Run the video downloader
        downloaded_yt_video_file = os.path.join(folders[OutputFolder.VIDEO], "video.mp4")
        video_downloader_command = f"{python_path} yt_video_downloader.py --youtube-url {youtube_url} --output-file {downloaded_yt_video_file}"
        execute_command(f"(Video {i} - 3/7) Downloading video", video_downloader_command)

        # Run the suggested video clipper
        yt_clip_folder = folders[OutputFolder.VIDEO_CLIPS]
        video_clipper_command = f"{python_path} video_suggestion_clipper.py {downloaded_yt_video_file} {suggestion_json_file} {yt_clip_folder} --remove-silence"
        execute_command(f"(Video {i} - 4/7) Clipping video", video_clipper_command)

        # Run the vertical video converter
        vertical_video_folder = folders[OutputFolder.VERTICAL_CLIPS]
        vertical_video_converter_command = f"{python_path} vertical_video_converter.py {yt_clip_folder} --output_folder {vertical_video_folder}"
        execute_command(f"(Video {i} - 5/7) Converting video to vertical", vertical_video_converter_command)

        # Run subtitle generator
        clip_subtitles_folder = folders[OutputFolder.CLIP_SUBTITLES]
        subtitle_generator_command = f"{python_path} video_subtitle_generator.py {vertical_video_folder} --output_folder {clip_subtitles_folder} --word_timings"
        execute_command(f"(Video {i} - 6/7) Generating subtitles", subtitle_generator_command)

        # Attach subtitles to the vertical video
        subtitled_video_folder = folders[OutputFolder.SUBTITLED_CLIPS]
        highlight_style = "standard" # "bigword"
        animation_style = "scale" # "bounce"
        subtitled_video_converter_command = f"{python_path} video_subtitle_embedder.py {vertical_video_folder} {clip_subtitles_folder} --output_folder {subtitled_video_folder} --highlight {highlight_style} --animation {animation_style}"
        execute_command(f"(Video {i} - 7/7) Attaching subtitles", subtitled_video_converter_command)

        # Calculate and display time taken for this video
        video_end_time = time.time()
        video_duration = video_end_time - video_start_time
        print(f"\nTime taken to process video {i}: {format_time(video_duration)}")
        print("=" * 80)

    # Calculate and display total time taken
    total_end_time = time.time()
    total_duration = total_end_time - total_start_time
    print(f"\n{'=' * 80}")
    print(f"Processing completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time taken to process all videos: {format_time(total_duration)}")
    print(f"{'=' * 80}\n")

if __name__ == "__main__":
    youtube_urls = [
        "https://www.youtube.com/watch?v=ZPUtA3W-7_I", # Narendra Modi: Prime Minister of India - Power, Democracy, War & Peace | Lex Fridman Podcast #460
        "https://www.youtube.com/watch?v=f_lRdkH_QoY", # Tucker Carlson: Putin, Navalny, Trump, CIA, NSA, War, Politics & Freedom | Lex Fridman Podcast #414
        "https://www.youtube.com/watch?v=oFfVt3S51T4", # Cursor Team: Future of Programming with AI | Lex Fridman Podcast #447
        "https://www.youtube.com/watch?v=sSOxPJD-VNo", # Joe Rogan Experience #2281 - Elon Musk
        "https://www.youtube.com/watch?v=sY8aFSY2zv4", # Jordan Peterson: Life, Death, Power, Fame, and Meaning | Lex Fridman Podcast #313
        "https://www.youtube.com/watch?v=T3FC7qIAGZk", # Andrew Bustamante: CIA Spy | Lex Fridman Podcast #310
        "https://www.youtube.com/watch?v=JN3KPFbWCy8", # Elon Musk: War, AI, Aliens, Politics, Physics, Video Games, and Humanity | Lex Fridman Podcast #400
        "https://www.youtube.com/watch?v=3qHkcs3kG44", # Joe Rogan Experience #1309 - Naval Ravikant
        "https://www.youtube.com/watch?v=q8VePUwjB9Y", # Jordan Peterson: Nietzsche, Hitler, God, Psychopathy, Suffering & Meaning | Lex Fridman Podcast #448
        "https://www.youtube.com/watch?v=BEWz4SXfyCQ", # Joe Rogan Experience #1315 - Bob Lazar & Jeremy Corbell
    ]
    run_podcast_clipper(youtube_urls)