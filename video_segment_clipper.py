import os
import json
import argparse
import subprocess
import time
from datetime import datetime
from tqdm import tqdm
import tempfile
import shutil

class VideoSegmentClipper:
    """
    A class to clip segments from a video based on suggestions.
    """
    
    def __init__(
        self, 
        video_path: str, 
        suggestions_path: str, 
        output_folder: str,
        remove_silence: bool = False,
        silence_threshold: float = -30.0,
        silence_duration: float = 0.5
    ):
        """
        Initialize the VideoSegmentClipper.
        
        Args:
            video_path: Path to the input video
            suggestions_path: Path to the JSON file containing segment suggestions
            output_folder: Path to the output folder where clips will be saved
            remove_silence: Whether to remove silent gaps between conversations
            silence_threshold: Threshold in dB for silence detection (lower means more strict)
            silence_duration: Minimum duration of silence to be detected and removed (in seconds)
        """
        self.video_path = video_path
        self.suggestions_path = suggestions_path
        self.output_folder = output_folder
        self.remove_silence = remove_silence
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output directory: {output_folder}")
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert a time string in format 'HH:MM:SS' or 'HH:MM:SS.mmm' to seconds.
        
        Args:
            time_str: Time string in format 'HH:MM:SS' or 'HH:MM:SS.mmm'
            
        Returns:
            float: Time in seconds
        """
        # Handle different time formats
        if '.' in time_str:
            # Format: HH:MM:SS.mmm
            time_obj = datetime.strptime(time_str, '%H:%M:%S.%f')
            return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second + time_obj.microsecond / 1000000
        else:
            # Format: HH:MM:SS
            time_obj = datetime.strptime(time_str, '%H:%M:%S')
            return time_obj.hour * 3600 + time_obj.minute * 60 + time_obj.second
    
    def _get_video_duration(self) -> float:
        """
        Get the duration of the input video in seconds.
        
        Returns:
            float: Duration in seconds
        """
        try:
            # Use ffprobe to get video duration
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.video_path
            ]
            
            duration = float(subprocess.check_output(cmd, text=True).strip())
            return duration
        except Exception as e:
            print(f"Error getting video duration: {str(e)}")
            return 0
    
    def _clip_exists(self, output_path: str) -> bool:
        """
        Check if a clip already exists in the output folder.
        
        Args:
            output_path: Path to the output clip
            
        Returns:
            bool: True if the clip exists, False otherwise
        """
        return os.path.exists(output_path)
    
    def _clip_segment(
        self, 
        start_time: float, 
        end_time: float, 
        output_path: str,
        title: str = ""
    ) -> bool:
        """
        Clip a segment from the input video with progress display.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Path to save the output clip
            title: Title of the clip for display purposes
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if ffmpeg is installed
            try:
                cmd = ["ffmpeg", "-version"]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("ffmpeg not found. Please install ffmpeg.")
                return False
            
            # Calculate duration
            duration = end_time - start_time
            
            if duration <= 0:
                print(f"Invalid clip duration: {duration} seconds")
                return False
                
            # Get video info to show progress
            info_cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                self.video_path
            ]
            
            try:
                fps_str = subprocess.check_output(info_cmd, text=True).strip()
                if '/' in fps_str:
                    num, denom = map(float, fps_str.split('/'))
                    fps = num / denom
                else:
                    fps = float(fps_str)
            except:
                fps = 30  # Default assumption
                
            # Calculate total frames for progress
            total_frames = int(duration * fps)
            print(f"Creating clip: {title if title else 'Segment'} ({duration:.1f}s, ~{total_frames} frames)")
            
            if not self.remove_silence:
                # Simple clip without silence removal
                cmd = [
                    "ffmpeg",
                    "-y",  # Overwrite output file if it exists
                    "-ss", str(start_time),
                    "-i", self.video_path,
                    "-t", str(duration),
                    "-c", "copy",  # Copy codecs without re-encoding for speed
                    "-progress", "pipe:1",  # Output progress to stdout
                    output_path
                ]
                
                # Run the process with live progress updates
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    bufsize=1
                )
                
                # Track progress variables
                frame_count = 0
                progress_shown = False
                
                # Process the progress output
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                        
                    # Parse frame information
                    if line.startswith('frame='):
                        try:
                            frame_count = int(line.split('=')[1].strip())
                            if total_frames > 0:
                                percent = min(100, int(100 * frame_count / total_frames))
                                progress_bar = f"[{'=' * (percent // 5)}{'>' if percent < 100 else '='}{' ' * (20 - percent // 5)}]"
                                print(f"\rProgress: {progress_bar} {percent}% (Frame {frame_count}/{total_frames})", end="", flush=True)
                                progress_shown = True
                        except:
                            pass
                
                # Get result and clear progress line if shown
                returncode = process.wait()
                if progress_shown:
                    print()  # New line after progress bar
                    
                if returncode != 0:
                    stderr = process.stderr.read()
                    print(f"FFmpeg error: {stderr}")
                    return False
                
                return os.path.exists(output_path)
            else:
                # Clip with silence removal - need to create a temporary file first
                with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
                    temp_path = temp_file.name
                
                try:
                    # First, create the basic clip
                    cmd = [
                        "ffmpeg",
                        "-y",  # Overwrite output file if it exists
                        "-ss", str(start_time),
                        "-i", self.video_path,
                        "-t", str(duration),
                        "-c", "copy",  # Copy codecs without re-encoding for speed
                        "-progress", "pipe:1",  # Output progress to stdout
                        temp_path
                    ]
                    
                    # Run the process with live progress updates
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1
                    )
                    
                    # Track progress variables
                    frame_count = 0
                    progress_shown = False
                    
                    # Process the progress output
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                            
                        # Parse frame information
                        if line.startswith('frame='):
                            try:
                                frame_count = int(line.split('=')[1].strip())
                                if total_frames > 0:
                                    percent = min(100, int(100 * frame_count / total_frames))
                                    progress_bar = f"[{'=' * (percent // 5)}{'>' if percent < 100 else '='}{' ' * (20 - percent // 5)}]"
                                    print(f"\rInitial Clip: {progress_bar} {percent}% (Frame {frame_count}/{total_frames})", end="", flush=True)
                                    progress_shown = True
                            except:
                                pass
                    
                    # Get result and clear progress line if shown
                    returncode = process.wait()
                    if progress_shown:
                        print()  # New line after progress bar
                        
                    if returncode != 0:
                        stderr = process.stderr.read()
                        print(f"FFmpeg error (initial clip): {stderr}")
                        return False
                    
                    # Now remove silence from the temporary clip
                    print("Removing silent gaps...")
                    silence_cmd = [
                        "ffmpeg",
                        "-y",
                        "-i", temp_path,
                        "-af", f"silenceremove=1:0:{self.silence_threshold}dB:{self.silence_duration}:1:{self.silence_threshold}dB:{self.silence_duration}",
                        "-c:v", "copy",
                        output_path
                    ]
                    
                    process = subprocess.run(silence_cmd, capture_output=True, text=True)
                    
                    if process.returncode != 0:
                        print(f"FFmpeg error (silence removal): {process.stderr}")
                        # If silence removal fails, just use the initial clip
                        shutil.copy(temp_path, output_path)
                        print("Silence removal failed. Using the initial clip instead.")
                    else:
                        print("Silence removed successfully.")
                    
                    return os.path.exists(output_path)
                    
                finally:
                    # Clean up temporary file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
        except Exception as e:
            print(f"Error creating clip: {str(e)}")
            return False
    
    def process_suggestions(self) -> None:
        """
        Process all suggestions and create video clips.
        """
        # Load suggestions
        try:
            with open(self.suggestions_path, 'r') as f:
                suggestions = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading suggestions: {e}")
            return
        
        print(f"Loaded {len(suggestions)} suggestions from {self.suggestions_path}")
        
        # Get video duration for validation
        video_duration = self._get_video_duration()
        if video_duration == 0:
            print("Could not determine video duration. Proceeding anyway...")
        
        # Process each suggestion
        successful_clips = 0
        skipped_clips = 0
        video_basename = os.path.basename(self.video_path)
        video_name, _ = os.path.splitext(video_basename)
        
        for i, suggestion in enumerate(tqdm(suggestions, desc="Processing video segments")):
            # Extract information from suggestion
            try:
                start_time_str = suggestion.get('start', '')
                end_time_str = suggestion.get('end', '')
                title = suggestion.get('title', f'Clip_{i+1}')
                hashtags = suggestion.get('hashtags', [])
                
                # Skip if missing critical information
                if not start_time_str or not end_time_str:
                    print(f"Skipping suggestion {i+1}: Missing start or end time")
                    continue
                
                # Convert times to seconds
                start_time = self._time_to_seconds(start_time_str)
                end_time = self._time_to_seconds(end_time_str)
                
                # Validate times
                if start_time >= end_time:
                    print(f"Skipping suggestion {i+1}: Start time ({start_time_str}) is not before end time ({end_time_str})")
                    continue
                
                if video_duration > 0 and end_time > video_duration:
                    print(f"Warning: End time ({end_time_str}) exceeds video duration ({video_duration:.2f}s). Clipping to video end.")
                    end_time = video_duration
                
                # Create output filename (sanitize title to make it filesystem-friendly)
                sanitized_title = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in title)
                sanitized_title = sanitized_title.replace(' ', '_')
                output_filename = f"{sanitized_title}_{start_time_str.replace(':', '-')}_to_{end_time_str.replace(':', '-')}.mp4"
                
                # Truncate filename if longer than 150 chars
                if len(output_filename) > 150:
                    base, ext = os.path.splitext(output_filename)
                    output_filename = base[:146] + ext
                output_path = os.path.join(self.output_folder, output_filename)
                
                # Check if clip already exists
                if self._clip_exists(output_path):
                    print(f"Skipping suggestion {i+1}: Clip already exists at {output_path}")
                    skipped_clips += 1
                    continue
                
                # Display progress
                print(f"Processing clip {i+1}/{len(suggestions)} - {title}")
                print(f"  Start: {start_time_str}, End: {end_time_str}, Duration: {end_time-start_time:.2f}s")
                if hashtags:
                    print(f"  Hashtags: {' '.join(hashtags)}")
                
                # Clip the segment
                start_time_clip = time.time()
                success = self._clip_segment(start_time, end_time, output_path, title)
                end_time_clip = time.time()
                
                if success:
                    print(f"  Successfully created clip: {output_filename}")
                    print(f"  Processing time: {end_time_clip - start_time_clip:.2f}s")
                    successful_clips += 1
                else:
                    print(f"  Failed to create clip!")
                
            except Exception as e:
                print(f"Error processing suggestion {i+1}: {str(e)}")
                continue
        
        print(f"\nProcessing completed:")
        print(f"  Successfully created {successful_clips} clips")
        print(f"  Skipped {skipped_clips} existing clips")
        print(f"  Total suggestions: {len(suggestions)}")
        print(f"  Output folder: {self.output_folder}")

def main():
    """Main function to run when script is executed directly."""
    parser = argparse.ArgumentParser(description="Clip video segments based on suggestions")
    parser.add_argument("video", help="Path to the input video file")
    parser.add_argument("suggestions", help="Path to the JSON file containing segment suggestions")
    parser.add_argument("output_folder", help="Path to the output folder where clips will be saved")
    parser.add_argument("--remove-silence", action="store_true", help="Remove silent gaps between conversations")
    parser.add_argument("--silence-threshold", type=float, default=-30.0, help="Threshold in dB for silence detection (default: -30.0)")
    parser.add_argument("--silence-duration", type=float, default=0.5, help="Minimum duration of silence to be detected and removed in seconds (default: 0.5)")
    args = parser.parse_args()
    
    # Validate input paths
    if not os.path.exists(args.video):
        print(f"Error: Input video file '{args.video}' does not exist")
        return
    
    if not os.path.exists(args.suggestions):
        print(f"Error: Suggestions file '{args.suggestions}' does not exist")
        return
    
    # Initialize clipper and process suggestions
    start_time = time.time()
    clipper = VideoSegmentClipper(
        video_path=args.video,
        suggestions_path=args.suggestions,
        output_folder=args.output_folder,
        remove_silence=args.remove_silence,
        silence_threshold=args.silence_threshold,
        silence_duration=args.silence_duration
    )
    
    # Process video segments
    try:
        clipper.process_suggestions()
        end_time = time.time()
        print(f"Total processing time: {end_time - start_time:.2f} seconds")
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
    except Exception as e:
        print(f"Error during processing: {str(e)}")


if __name__ == "__main__":
    main()
