import os
import cv2
import argparse
import re
import time
import tempfile
import subprocess
from pathlib import Path
from tqdm import tqdm
from typing import Dict, List, Tuple, Optional

class SubtitleEntry:
    """Class representing a single subtitle entry."""
    def __init__(self, index: int, start_time: float, end_time: float, text: str):
        self.index = index
        self.start_time = start_time
        self.end_time = end_time
        self.text = text

    def __repr__(self):
        return f"SubtitleEntry({self.index}, {self.start_time:.2f}, {self.end_time:.2f}, '{self.text}')"

class SubtitleProcessor:
    def __init__(self, videos_folder: str, subtitles_folder: str, output_folder: str):
        """
        Initialize the SubtitleProcessor.
        
        Args:
            videos_folder: Path to the folder containing video files
            subtitles_folder: Path to the folder containing subtitle files (.srt)
            output_folder: Path where the output videos with subtitles will be saved
        """
        self.videos_folder = videos_folder
        self.subtitles_folder = subtitles_folder
        self.output_folder = output_folder
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output directory: {output_folder}")
    
    def process_videos(self, video_extensions: List[str] = None):
        """
        Process all videos in the videos folder by adding subtitles.
        
        Args:
            video_extensions: List of video file extensions to process
        """
        if video_extensions is None:
            video_extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm"]
        
        # Get list of video files
        video_files = []
        for root, _, files in os.walk(self.videos_folder):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(root, file))
        
        if not video_files:
            print(f"No video files found in {self.videos_folder} with extensions {video_extensions}")
            return
        
        print(f"Found {len(video_files)} video files to process.")
        
        # Process each video file
        for video_path in tqdm(video_files, desc="Processing videos"):
            self.add_subtitles_to_video(video_path)
    
    def add_subtitles_to_video(self, video_path: str):
        """
        Add subtitles to a video file.
        
        Args:
            video_path: Path to the input video file
        """
        # Get video name and find corresponding subtitle file
        video_name = os.path.basename(video_path)
        base_name, _ = os.path.splitext(video_name)
        subtitle_path = os.path.join(self.subtitles_folder, f"{base_name}.srt")
        
        # Check if subtitle file exists
        if not os.path.exists(subtitle_path):
            print(f"Subtitle not found for {video_name}, skipping.")
            return
        
        # Parse subtitle file
        subtitles = self.parse_srt(subtitle_path)
        if not subtitles:
            print(f"No valid subtitles found in {subtitle_path}, skipping.")
            return
        
        # Process video with subtitles
        try:
            self._process_video_with_subtitles(video_path, subtitles)
            print(f"Successfully processed video: {video_name}")
        except Exception as e:
            print(f"Error processing video {video_name}: {str(e)}")
    
    def _process_video_with_subtitles(self, video_path: str, subtitles: List[SubtitleEntry]):
        """
        Add subtitles to video and save the new video.
        
        Args:
            video_path: Path to input video
            subtitles: List of subtitle entries
        """
        # Create temporary file for video without audio
        temp_video_file = os.path.join(tempfile.gettempdir(), f"temp_subtitle_video_{int(time.time())}.mp4")
        
        # Open video file
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")
        
        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Set up video writer for output
        video_name = os.path.basename(video_path)
        base_name, ext = os.path.splitext(video_name)
        output_path = os.path.join(self.output_folder, f"{base_name}_with_subtitles{ext}")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_video_file, fourcc, fps, (width, height))
        
        frame_count = 0
        current_time = 0
        
        # Calculate font scale based on video width (increased for larger text)
        font_scale = width / 640  # Increased scale for bigger text
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate current time in seconds
            current_time = frame_count / fps
            
            # Find active subtitles for current time
            active_text = self._get_active_subtitle_text(subtitles, current_time)
            
            # Add subtitle text to frame if there's active text
            if active_text:
                frame = self._add_text_to_frame(frame, active_text, font_scale)
            
            # Write the frame to output video
            out.write(frame)
            
            frame_count += 1
            if frame_count % 500 == 0:
                print(f"Processed {frame_count}/{total_frames} frames ({(frame_count/total_frames)*100:.1f}%)")
        
        # Release OpenCV resources
        cap.release()
        out.release()
        
        # Add audio from the original file to the output
        self._add_audio_to_video(video_path, temp_video_file, output_path)
        
        # Remove the temporary file
        if os.path.exists(temp_video_file):
            os.remove(temp_video_file)
            
        print(f"Video with subtitles saved to: {output_path}")
    
    def _add_audio_to_video(self, input_video: str, subtitle_video: str, output_video: str):
        """
        Extract audio from input video and add it to the subtitle video.
        
        Args:
            input_video: Original video with audio
            subtitle_video: Video with subtitles but no audio
            output_video: Final output file path
        """
        try:
            # Use FFmpeg to combine the video with the original audio
            cmd = [
                'ffmpeg',
                '-i', subtitle_video,     # Video with subtitles
                '-i', input_video,        # Original file with audio
                '-c:v', 'copy',           # Copy video stream without re-encoding
                '-c:a', 'aac',            # Audio codec
                '-map', '0:v:0',          # Use video from first input
                '-map', '1:a:0',          # Use audio from second input
                '-shortest',              # Finish encoding when the shortest input stream ends
                output_video              # Output file
            ]
            
            print("Adding audio to the video...")
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
                
        except subprocess.CalledProcessError as e:
            print(f"Error adding audio: {e}")
            print("Saving video without audio...")
            if os.path.exists(subtitle_video):
                os.rename(subtitle_video, output_video)
        except FileNotFoundError:
            print("FFmpeg not found. Please install FFmpeg to add audio to the video.")
            print("Saving video without audio...")
            if os.path.exists(subtitle_video):
                os.rename(subtitle_video, output_video)
    
    def _get_active_subtitle_text(self, subtitles: List[SubtitleEntry], current_time: float) -> str:
        """
        Get the text of active subtitles at the current time.
        
        Args:
            subtitles: List of subtitle entries
            current_time: Current time in the video (seconds)
            
        Returns:
            Active subtitle text or empty string if no active subtitle
        """
        for subtitle in subtitles:
            if subtitle.start_time <= current_time <= subtitle.end_time:
                return subtitle.text
        
        return ""
    
    def _add_text_to_frame(self, frame, text: str, font_scale: float):
        """
        Add subtitle text to a video frame.
        
        Args:
            frame: Input video frame
            text: Subtitle text to add
            font_scale: Font scale factor based on video width
            
        Returns:
            Frame with subtitle text added
        """
        # Get frame dimensions
        height, width, _ = frame.shape
        
        # Set text properties
        font = cv2.FONT_HERSHEY_DUPLEX
        thickness = max(1, int(font_scale * 2))  # Scale thickness with font size
        color = (255, 255, 255)  # White text
        
        # Wrap text to fit width and limit to max 3 lines
        wrapped_text = self._wrap_text(text, font, font_scale, thickness, width - 100, max_lines=3)  
        
        # Calculate position (at 70% of video height)
        text_lines = wrapped_text.split('\n')
        line_height = int(50 * font_scale)  # Increased for better spacing with larger text
        total_text_height = line_height * len(text_lines)
        
        # Position text at approximately 70% of frame height
        y_position = int(height * 0.7) - (total_text_height // 2)
        
        # Add black outline/background for better readability
        for i, line in enumerate(text_lines):
            # Calculate text position for centered text
            text_size = cv2.getTextSize(line, font, font_scale, thickness)[0]
            x_position = (width - text_size[0]) // 2
            line_y_position = y_position + (i * line_height) + 30
            
            # Draw black outline/background (thicker for better visibility)
            for offset_x in [-2, -1, 0, 1, 2]:
                for offset_y in [-2, -1, 0, 1, 2]:
                    if offset_x != 0 or offset_y != 0:  # Skip the center point
                        cv2.putText(frame, line, 
                                   (x_position + offset_x, line_y_position + offset_y), 
                                   font, font_scale, (0, 0, 0), thickness + 1)
            
            # Draw white text
            cv2.putText(frame, line, (x_position, line_y_position), font, font_scale, color, thickness)
        
        return frame
    
    def _wrap_text(self, text: str, font, font_scale: float, thickness: int, max_width: int, max_lines: int = 3) -> str:
        """
        Wrap text to fit within specified width and limit to a maximum number of lines.
        
        Args:
            text: Input text
            font: OpenCV font
            font_scale: Font scale factor
            thickness: Text thickness
            max_width: Maximum width for the text
            max_lines: Maximum number of lines to generate
            
        Returns:
            Text with line breaks added as needed, limited to max_lines
        """
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            # Try adding the word to the current line
            test_line = current_line + [word]
            test_text = ' '.join(test_line)
            
            # Check if the line fits
            text_size = cv2.getTextSize(test_text, font, font_scale, thickness)[0]
            
            if text_size[0] <= max_width:
                # Word fits, add it to the line
                current_line = test_line
            else:
                # Word doesn't fit, start a new line
                if current_line:  # Only add if line has content
                    lines.append(' '.join(current_line))
                current_line = [word]
                
                # If we've reached the maximum number of lines, we need to truncate
                if len(lines) >= max_lines - 1 and current_line:  # -1 to account for the current line
                    break
        
        # Add the last line if it has content
        if current_line and len(lines) < max_lines:
            lines.append(' '.join(current_line))
        
        # If we have too many lines, truncate and add ellipsis
        if len(lines) > max_lines:
            lines = lines[:max_lines-1]
            last_line = lines[-1]
            if len(last_line) > 3:
                lines[-1] = last_line[:-3] + "..."
            else:
                lines[-1] = last_line + "..."
        
        return '\n'.join(lines)
    
    def parse_srt(self, srt_file: str) -> List[SubtitleEntry]:
        """
        Parse an SRT subtitle file into subtitle entries.
        
        Args:
            srt_file: Path to the SRT file
            
        Returns:
            List of SubtitleEntry objects
        """
        subtitles = []
        
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content by double newline to get entries
            entries = re.split(r'\n\s*\n', content.strip())
            
            for entry in entries:
                lines = entry.strip().split('\n')
                
                if len(lines) < 3:
                    continue  # Invalid entry
                
                # Parse entry index
                try:
                    index = int(lines[0])
                except ValueError:
                    continue  # Invalid index
                
                # Parse timestamps
                timestamp_match = re.match(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})', lines[1])
                if not timestamp_match:
                    continue  # Invalid timestamp
                
                # Convert timestamps to seconds
                start_time = (int(timestamp_match.group(1)) * 3600 +  # hours
                             int(timestamp_match.group(2)) * 60 +     # minutes
                             int(timestamp_match.group(3)) +          # seconds
                             int(timestamp_match.group(4)) / 1000)    # milliseconds
                
                end_time = (int(timestamp_match.group(5)) * 3600 +    # hours
                           int(timestamp_match.group(6)) * 60 +       # minutes
                           int(timestamp_match.group(7)) +            # seconds
                           int(timestamp_match.group(8)) / 1000)      # milliseconds
                
                # Get subtitle text (can be multiple lines)
                text = ' '.join(lines[2:])
                
                # Create and add entry
                subtitles.append(SubtitleEntry(index, start_time, end_time, text))
            
            return subtitles
            
        except Exception as e:
            print(f"Error parsing subtitle file {srt_file}: {str(e)}")
            return []

def main():
    parser = argparse.ArgumentParser(description="Add subtitles directly to video files")
    parser.add_argument("videos_folder", help="Path to folder containing video files")
    parser.add_argument("subtitles_folder", help="Path to folder containing subtitle (.srt) files")
    parser.add_argument("--output_folder", help="Path to output folder (default: subtitle_video_output)",
                        default=None)
    parser.add_argument("--extensions", nargs="+", 
                        default=[".mp4", ".avi", ".mov", ".mkv", ".webm"],
                        help="Video file extensions to process (default: .mp4 .avi .mov .mkv .webm)")
    args = parser.parse_args()
    
    # Set up the output folder - in the same directory as the script
    if args.output_folder is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_folder = os.path.join(script_dir, "subtitle_video_output")
    else:
        output_folder = args.output_folder
    
    # Initialize the subtitle processor
    processor = SubtitleProcessor(
        videos_folder=args.videos_folder,
        subtitles_folder=args.subtitles_folder,
        output_folder=output_folder
    )
    
    # Process videos
    processor.process_videos(video_extensions=args.extensions)
    
    print("Video processing completed.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
