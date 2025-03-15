import os
import argparse
import whisper
import time
from tqdm import tqdm
from pathlib import Path

class SubtitleGenerator:
    def __init__(self, model_name="base"):
        """
        Initialize the SubtitleGenerator with the specified Whisper model.
        
        Args:
            model_name: Whisper model size to use (tiny, base, small, medium, large)
        """
        print(f"Loading Whisper model '{model_name}'...")
        self.model = whisper.load_model(model_name)
        print("Model loaded successfully.")
    
    def generate_subtitle(self, video_path, output_path):
        """
        Generate subtitles for a video file using Whisper.
        
        Args:
            video_path: Path to the input video file
            output_path: Path where the subtitle file will be saved
        
        Returns:
            bool: True if subtitles were generated successfully, False otherwise
        """
        try:
            print(f"Transcribing video: {os.path.basename(video_path)}")
            
            # Use Whisper to transcribe the audio
            result = self.model.transcribe(video_path)
            
            # Create .srt format
            with open(output_path, 'w', encoding='utf-8') as srt_file:
                for i, segment in enumerate(result["segments"], start=1):
                    # Format start and end times (convert seconds to SRT format)
                    start_time = self._format_time(segment["start"])
                    end_time = self._format_time(segment["end"])
                    
                    # Write subtitle entry
                    srt_file.write(f"{i}\n")
                    srt_file.write(f"{start_time} --> {end_time}\n")
                    srt_file.write(f"{segment['text'].strip()}\n\n")
            
            print(f"Subtitle generated successfully: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating subtitle for {video_path}: {str(e)}")
            return False
    
    def _format_time(self, seconds):
        """
        Convert seconds to SRT time format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            str: Formatted time string
        """
        hours = int(seconds // 3600)
        seconds %= 3600
        minutes = int(seconds // 60)
        seconds %= 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def main():
    parser = argparse.ArgumentParser(description="Generate subtitles for videos using OpenAI's Whisper")
    parser.add_argument("input_folder", help="Path to folder containing video files")
    parser.add_argument("--model", choices=["tiny", "base", "small", "medium", "large"], 
                        default="base", help="Whisper model to use (default: base)")
    parser.add_argument("--output_folder", help="Path to output folder for subtitles (default: subtitle_output)",
                        default=None)
    parser.add_argument("--extensions", nargs="+", 
                        default=[".mp4", ".avi", ".mov", ".mkv", ".webm"],
                        help="Video file extensions to process (default: .mp4 .avi .mov .mkv .webm)")
    args = parser.parse_args()
    
    # Set up the output folder - in the same directory as the script
    if args.output_folder is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_folder = os.path.join(script_dir, "subtitle_output")
    else:
        output_folder = args.output_folder
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output directory: {output_folder}")
    
    # Initialize the subtitle generator
    subtitle_generator = SubtitleGenerator(model_name=args.model)
    
    # Get list of video files in the input directory
    video_files = []
    for root, _, files in os.walk(args.input_folder):
        for file in files:
            if any(file.lower().endswith(ext) for ext in args.extensions):
                video_files.append(os.path.join(root, file))
    
    if not video_files:
        print(f"No video files found in {args.input_folder} with extensions {args.extensions}")
        return
    
    print(f"Found {len(video_files)} video files to process.")
    
    # Process each video file
    for video_path in tqdm(video_files, desc="Generating subtitles"):
        # Determine output subtitle path
        video_name = os.path.basename(video_path)
        base_name, _ = os.path.splitext(video_name)
        subtitle_path = os.path.join(output_folder, f"{base_name}.srt")
        
        # Check if subtitle already exists
        if os.path.exists(subtitle_path):
            print(f"Subtitle already exists for {video_name}, skipping.")
            continue
        
        # Generate subtitle
        subtitle_generator.generate_subtitle(video_path, subtitle_path)
    
    print("Subtitle generation completed.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
