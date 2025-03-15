import os
import argparse
import whisper
import time
import re
import json
from tqdm import tqdm
from pathlib import Path

class SubtitleGenerator:
    def __init__(self, model_name="base", max_words_per_subtitle=12):
        """
        Initialize the SubtitleGenerator with the specified Whisper model.
        
        Args:
            model_name: Whisper model size to use (tiny, base, small, medium, large)
            max_words_per_subtitle: Maximum number of words per subtitle segment
        """
        print(f"Loading Whisper model '{model_name}'...")
        self.model = whisper.load_model(model_name)
        self.max_words_per_subtitle = max_words_per_subtitle
        print("Model loaded successfully.")
    
    def generate_subtitle(self, video_path, output_path, generate_word_timings=False):
        """
        Generate subtitles for a video file using Whisper.
        
        Args:
            video_path: Path to the input video file
            output_path: Path where the subtitle file will be saved
            generate_word_timings: Whether to generate a JSON file with word timings
        
        Returns:
            bool: True if subtitles were generated successfully, False otherwise
        """
        try:
            print(f"Transcribing video: {os.path.basename(video_path)}")
            
            # Use standard Whisper transcription without additional parameters
            # This ensures compatibility with different Whisper versions
            result = self.model.transcribe(video_path)
            
            # Post-process and refine segments
            refined_segments = self._refine_segments(result)
            
            # Create .srt format
            with open(output_path, 'w', encoding='utf-8') as srt_file:
                for i, segment in enumerate(refined_segments, start=1):
                    # Format start and end times (convert seconds to SRT format)
                    start_time = self._format_time(segment["start"])
                    end_time = self._format_time(segment["end"])
                    
                    # Write subtitle entry
                    srt_file.write(f"{i}\n")
                    srt_file.write(f"{start_time} --> {end_time}\n")
                    srt_file.write(f"{segment['text'].strip()}\n\n")
            
            # Generate word-level timing JSON if requested
            if generate_word_timings:
                self._generate_word_timing_json(result, output_path)
            
            print(f"Subtitle generated successfully: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error generating subtitle for {video_path}: {str(e)}")
            # Check for FFmpeg-related errors
            if "ffmpeg" in str(e).lower() or "pipe" in str(e).lower():
                print("This appears to be an FFmpeg error. Make sure FFmpeg is installed correctly and the video file is valid.")
            return False
    
    def _generate_word_timing_json(self, result, srt_path):
        """
        Generate a JSON file with word-level timing information.
        
        Args:
            result: Whisper transcription result
            srt_path: Path to the SRT file (used to determine JSON file path)
        """
        try:
            # Create a path for the JSON file
            json_path = os.path.splitext(srt_path)[0] + "_words.json"
            
            # Extract word timing information
            word_data = {"words": []}
            
            # Try to extract word-level timing from segments
            for segment in result["segments"]:
                segment_text = segment["text"].strip()
                segment_start = segment["start"]
                segment_end = segment["end"]
                segment_duration = segment_end - segment_start
                
                # Split into words and estimate timing
                words = segment_text.split()
                if len(words) == 0:
                    continue
                    
                # If we have word-level timestamps (available in newer Whisper versions)
                if "words" in segment and segment["words"]:
                    for word_info in segment["words"]:
                        if "word" in word_info and "start" in word_info and "end" in word_info:
                            word_data["words"].append({
                                "word": word_info["word"],
                                "start": word_info["start"],
                                "end": word_info["end"]
                            })
                else:
                    # Estimate word timing based on segment duration
                    word_duration = segment_duration / len(words)
                    for i, word in enumerate(words):
                        word_start = segment_start + (i * word_duration)
                        word_end = word_start + word_duration
                        
                        word_data["words"].append({
                            "word": word,
                            "start": word_start,
                            "end": word_end
                        })
            
            # Save to JSON file
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(word_data, f, indent=2)
                
            print(f"Word timing data saved to: {json_path}")
                
        except Exception as e:
            print(f"Error generating word timing data: {str(e)}")
    
    def _refine_segments(self, result):
        """
        Process Whisper transcription results to create better-sized subtitle segments.
        
        Args:
            result: Whisper transcription result
            
        Returns:
            List of refined subtitle segments
        """
        refined_segments = []
        
        for segment in result["segments"]:
            text = segment["text"].strip()
            words = text.split()
            
            # If the segment is short enough, keep it as is
            if len(words) <= self.max_words_per_subtitle:
                refined_segments.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": text
                })
                continue
                
            # For longer segments, split into smaller chunks based on word count
            # Simple approach that works with all Whisper versions
            segment_duration = segment["end"] - segment["start"]
            words_per_second = len(words) / segment_duration if segment_duration > 0 else 1
            
            for i in range(0, len(words), self.max_words_per_subtitle):
                chunk = words[i:i+self.max_words_per_subtitle]
                # Calculate estimated duration for this chunk
                chunk_duration = len(chunk) / words_per_second if words_per_second > 0 else 2.0
                
                # Calculate time positions
                chunk_start = segment["start"] + (i / words_per_second if words_per_second > 0 else 0)
                chunk_end = min(chunk_start + chunk_duration, segment["end"])
                
                # Add a small gap between segments for readability
                if i > 0:
                    chunk_start += 0.1
                
                refined_segments.append({
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": " ".join(chunk).strip()
                })
        
        return refined_segments
    
    def _format_time(self, seconds):
        """
        Convert seconds to SRT time format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            str: Formatted time string
        """
        # Handle negative times (shouldn't happen but just in case)
        seconds = max(0, seconds)
        
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
    parser.add_argument("--max_words", type=int, default=8,
                        help="Maximum number of words per subtitle (default: 12)")
    parser.add_argument("--word_timings", action="store_true",
                        help="Generate word-level timing data for highlighting")
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
    subtitle_generator = SubtitleGenerator(model_name=args.model, max_words_per_subtitle=args.max_words)
    
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
        subtitle_generator.generate_subtitle(video_path, subtitle_path, generate_word_timings=args.word_timings)
    
    print("Subtitle generation completed.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
