import cv2
import numpy as np
import mediapipe as mp
import argparse
import os
import random
import time
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
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.out = cv2.VideoWriter(
            output_file, fourcc, self.fps, (self.output_width, self.output_height)
        )
        
        # Variables for smooth camera movement
        self.crop_width = int(self.input_height * (self.output_width / self.output_height))
        self.crop_height = self.input_height
        self.last_crop_x = (self.input_width - self.crop_width) // 2  # Start in the middle
        self.transition_frames = 0
        
        # Variables for zoom effect
        self.zoom_state = "neutral"  # neutral, zooming_in, zooming_out
        self.zoom_factor = 1.0
        self.zoom_direction = 0
        self.zoom_duration = 0
        self.zoom_step = 0
        self.frames_since_last_zoom = 0
        self.min_zoom = 1.0
        self.max_zoom = 1.2
        
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
    
    def apply_zoom_effect(self, crop_x: int, crop_width: int) -> Tuple[int, int]:
        """
        Apply zoom effects to make the video more dynamic.
        
        Args:
            crop_x: Current crop x position
            crop_width: Current crop width
            
        Returns:
            Tuple of (new_crop_x, new_crop_width)
        """
        # Update zoom
        if self.zoom_state == "neutral":
            self.frames_since_last_zoom += 1
            
            # Randomly start a new zoom after a certain period
            if self.frames_since_last_zoom > random.randint(60, 180):  # 2-6 seconds at 30fps
                self.zoom_state = random.choice(["zooming_in", "zooming_out"])
                self.zoom_duration = random.randint(90, 150)  # 3-5 seconds
                self.zoom_step = (random.uniform(0.1, 0.15) if self.zoom_state == "zooming_in" else -random.uniform(0.05, 0.1)) / self.zoom_duration
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
        
        # Apply zoom effect
        adjusted_crop_width = int(crop_width / self.zoom_factor)
        adjusted_crop_x = crop_x + (crop_width - adjusted_crop_width) // 2
        
        return adjusted_crop_x, adjusted_crop_width
    
    def process(self):
        """Process the input video and create a vertical video output."""
        frame_count = 0
        target_x = self.last_crop_x  # Start with center crop
        
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
                center_x, _ = person_center
                
                # Make sure we don't go out of bounds with the crop
                max_x = self.input_width - self.crop_width
                target_x = max(0, min(max_x, center_x - self.crop_width // 2))
            
            # Apply smooth transition to target position
            smoothing_factor = 0.1  # Lower value for slower, smoother transitions
            self.last_crop_x = int(self.last_crop_x * (1 - smoothing_factor) + target_x * smoothing_factor)
            
            # Apply zoom effect
            crop_x, crop_width = self.apply_zoom_effect(self.last_crop_x, self.crop_width)
            
            # Make sure we don't go out of bounds after zoom
            if crop_x < 0:
                crop_x = 0
            if crop_x + crop_width > self.input_width:
                crop_x = self.input_width - crop_width
            
            # Crop the frame
            cropped_frame = frame[:, crop_x:crop_x + crop_width]
            
            # Resize to output dimensions
            vertical_frame = cv2.resize(cropped_frame, (self.output_width, self.output_height))
            
            # Write frame to output video
            self.out.write(vertical_frame)
        
        # Clean up
        self.cap.release()
        self.out.release()
        self.pose.close()
        print(f"Vertical video created successfully: {self.output_file}")
    
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
