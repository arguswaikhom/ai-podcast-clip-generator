# Vertical Video Clipper

This project automatically processes YouTube podcasts into vertical short-form clips with subtitles. It identifies the most engaging segments from a podcast and converts them into mobile-friendly vertical videos.

## Components

The Vertical Video Clipper consists of several key components:

1. **Transcript Downloader**: Downloads and cleans the transcript from a YouTube video
2. **AI Suggestion Generator**: Uses AI to identify the most engaging segments of the podcast
3. **Video Downloader**: Downloads the YouTube video 
4. **Video Suggestion Clipper**: Cuts the original video into clips based on AI-generated suggestions
5. **Vertical Video Converter**: Converts landscape clips to vertical format, focusing on people
6. **Video Subtitle Generator**: Creates subtitles for each clip
7. **Video Subtitle Embedder**: Adds subtitles to the vertical videos with highlighting and animation

## Getting Started

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed and available in the system PATH
- Required Python packages (install via requirements.txt):
  - opencv-python
  - mediapipe
  - numpy
  - yt-dlp
  - requests
  - openai or deepseek

- A Deepseek API key (set as the environment variable `DEEPSEEK_API_KEY`)

### Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd VerticalVideoClipper
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Process a YouTube Podcast

To process one or more YouTube podcasts, run:

```
python podcast_clip_generator.py
```

By default, the script processes a predefined list of YouTube videos. You can modify the list in `podcast_clip_generator.py` to include your desired videos.

This will:
1. Download the transcript and video
2. Identify engaging segments using AI
3. Create vertical clips with subtitles
4. Save everything to the organized output directories

### Command-line Options

Each component can also be run individually:

```
python yt_transcript_downloader.py [youtube_url] --output_folder [output_folder]
python ai_suggestion_generator.py --segment-folder [folder] --system-prompt-file [file] --output-folder [folder] --suggestion-output [file] --api-key [key]
python yt_video_downloader.py --youtube-url [url] --output-file [file]
python video_suggestion_clipper.py [input_video] [suggestions_json] [output_folder] --remove-silence
python vertical_video_converter.py [input_folder] --output_folder [output_folder]
python video_subtitle_generator.py [input_folder] --output_folder [output_folder] --word_timings
python video_subtitle_embedder.py [video_folder] [subtitle_folder] --output_folder [output_folder] --highlight [style] --animation [style]
```

## Project Structure

The project consists of several Python modules:

- `podcast_clip_generator.py`: Main orchestration script that processes YouTube videos
- `yt_transcript_downloader.py`: Downloads and segments YouTube transcripts
- `ai_suggestion_generator.py`: Generates clip suggestions using AI
- `yt_video_downloader.py`: Downloads YouTube videos
- `video_suggestion_clipper.py`: Clips video segments based on suggestions
- `vertical_video_converter.py`: Converts landscape videos to vertical format
- `video_subtitle_generator.py`: Generates subtitles for videos
- `video_subtitle_embedder.py`: Adds subtitles to vertical videos with highlighting and animation

Additional directories:
- `utils/`: Helper utilities for the project
  - `output_folder_creator.py`: Creates the directory structure for outputs
  - `time_format.py`: Utilities for time formatting
  - `size_format.py`: Utilities for file size formatting
  - `yt_info_extractor.py`: Extract information from YouTube videos
- `prompt/`: Contains AI system prompts for segment generation
- `output/`: Default root directory for processed videos

## Output Structure

The output will be organized in the following structure:

```
/output
    /youtube_video_title
        /transcript
            /transcript_original.vtt
            /transcript_cleaned.vtt
        /segments
            /input
                /segment_1.txt
                /segment_2.txt
            /response
                /segment_1_response.txt
                /segment_2_response.txt
            /suggestions.json
        /video
            /video.mp4
            /clips
                /clip_1_video_clip_title.mp4
                /clip_2_video_clip_title.mp4
            /clip_subtitles
                /clip_1_video_clip_title.srt
                /clip_2_video_clip_title.srt
            /vertical_clips
                /clip_1_video_clip_title.mp4
                /clip_2_video_clip_title.mp4
            /subtitled_clips
                /clip_1_video_clip_title.mp4
                /clip_2_video_clip_title.mp4
```

## Features

- Convert landscape videos to vertical format (9:16 aspect ratio)
- Automatically detect and track people in the video
- Intelligently crop the video to keep people in frame
- Add smooth, subtle zoom-in and zoom-out effects for more dynamic content
- Follow camera movements and transitions to maintain focus on subjects
- Word-level subtitle highlighting with animation effects
- Noise and silence removal from clips

## Troubleshooting

If you encounter issues with module imports, make sure all required packages are installed correctly within your Python environment.

For Deepseek API key issues, ensure the environment variable is set properly:

```bash
# On Windows
set DEEPSEEK_API_KEY=your_api_key_here

# On Linux/macOS
export DEEPSEEK_API_KEY=your_api_key_here
```

## License

This project is open source and available under the MIT License. 