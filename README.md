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

## YouTube Video Downloader

This tool allows you to download YouTube videos in the highest available quality using yt-dlp. It provides detailed progress information and avoids re-downloading videos that have already been downloaded.

### Features

- Downloads videos in the best available quality (highest resolution with audio)
- Uses yt-dlp, a powerful and actively maintained YouTube downloader
- Displays download progress with percentage, size, speed, and estimated time remaining
- Automatically converts to MP4 format for maximum compatibility
- Skips downloading if the file already exists
- Creates the output directory if it doesn't exist

### Usage

```bash
python yt_video_downloader.py --youtube-url "https://www.youtube.com/watch?v=VIDEOID" --output-file "path/to/output.mp4"
```

### Requirements

This script requires yt-dlp and FFmpeg:

```bash
pip install yt-dlp
```

FFmpeg is needed for the best quality downloads (merging separate video and audio streams). Install it according to your OS:
- Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use Chocolatey: `choco install ffmpeg`
- macOS: Use Homebrew: `brew install ffmpeg`
- Linux: Use your package manager, e.g., `apt install ffmpeg` or `yum install ffmpeg`

## Subtitle Segment Generator

This tool processes subtitle segments, analyzes them using an AI model, and generates suggestions. It can be used to identify interesting segments in videos based on their subtitles.

### Features

- Process text segments from subtitle files
- Call AI model API to analyze segments for interesting content
- Save raw API responses for future reference
- Skip API calls if responses already exist
- Generate a JSON file with all suggestions

### Usage

```bash
python subtitle_segment_generator.py --segment-folder "path/to/segments" --system-prompt-file "path/to/prompt.txt" --output-folder "path/to/outputs" --suggestion-output "path/to/suggestions.json" --api-key "your-api-key"
```

### Arguments

- `--segment-folder`: Folder containing all the subtitle segments to analyze
- `--system-prompt-file`: File containing the system prompt for the AI model
- `--output-folder`: Folder to store the AI model raw outputs
- `--suggestion-output`: File to store the final JSON output
- `--api-key`: AI model API key 

## Video Segment Clipper

The Video Segment Clipper tool allows you to automatically cut segments from a video based on suggestions provided in a JSON file. It's particularly useful for extracting highlights or interesting segments from longer videos.

### Features

- Cut video segments based on start and end timestamps from a JSON suggestions file
- Include both video and audio in the clips
- Optionally remove silent gaps between conversations to preserve only the conversation
- Skip segments that have already been clipped
- Display detailed progress and logs during processing
- Sanitize filenames based on segment titles for compatibility

### Usage

```bash
python video_segment_clipper.py video_file.mp4 suggestions.json output_folder
```

### Arguments

- `video`: Path to the input video file
- `suggestions`: Path to the JSON file containing segment suggestions
- `output_folder`: Path to the output folder where clips will be saved

### Optional Arguments

- `--remove-silence`: Enable removal of silent gaps between conversations (default: False)
- `--silence-threshold`: Threshold in dB for silence detection (default: -30.0)
- `--silence-duration`: Minimum duration of silence to be detected and removed in seconds (default: 0.5)

### Suggestions JSON Format

The suggestions JSON file should have the following format:

```json
[
  {
    "start": "00:02:12",
    "end": "00:03:17",
    "title": "Segment Title",
    "description": "Optional description",
    "hashtags": ["#tag1", "#tag2"]
  },
  {
    "start": "00:05:30",
    "end": "00:06:45",
    "title": "Another Segment",
    "description": "Optional description",
    "hashtags": ["#tag3", "#tag4"]
  }
]
```

Each segment must include at least the `start` and `end` timestamps in the format `HH:MM:SS` or `HH:MM:SS.mmm`.

### Example with silence removal

```bash
python video_segment_clipper.py video_file.mp4 suggestions.json clips_output --remove-silence --silence-threshold -35 --silence-duration 0.75
```

This will extract segments from `video_file.mp4` according to the timestamps in `suggestions.json`, remove silent gaps longer than 0.75 seconds below -35dB, and save the clips to the `clips_output` folder. 