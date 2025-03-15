import cv2
import numpy as np
import mediapipe as mp
import argparse
import os
import random
import time
import subprocess
import tempfile
from typing import Tuple, List, Dict, Optional

class VerticalVideoClipper:
    def __init__(self, input_file: str, output_file: str, width: int = 1080, height: int = 1920):
        """
        Initialize the VerticalVideoClipper.
        
        Args:
            input_file: Path to the input landscape video file
            output_file: Path where the output vertical video will be saved
            width: Width of the output vertical video (default: 1080)
            height: Height of the output vertical video (default: 1920)
        """
        self.input_file = input_file
        self.output_file = output_file
        self.temp_video_file = os.path.join(tempfile.gettempdir(), "temp_vertical_video.mp4")
        self.output_width = width
        self.output_height = height
        
        # Initialize video capture
        self.cap = cv2.VideoCapture(input_file)
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video file: {input_file}")
        
        # Get video properties
        self.input_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.input_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Initialize MediaPipe for person detection
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Calculate crop dimensions while maintaining aspect ratio
        # First determine the vertical crop height (same as input height)
        self.crop_height = self.input_height
        
        # Calculate the width needed to maintain 9:16 aspect ratio
        self.crop_width = int(self.crop_height * (self.output_width / self.output_height))
        
        # If calculated crop width is larger than input width, adjust both dimensions
        if self.crop_width > self.input_width:
            self.crop_width = self.input_width
            self.crop_height = int(self.crop_width * (self.output_height / self.output_width))
            
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(
            self.temp_video_file, fourcc, self.fps, (self.output_width, self.output_height)
        )
        
        # Variables for smooth camera movement
        self.last_crop_x = (self.input_width - self.crop_width) // 2  # Start in the middle
        self.last_crop_y = (self.input_height - self.crop_height) // 2  # Start in the middle if needed
        
        # Variables for zoom effect (reduced amplitude)
        self.zoom_state = "neutral"  # neutral, zooming_in, zooming_out
        self.zoom_factor = 1.0
        self.zoom_duration = 0
        self.zoom_step = 0
        self.frames_since_last_zoom = 0
        self.min_zoom = 1.0
        self.max_zoom = 1.1  # Reduced from 1.2 to 1.1 for subtler effect
        
    def detect_person(self, frame) -> Optional[Tuple[int, int]]:
        """
        Detect people in the frame and return the center point of the main person.
        
        Args:
            frame: The input video frame
            
        Returns:
            Tuple (x, y) of the center point of the main person, or None if no person is detected
        """
        # Convert to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        
        if results.pose_landmarks:
            # Calculate the center point based on visible landmarks
            visible_landmarks = []
            for idx, landmark in enumerate(results.pose_landmarks.landmark):
                # Only use landmarks with good visibility
                if landmark.visibility > 0.5:
                    x = int(landmark.x * frame.shape[1])
                    y = int(landmark.y * frame.shape[0])
                    visible_landmarks.append((x, y))
            
            if visible_landmarks:
                # Calculate center of the person using the average of visible landmarks
                center_x = sum(x for x, y in visible_landmarks) // len(visible_landmarks)
                center_y = sum(y for x, y in visible_landmarks) // len(visible_landmarks)
                return center_x, center_y
                
        return None
    
    def apply_zoom_effect(self, crop_x: int, crop_y: int, crop_width: int, crop_height: int) -> Tuple[int, int, int, int]:
        """
        Apply zoom effects to make the video more dynamic, but with reduced intensity.
        
        Args:
            crop_x: Current crop x position
            crop_y: Current crop y position
            crop_width: Current crop width
            crop_height: Current crop height
            
        Returns:
            Tuple of (new_crop_x, new_crop_y, new_crop_width, new_crop_height)
        """
        # Update zoom state with less frequent changes
        if self.zoom_state == "neutral":
            self.frames_since_last_zoom += 1
            
            # Randomly start a new zoom after a longer period (reduced frequency)
            if self.frames_since_last_zoom > random.randint(120, 300):  # Increased from 60-180 to 120-300
                self.zoom_state = random.choice(["zooming_in", "zooming_out"])
                self.zoom_duration = random.randint(150, 210)  # Increased duration for smoother effect
                
                # Reduced zoom step for less dramatic movement
                self.zoom_step = (random.uniform(0.05, 0.08) if self.zoom_state == "zooming_in" 
                                 else -random.uniform(0.03, 0.05)) / self.zoom_duration
                self.frames_since_last_zoom = 0
                
        elif self.zoom_state == "zooming_in":
            self.zoom_factor += self.zoom_step
            self.zoom_duration -= 1
            
            if self.zoom_duration <= 0 or self.zoom_factor >= self.max_zoom:
                self.zoom_state = "neutral"
                self.zoom_factor = min(self.zoom_factor, self.max_zoom)
                self.frames_since_last_zoom = 0
                
        elif self.zoom_state == "zooming_out":
            self.zoom_factor += self.zoom_step
            self.zoom_duration -= 1
            
            if self.zoom_duration <= 0 or self.zoom_factor <= self.min_zoom:
                self.zoom_state = "neutral"
                self.zoom_factor = max(self.zoom_factor, self.min_zoom)
                self.frames_since_last_zoom = 0
        
        # Apply zoom effect while maintaining aspect ratio
        adjusted_crop_width = int(crop_width / self.zoom_factor)
        adjusted_crop_height = int(crop_height / self.zoom_factor)
        
        # Ensure we maintain the correct aspect ratio
        aspect_ratio = self.output_width / self.output_height
        if adjusted_crop_width / adjusted_crop_height != aspect_ratio:
            # Recalculate to maintain aspect ratio
            adjusted_crop_width = int(adjusted_crop_height * aspect_ratio)
        
        # Center the zoom
        adjusted_crop_x = crop_x + (crop_width - adjusted_crop_width) // 2
        adjusted_crop_y = crop_y + (crop_height - adjusted_crop_height) // 2
        
        return adjusted_crop_x, adjusted_crop_y, adjusted_crop_width, adjusted_crop_height
    
    def process(self):
        """Process the input video and create a vertical video output with audio."""
        frame_count = 0
        target_x = self.last_crop_x  # Start with center crop
        target_y = self.last_crop_y
        
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
                
            frame_count += 1
            if frame_count % 100 == 0:
                print(f"Processing frame {frame_count}/{self.total_frames} ({(frame_count/self.total_frames)*100:.1f}%)")
            
            # Detect person in the frame
            person_center = self.detect_person(frame)
            
            if person_center:
                # Calculate the target x position for cropping
                center_x, center_y = person_center
                
                # Make sure we don't go out of bounds with the crop
                max_x = self.input_width - self.crop_width
                max_y = self.input_height - self.crop_height
                target_x = max(0, min(max_x, center_x - self.crop_width // 2))
                target_y = max(0, min(max_y, center_y - self.crop_height // 2))
            
            # Apply smooth transition to target position (reduced smoothing factor for less movement)
            smoothing_factor = 0.05  # Reduced from 0.1 to 0.05 for smoother, slower transitions
            self.last_crop_x = int(self.last_crop_x * (1 - smoothing_factor) + target_x * smoothing_factor)
            self.last_crop_y = int(self.last_crop_y * (1 - smoothing_factor) + target_y * smoothing_factor)
            
            # Apply zoom effect with maintained aspect ratio
            crop_x, crop_y, crop_width, crop_height = self.apply_zoom_effect(
                self.last_crop_x, self.last_crop_y, self.crop_width, self.crop_height
            )
            
            # Make sure we don't go out of bounds after zoom
            if crop_x < 0:
                crop_x = 0
            if crop_y < 0:
                crop_y = 0
            if crop_x + crop_width > self.input_width:
                crop_x = self.input_width - crop_width
            if crop_y + crop_height > self.input_height:
                crop_y = self.input_height - crop_height
            
            # Crop the frame with proper aspect ratio
            cropped_frame = frame[crop_y:crop_y + crop_height, crop_x:crop_x + crop_width]
            
            # Resize to output dimensions
            vertical_frame = cv2.resize(cropped_frame, (self.output_width, self.output_height))
            
            # Write frame to output video
            self.out.write(vertical_frame)
        
        # Clean up OpenCV resources
        self.cap.release()
        self.out.release()
        self.pose.close()
        
        # Add audio from the original file to the output
        self._add_audio_to_video()
        
        print(f"Vertical video created successfully: {self.output_file}")
    
    def _add_audio_to_video(self):
        """Extract audio from input video and add it to the output video."""
        try:
            # Use FFmpeg to combine the video with the original audio
            cmd = [
                'ffmpeg',
                '-i', self.temp_video_file,  # Video file
                '-i', self.input_file,      # Original file with audio
                '-c:v', 'copy',             # Copy video stream without re-encoding
                '-c:a', 'aac',              # Audio codec
                '-map', '0:v:0',            # Use video from first input
                '-map', '1:a:0',            # Use audio from second input
                '-shortest',                # Finish encoding when the shortest input stream ends
                self.output_file            # Output file
            ]
            
            print("Adding audio to the video...")
            subprocess.run(cmd, check=True)
            
            # Remove the temporary file
            if os.path.exists(self.temp_video_file):
                os.remove(self.temp_video_file)
                
        except subprocess.CalledProcessError as e:
            print(f"Error adding audio: {e}")
            print("Saving video without audio...")
            # If FFmpeg fails, just rename the temp file to the output file
            if os.path.exists(self.temp_video_file):
                os.rename(self.temp_video_file, self.output_file)
        except FileNotFoundError:
            print("FFmpeg not found. Please install FFmpeg to add audio to the video.")
            print("Saving video without audio...")
            # If FFmpeg is not installed, just rename the temp file to the output file
            if os.path.exists(self.temp_video_file):
                os.rename(self.temp_video_file, self.output_file)

def main():
    parser = argparse.ArgumentParser(description="Convert landscape videos to vertical format with focus on people")
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("output", help="Path to output video file")
    parser.add_argument("--width", type=int, default=1080, help="Output width (default: 1080)")
    parser.add_argument("--height", type=int, default=1920, help="Output height (default: 1920)")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Process video
    start_time = time.time()
    clipper = VerticalVideoClipper(args.input, args.output, args.width, args.height)
    clipper.process()
    end_time = time.time()
    
    print(f"Processing completed in {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
