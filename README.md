# Vertical Video Clipper

This project automatically processes YouTube podcasts into vertical short-form clips with subtitles. It identifies the most engaging segments from a podcast and converts them into mobile-friendly vertical videos.

## Components

The Vertical Video Clipper consists of several key components:

1. **Transcript Downloader**: Downloads and cleans the transcript from a YouTube video
2. **Segment Generator**: Uses AI to identify the most engaging segments of the podcast
3. **Video Downloader**: Downloads the YouTube video 
4. **Video Segment Clipper**: Cuts the original video into clips based on AI-generated suggestions
5. **Vertical Video Converter**: Converts landscape clips to vertical format, focusing on people
6. **Subtitle Generator**: Creates subtitles for each clip
7. **Subtitle Overlay**: Adds subtitles to the vertical videos with highlighting

## Getting Started

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed and available in the system PATH
- Required Python packages (these should be added to requirements.txt):
  - opencv-python
  - mediapipe
  - numpy
  - yt-dlp
  - deepseek
  - requests
  - openai (if using OpenAI API)

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

3. Make sure to update the requirements.txt file with all necessary dependencies.

## Usage

### Process a YouTube Podcast

To process one or more YouTube podcasts, run:

```
python main.py
```

By default, the script processes a predefined list of YouTube videos. You can modify the list in `main.py` to include your desired videos.

This will:
1. Download the transcript and video
2. Identify engaging segments
3. Create vertical clips with subtitles
4. Save everything to the organized output directories

### Command-line Options

The main script orchestrates the process, but each component can also be run individually:

```
python yt_transcript_downloader.py [youtube_url] --output_folder [output_folder]
python subtitle_segment_generator.py --segment-folder [folder] --system-prompt-file [file] --output-folder [folder] --suggestion-output [file] --api-key [key]
python yt_video_downloader.py --youtube-url [url] --output-file [file]
python video_segment_clipper.py [input_video] [suggestions_json] [output_folder] --remove-silence
python vertical_video_clipper.py [input_folder] --output_folder [output_folder]
python subtitle_generator.py [input_folder] --output_folder [output_folder] --word_timings
python vertical_video_subtitle.py [video_folder] [subtitle_folder] --output_folder [output_folder] --highlight [style] --animation [style]
```

## Project Structure

The project consists of several Python modules:

- `main.py`: Main orchestration script that processes YouTube videos
- `yt_transcript_downloader.py`: Downloads and segments YouTube transcripts
- `subtitle_segment_generator.py`: Generates clip suggestions using AI
- `yt_video_downloader.py`: Downloads YouTube videos
- `video_segment_clipper.py`: Clips video segments based on suggestions
- `vertical_video_clipper.py`: Converts landscape videos to vertical format
- `subtitle_generator.py`: Generates subtitles for videos
- `vertical_video_subtitle.py`: Adds subtitles to vertical videos

Additional directories:
- `utils/`: Helper utilities for the project
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