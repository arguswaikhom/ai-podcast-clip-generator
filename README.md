# Vertical Video Clipper

This tool converts landscape videos to vertical format, optimized for social media platforms. It automatically focuses on people in the video and adds dynamic zoom effects to make the content more engaging.

## Features

- Convert landscape videos to vertical format (9:16 aspect ratio)
- Automatically detect and track people in the video
- Intelligently crop the video to keep people in frame
- Add smooth, subtle zoom-in and zoom-out effects for more dynamic content
- Follow camera movements and transitions to maintain focus on subjects

## Requirements

- Python 3.7+
- OpenCV
- NumPy
- MediaPipe

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python vertical_video_clipper.py input_video.mp4
```

This will automatically create an "output" folder in the same directory as the script and save the processed video as "input_video_vertical.mp4". If a file with that name already exists, it will append a counter (like "input_video_vertical_1.mp4").

If you want to specify a custom output location:

```bash
python vertical_video_clipper.py input_video.mp4 --output custom_output.mp4
```

### Optional arguments:

- `--output`, `-o`: Path to output video file (optional)
- `--width`: Width of the output video (default: 1080)
- `--height`: Height of the output video (default: 1920)

Example with custom dimensions:
```bash
python vertical_video_clipper.py input_video.mp4 --width 720 --height 1280
```

## How It Works

1. The script uses MediaPipe's Pose estimation to detect people in each frame
2. It calculates where to crop the video to keep people in the center
3. Smooth transitions are applied when people move across the frame
4. Random zoom effects are added to make the video more dynamic
5. The final video is resized to vertical format (9:16 aspect ratio)

## Notes

- Processing time depends on the length and resolution of the input video
- For best results, use videos where people are clearly visible
- The tool works with various video formats supported by OpenCV 

## Subtitle Generator

This repository also includes a subtitle generator tool that can automatically create subtitles for your videos using OpenAI's Whisper speech recognition model.

### Features

- Batch process all videos in a folder
- Skip videos that already have subtitles generated
- Support for multiple video formats
- SRT subtitle format output
- Configurable Whisper model size

### Usage

```bash
python subtitle_generator.py input_folder
```

This will process all videos in the specified folder and save the generated subtitles to a "subtitle_output" folder in the same directory as the script.

### Optional arguments:

- `--model`: Whisper model to use (choices: tiny, base, small, medium, large, default: base)
- `--output_folder`: Custom path for subtitle output (default: subtitle_output)
- `--extensions`: List of video file extensions to process (default: .mp4 .avi .mov .mkv .webm)

Example with custom model and extensions:
```bash
python subtitle_generator.py videos_folder --model medium --extensions .mp4 .mov
```

## Subtitle Video Creator

This repository also includes a tool to embed subtitles directly onto videos. This creates new videos with the subtitles "burned in" rather than as separate subtitle files.

### Features

- Match videos with their corresponding subtitle files
- Embed readable subtitles in the bottom half of the video
- Automatically format and wrap text to fit the video width
- Add black outline to text for better readability on any background
- Skip videos that don't have matching subtitle files

### Usage

```bash
python vertical_video_subtitle.py videos_folder subtitles_folder
```

This will take all videos from the videos folder, find their matching subtitles in the subtitles folder, and create new videos with subtitles embedded. The output will be saved to a "subtitle_video_output" folder.

### Optional arguments:

- `--output_folder`: Custom path for output videos with subtitles (default: subtitle_video_output)
- `--extensions`: List of video file extensions to process (default: .mp4 .avi .mov .mkv .webm)

Example with custom output folder:
```bash
python vertical_video_subtitle.py videos_folder subtitles_folder --output_folder custom_output
``` 