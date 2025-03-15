import os
import cv2
import argparse
import re
import time
import tempfile
import subprocess
import json
import math
from tqdm import tqdm
from typing import Dict, List, Optional

class SubtitleEntry:
    """Class representing a single subtitle entry."""
    def __init__(self, index: int, start_time: float, end_time: float, text: str, word_timings: List[Dict] = None):
        self.index = index
        self.start_time = start_time
        self.end_time = end_time
        self.text = text
        # Word timings is a list of dictionaries with word, start, end times
        self.word_timings = word_timings or []

    def __repr__(self):
        return f"SubtitleEntry({self.index}, {self.start_time:.2f}, {self.end_time:.2f}, '{self.text}')"

class SubtitleProcessor:
    def __init__(self, videos_folder: str, subtitles_folder: str, output_folder: str, highlight_style: str = None, animation_style: str = "bounce"):
        """
        Initialize the SubtitleProcessor.
        
        Args:
            videos_folder: Path to the folder containing video files
            subtitles_folder: Path to the folder containing subtitle files (.srt)
            output_folder: Path where the output videos with subtitles will be saved
            highlight_style: Style of word highlighting ('standard', 'bigword', or None)
            animation_style: Animation style for bigword mode ('bounce' or 'scale')
        """
        self.videos_folder = videos_folder
        self.subtitles_folder = subtitles_folder
        self.output_folder = output_folder
        self.highlight_style = highlight_style
        self.animation_style = animation_style
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output directory: {output_folder}")
        
        # For animations
        self.animation_oscillator = 0
    
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
        
        # Check if there's a json file with word timings available
        word_timing_path = os.path.join(self.subtitles_folder, f"{base_name}_words.json")
        if self.highlight_style and os.path.exists(word_timing_path):
            self._add_word_timings_to_subtitles(subtitles, word_timing_path)
        
        # Process video with subtitles
        try:
            self._process_video_with_subtitles(video_path, subtitles)
            print(f"Successfully processed video: {video_name}")
        except Exception as e:
            print(f"Error processing video {video_name}: {str(e)}")
    
    def _add_word_timings_to_subtitles(self, subtitles: List[SubtitleEntry], word_timing_path: str):
        """
        Add word-level timings to subtitle entries from a JSON file.
        
        Args:
            subtitles: List of subtitle entries
            word_timing_path: Path to JSON file with word timings
        """
        try:
            with open(word_timing_path, 'r', encoding='utf-8') as f:
                word_data = json.load(f)
            
            if 'words' not in word_data:
                print(f"Invalid word timing format in {word_timing_path}")
                return
            
            # Group words by subtitle segments
            for subtitle in subtitles:
                subtitle.word_timings = []
                
                # Find words that fall within this subtitle's time range
                for word_info in word_data['words']:
                    word_start = word_info.get('start', 0)
                    word_end = word_info.get('end', 0)
                    word_text = word_info.get('word', '')
                    
                    # If word overlaps with subtitle timing, add it
                    if (word_start >= subtitle.start_time and word_start < subtitle.end_time) or \
                       (word_end > subtitle.start_time and word_end <= subtitle.end_time) or \
                       (word_start <= subtitle.start_time and word_end >= subtitle.end_time):
                        subtitle.word_timings.append({
                            'word': word_text,
                            'start': word_start,
                            'end': word_end
                        })
                
        except Exception as e:
            print(f"Error loading word timings from {word_timing_path}: {str(e)}")
    
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
        font_scale = width / 640  # Base scale for regular subtitles
        
        # Reset animation oscillator for this video
        self.animation_oscillator = 0
        
        # Define animation cycle - use a slightly longer cycle for scale animation
        bounce_cycle = int(fps * 0.6)  # 0.6 seconds for bounce
        scale_cycle = int(fps * 1.2)   # 1.2 seconds for scale (slower)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Calculate current time in seconds
            current_time = frame_count / fps
            
            # Update animation oscillator based on the animation style
            if self.animation_style == "bounce":
                self.animation_oscillator = (self.animation_oscillator + 1) % bounce_cycle
            else:  # scale
                self.animation_oscillator = (self.animation_oscillator + 1) % scale_cycle
            
            # Find active subtitles for current time
            active_subtitle = self._get_active_subtitle(subtitles, current_time)
            
            # Add subtitle text to frame if there's an active subtitle
            if active_subtitle:
                if self.highlight_style == 'standard' and active_subtitle.word_timings:
                    frame = self._add_highlighted_text_to_frame(frame, active_subtitle, current_time, font_scale)
                elif self.highlight_style == 'bigword' and active_subtitle.word_timings:
                    frame = self._add_big_word_to_frame(frame, active_subtitle, current_time, font_scale, fps)
                else:
                    frame = self._add_text_to_frame(frame, active_subtitle.text, font_scale)
            
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
    
    def _get_active_subtitle(self, subtitles: List[SubtitleEntry], current_time: float) -> Optional[SubtitleEntry]:
        """
        Get the subtitle entry active at the current time.
        
        Args:
            subtitles: List of subtitle entries
            current_time: Current time in the video (seconds)
            
        Returns:
            Active subtitle entry or None if no active subtitle
        """
        for subtitle in subtitles:
            if subtitle.start_time <= current_time <= subtitle.end_time:
                return subtitle
        
        return None
    
    def _add_big_word_to_frame(self, frame, subtitle: SubtitleEntry, current_time: float, font_scale: float, fps: float):
        """
        Add only the current word to the frame with large text and animation.
        
        Args:
            frame: Input video frame
            subtitle: Subtitle entry with word timings
            current_time: Current time in seconds
            font_scale: Base font scale factor
            fps: Frames per second of the video
            
        Returns:
            Frame with big word added
        """
        # Get frame dimensions
        height, width, _ = frame.shape
        
        # Find current word
        current_word = ""
        word_progress = 0.0  # How far we are through the current word (0.0 to 1.0)
        
        for word_info in subtitle.word_timings:
            if word_info['start'] <= current_time <= word_info['end']:
                current_word = word_info['word']
                word_duration = word_info['end'] - word_info['start']
                if word_duration > 0:
                    word_progress = (current_time - word_info['start']) / word_duration
                break
        
        if not current_word:
            return frame  # No current word to display
        
        # Set up font properties - much larger for the big word style
        big_font_scale = font_scale * 2.5  # Much bigger than regular subtitles
        font = cv2.FONT_HERSHEY_DUPLEX
        
        # Apply animations based on selected style
        if self.animation_style == "bounce":
            # Bounce animation
            # Calculate the bounce effect (subtle up and down movement)
            bounce_cycle = int(fps * 0.6)
            bounce_height = 20 * font_scale  # Maximum bounce height in pixels
            bounce_position = math.sin(self.animation_oscillator / bounce_cycle * 2 * math.pi) * bounce_height
            
            # Animation parameters
            thickness = max(2, int(big_font_scale * 2.5))  # Bold text
            final_font_scale = big_font_scale  # No scaling in bounce mode
            y_offset = int(bounce_position)
            
            # Get text dimensions
            (text_width, text_height), _ = cv2.getTextSize(current_word, font, final_font_scale, thickness)
            
            # Position the word at 70% of the screen height with bounce effect
            x_position = (width - text_width) // 2
            y_position = int(height * 0.7) + y_offset
            
            # Draw background for better readability - rounded rectangle
            background_padding = int(20 * font_scale)
            background_rect = (
                x_position - background_padding, 
                y_position - text_height - background_padding,
                text_width + 2 * background_padding,
                text_height + 2 * background_padding
            )
            
            # Draw rounded rectangle background
            cv2.rectangle(
                frame,
                (background_rect[0], background_rect[1]),
                (background_rect[0] + background_rect[2], background_rect[1] + background_rect[3]),
                (0, 0, 0),
                -1
            )
            
            # Draw text with bright yellow color
            text_color = (255, 255, 100)  # Bright yellow
            cv2.putText(frame, current_word, (x_position, y_position), font, final_font_scale, text_color, thickness)
            
        else:  # "scale" animation
            # Scale animation
            scale_cycle = int(fps * 1.2)  # Slowed down to 1.2 seconds
            scale_factor = 0.9 + 0.1 * math.sin(self.animation_oscillator / scale_cycle * math.pi) ** 2  # Range from 0.9 to 1.0
            
            # Animation parameters
            final_font_scale = big_font_scale * scale_factor
            thickness = max(2, int(final_font_scale * 1.5))  # Thinner for scale mode
            y_offset = 0  # No vertical movement in scale mode
            
            # Get text dimensions for current scale
            (text_width, text_height), _ = cv2.getTextSize(current_word, font, final_font_scale, thickness)
            
            # Position the word at 70% of the screen height
            x_position = (width - text_width) // 2
            y_position = int(height * 0.7)
            
            # Draw text with black outline (no background)
            text_color = (230, 230, 100)  # Light yellow
            outline_color = (0, 0, 0)  # Black outline
            
            # Draw the outline (thicker for better visibility)
            outline_thickness = thickness + 2
            for offset_x in [-2, -1, 0, 1, 2]:
                for offset_y in [-2, -1, 0, 1, 2]:
                    if offset_x != 0 or offset_y != 0:
                        cv2.putText(
                            frame, 
                            current_word, 
                            (x_position + offset_x, y_position + offset_y), 
                            font, 
                            final_font_scale, 
                            outline_color, 
                            outline_thickness
                        )
            
            # Draw the text
            cv2.putText(
                frame, 
                current_word, 
                (x_position, y_position), 
                font, 
                final_font_scale, 
                text_color, 
                thickness
            )
        
        return frame
    
    def _add_highlighted_text_to_frame(self, frame, subtitle: SubtitleEntry, current_time: float, font_scale: float):
        """
        Add subtitle text to a frame with the current word highlighted.
        
        Args:
            frame: Input video frame
            subtitle: Subtitle entry with word timings
            current_time: Current time in seconds
            font_scale: Font scale factor
            
        Returns:
            Frame with highlighted subtitle text
        """
        # Get frame dimensions
        height, width, _ = frame.shape
        
        # Set text properties
        font = cv2.FONT_HERSHEY_DUPLEX
        thickness = max(1, int(font_scale * 2))  # Scale thickness with font size
        regular_color = (255, 255, 255)  # White for regular text
        highlight_color = (255, 255, 0)  # Yellow for highlighted word
        
        # Prepare text with highlighted word
        # First, build the full text with markers for the currently spoken word
        full_text = subtitle.text
        highlighted_word = ""
        
        # Find which word should be highlighted based on timing
        for word_info in subtitle.word_timings:
            if word_info['start'] <= current_time <= word_info['end']:
                highlighted_word = word_info['word']
                break
        
        # If no word is currently being spoken, just render the regular text
        if not highlighted_word:
            return self._add_text_to_frame(frame, full_text, font_scale)
        
        # Split text into words for rendering
        words = full_text.split()
        
        # Calculate position (at 70% of video height)
        line_height = int(50 * font_scale)  # Increased for better spacing with larger text
        
        # Measure total text width for centering
        total_text_width = 0
        word_widths = []
        
        for word in words:
            (text_width, _), _ = cv2.getTextSize(word, font, font_scale, thickness)
            word_widths.append(text_width)
            total_text_width += text_width
            # Add space width
            space_width = int(text_width * 0.3)  # Approximate space width as 30% of word width
            if total_text_width > 0:  # Don't add space before first word
                total_text_width += space_width
        
        # Position text at approximately 70% of frame height
        y_position = int(height * 0.7)
        
        # Wrap the subtitle text over multiple lines if it's too wide
        wrapped_lines = []
        current_line = []
        current_line_width = 0
        max_line_width = width - 100  # Leave margin
        
        for i, word in enumerate(words):
            # Calculate width with space
            word_width = word_widths[i]
            space_width = int(word_width * 0.3) if i > 0 else 0
            
            # Check if adding this word would make line too long
            if current_line_width + word_width + space_width > max_line_width and current_line:
                wrapped_lines.append(current_line)
                current_line = [word]
                current_line_width = word_width
            else:
                current_line.append(word)
                current_line_width += word_width + space_width
        
        # Add the last line if it has content
        if current_line:
            wrapped_lines.append(current_line)
        
        # Limit to 3 lines maximum
        if len(wrapped_lines) > 3:
            wrapped_lines = wrapped_lines[:3]
            # Add ellipsis to last line if it's not the end
            if len(wrapped_lines[-1]) > 1:
                wrapped_lines[-1][-1] += "..."
        
        # Calculate total height of all lines
        total_text_height = line_height * len(wrapped_lines)
        y_start = y_position - (total_text_height // 2)
        
        # Render each line
        for line_idx, line_words in enumerate(wrapped_lines):
            # Calculate line width for centering
            line_width = sum(word_widths[words.index(word)] for word in line_words) + \
                        sum(int(word_widths[words.index(word)] * 0.3) for word in line_words[1:])
            
            x_start = (width - line_width) // 2
            current_x = x_start
            line_y = y_start + (line_idx * line_height) + 30
            
            # Render each word in the line
            for word in line_words:
                # Get word width
                word_idx = words.index(word)
                word_width = word_widths[word_idx]
                
                # Determine if this word should be highlighted
                is_highlighted = word.strip('.,?!:;') == highlighted_word.strip('.,?!:;')
                word_color = highlight_color if is_highlighted else regular_color
                
                # Draw black outline/background
                for offset_x in [-2, -1, 0, 1, 2]:
                    for offset_y in [-2, -1, 0, 1, 2]:
                        if offset_x != 0 or offset_y != 0:
                            cv2.putText(frame, word, 
                                       (current_x + offset_x, line_y + offset_y), 
                                       font, font_scale, (0, 0, 0), thickness + 1)
                
                # Draw text with appropriate color
                cv2.putText(frame, word, (current_x, line_y), font, font_scale, word_color, thickness)
                
                # Move x position for next word
                space_width = int(word_width * 0.3)
                current_x += word_width + space_width
        
        return frame
    
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
    parser.add_argument("--highlight", choices=["standard", "bigword"], 
                        help="Highlighting style: 'standard' for highlighting within text, 'bigword' for showing only the current word in large text")
    parser.add_argument("--animation", choices=["bounce", "scale"], default="bounce",
                        help="Animation style for bigword mode: 'bounce' for bouncing animation, 'scale' for scaling animation (default: bounce)")
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
        output_folder=output_folder,
        highlight_style=args.highlight,
        animation_style=args.animation
    )
    
    # Process videos
    processor.process_videos(video_extensions=args.extensions)
    
    print("Video processing completed.")

if __name__ == "__main__":
    start_time = time.time()
    main()
    end_time = time.time()
    print(f"Total processing time: {end_time - start_time:.2f} seconds")
