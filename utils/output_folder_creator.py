import os
from yt_info_extractor import get_video_title
import argparse

class OutputFolder:
    BASE = "base"
    TRANSCRIPT = "transcript"
    SEGMENTS_INPUT = "segments_input"
    SEGMENTS_RESPONSE = "segments_response"
    VIDEO = "video"
    VIDEO_CLIPS = "video_clips"
    VERTICAL_CLIPS = "vertical_clips"
    CLIP_SUBTITLES = "clip_subtitles"
    SUBTITLED_CLIPS = "subtitled_clips"
    

def create_directory_structure(base_folder: str) -> dict:
    """
    Create the directory structure for the podcast clipper.
    
    Args:
        base_folder (str): The base folder name
        
    Returns:
        dict: Dictionary containing all the folder paths
    """
    
    folders = {
        OutputFolder.BASE: base_folder,
        OutputFolder.TRANSCRIPT: os.path.join(base_folder, "transcript"),
        OutputFolder.SEGMENTS_INPUT: os.path.join(base_folder, "segments", "input"), 
        OutputFolder.SEGMENTS_RESPONSE: os.path.join(base_folder, "segments", "response"),
        OutputFolder.VIDEO: os.path.join(base_folder, "video"),
        OutputFolder.VIDEO_CLIPS: os.path.join(base_folder, "video", "clips"),
        OutputFolder.VERTICAL_CLIPS: os.path.join(base_folder, "video", "vertical_clips"),
        OutputFolder.CLIP_SUBTITLES: os.path.join(base_folder, "video", "clip_subtitles"),
        OutputFolder.SUBTITLED_CLIPS: os.path.join(base_folder, "video", "subtitled_clips")
    }
    
    # Create each folder
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
        print(f"Created directory: {folder}")
    
    return folders

def create_full_directory_structure(youtube_url: str) -> dict:
    video_title = get_video_title(youtube_url)

    # Truncate title to 150 chars
    folder_name = video_title[:150]
    print(f"Video title: {folder_name}")
    
    # Create base output directory
    output_root = "output"
    base_folder = os.path.join(output_root, folder_name)

    return create_directory_structure(base_folder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("youtube_url", help="URL of the YouTube video to process")
    parser.add_argument("--create-folders", "-c", action="store_true", help="Create the folders")
    args = parser.parse_args()

    if args.create_folders:
        create_full_directory_structure(args.youtube_url)

