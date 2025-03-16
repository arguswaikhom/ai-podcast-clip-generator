#!/usr/bin/env python3
import os
import json
import argparse
from openai import OpenAI
from pathlib import Path

def read_file(file_path):
    """Read the content of a file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def save_response_to_file(response_text, segment_name, output_folder):
    """
    Save the raw API response to a file
    
    Args:
        response_text: The raw response text from the API
        segment_name: Name of the current segment file
        output_folder: Directory to save the response file
    """
    # Create a responses directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Get basename and remove extension for cleaner response filename
    segment_basename = os.path.basename(segment_name)
    segment_name_without_ext = os.path.splitext(segment_basename)[0]
    
    # Save the response to a file
    response_file = os.path.join(output_folder, f"{segment_name_without_ext}_response.txt")
    with open(response_file, 'w', encoding='utf-8') as f:
        f.write(response_text)
    
    print(f"Saved raw response to {response_file}")

def get_segment_suggestions(client, segment_content, system_prompt, segment_name, output_folder):
    """
    Call AI model API to get suggestions for a segment
    
    Args:
        client: OpenAI client instance
        segment_content: Content of the subtitle segment
        system_prompt: The system prompt to use
        segment_name: Name of the current segment file
        output_folder: Directory to save response files
        
    Returns:
        list: List of suggestions
    """
    try:
        # Call API through OpenAI SDK
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the subtitle segment:\n\n{segment_content}"}
            ],
            stream=False,
            temperature=1.5,
        )
        
        # Extract the response
        response_text = response.choices[0].message.content
        
        # Save the raw response to a file
        save_response_to_file(response_text, segment_name, output_folder)
        
        # Try to extract JSON from the response
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            try:
                suggestions = json.loads(json_str)
                return suggestions
            except json.JSONDecodeError:
                print("Failed to parse JSON from the response. Raw response:")
                print(response_text)
                return []
        else:
            print("No JSON found in the response. Raw response:")
            print(response_text)
            return []
        
    except Exception as e:
        print(f"Error calling AI API: {e}")
        return []

def response_file_exists(segment_name, output_folder):
    """
    Check if a response file already exists for the given segment
    
    Args:
        segment_name: Name of the segment file
        output_folder: Directory where response files are stored
        
    Returns:
        bool: True if the file exists, False otherwise
        str: Path to the response file if it exists, None otherwise
    """
    
    # Get basename and remove extension for cleaner response filename
    segment_basename = os.path.basename(segment_name)
    segment_name_without_ext = os.path.splitext(segment_basename)[0]
    
    response_file = os.path.join(output_folder, f"{segment_name_without_ext}_response.txt")
    
    if os.path.isfile(response_file):
        return True, response_file
    return False, None

def extract_suggestions_from_response_file(response_file):
    """
    Extract suggestions from an existing response file
    
    Args:
        response_file: Path to the response file
        
    Returns:
        list: List of suggestions
    """
    try:
        # Read the response text
        response_text = read_file(response_file)
        
        # Try to extract JSON from the response
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            try:
                suggestions = json.loads(json_str)
                return suggestions
            except json.JSONDecodeError:
                print(f"Failed to parse JSON from the response file: {response_file}")
                return []
        else:
            print(f"No JSON found in the response file: {response_file}")
            return []
    except Exception as e:
        print(f"Error reading response file {response_file}: {e}")
        return []

def check_final_output_exists(suggestion_output):
    """
    Check if the final suggestion output file already exists
    
    Args:
        suggestion_output: Path to the final suggestion output file
        
    Returns:
        bool: True if the file exists and has valid content, False otherwise
    """
    if os.path.isfile(suggestion_output):
        try:
            with open(suggestion_output, 'r', encoding='utf-8') as f:
                content = json.load(f)
                if isinstance(content, list) and len(content) > 0:
                    print(f"Final suggestion output already exists at {suggestion_output}")
                    return True
        except (json.JSONDecodeError, FileNotFoundError):
            pass
    return False

def process_segments(segment_folder, system_prompt_file, output_folder, suggestion_output, api_key):
    """
    Process each segment file and generate suggestions
    
    Args:
        segment_folder: Folder with all the segments to be analyzed
        system_prompt_file: File with the system prompt to use for the AI model
        output_folder: Folder to store the AI model raw outputs
        suggestion_output: File to store the final JSON output
        api_key: AI model API key
        
    Returns:
        list: Combined list of suggestions
    """
    # Check if final output already exists
    if check_final_output_exists(suggestion_output):
        print("Final suggestion output already exists. Skipping processing.")
        return []
    
    # Initialize OpenAI client 
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    
    # Read the system prompt
    system_prompt = read_file(system_prompt_file)
    
    # Get segment files (sorted by name)
    segment_files = sorted(
        [os.path.join(segment_folder, f) for f in os.listdir(segment_folder) if f.endswith('.txt')]
    )
    
    if not segment_files:
        print(f"No segment files found in directory: {segment_folder}")
        return []
    
    # Process each segment
    all_suggestions = []
    
    for i, segment_file in enumerate(segment_files):
        print(f"Processing segment {i+1}/{len(segment_files)}: {os.path.basename(segment_file)}")
        
        # Check if response file already exists
        response_exists, response_file = response_file_exists(segment_file, output_folder)
        
        if response_exists:
            print(f"Response file already exists for segment {os.path.basename(segment_file)}. Skipping API call.")
            suggestions = extract_suggestions_from_response_file(response_file)
        else:
            # Read segment content
            segment_content = read_file(segment_file)
            
            # Get suggestions
            suggestions = get_segment_suggestions(client, segment_content, system_prompt, segment_file, output_folder)
        
        # Add segment information to each suggestion
        for suggestion in suggestions:
            suggestion["segment_file"] = os.path.basename(segment_file)
            suggestion["segment_index"] = i + 1
        
        # Add to the combined list
        all_suggestions.extend(suggestions)
    
    return all_suggestions

def main():
    parser = argparse.ArgumentParser(description="Generate suggestions from subtitle segments")
    parser.add_argument("--segment-folder", required=True, help="Folder with all the segments to be analyzed")
    parser.add_argument("--system-prompt-file", required=True, help="File with the system prompt to use for the AI model")
    parser.add_argument("--output-folder", required=True, help="Folder to store the AI model raw outputs")
    parser.add_argument("--suggestion-output", required=True, help="File to store the final JSON output")
    parser.add_argument("--api-key", required=True, help="AI model API key")
    
    args = parser.parse_args()
    
    # Verify segments directory exists
    if not os.path.isdir(args.segment_folder):
        print(f"Error: Segments directory not found: {args.segment_folder}")
        return
    
    # Verify system prompt file exists
    if not os.path.isfile(args.system_prompt_file):
        print(f"Error: System prompt file not found: {args.system_prompt_file}")
        return
    
    # Create output folder if it doesn't exist
    os.makedirs(args.output_folder, exist_ok=True)
    
    # Process segments to get suggestions
    all_suggestions = process_segments(
        args.segment_folder, 
        args.system_prompt_file,
        args.output_folder,
        args.suggestion_output,
        args.api_key
    )
    
    if all_suggestions:
        # Create directory for suggestion output if needed
        os.makedirs(os.path.dirname(os.path.abspath(args.suggestion_output)), exist_ok=True)
        
        # Write combined suggestions to file
        with open(args.suggestion_output, 'w', encoding='utf-8') as f:
            json.dump(all_suggestions, f, indent=2)
        
        print(f"Successfully generated {len(all_suggestions)} suggestions")
        print(f"Output file: {args.suggestion_output}")
    else:
        print("No suggestions generated")

if __name__ == "__main__":
    main()
