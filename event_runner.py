import os
import json
import argparse
import hashlib
import numpy as np
from typing import Dict, Any, Tuple, Optional, List, Callable
from pathlib import Path

from moviepy import (
    ImageClip,
    AudioFileClip,
    VideoFileClip,
    ColorClip,
    CompositeVideoClip,
    CompositeAudioClip
)
import moviepy.audio.fx as afx
from render_utils import render_text_block

class VideoGenerationError(Exception):
    """Custom exception for video generation errors."""
    pass

class VideoGenerator:
    """
    Comprehensive video generation class that encapsulates
    all video creation logic with hash-based caching.
    """
    def __init__(self, base_path: str):
        """
        Initialize video generator.

        Args:
            base_path (str): Base directory for project assets
        """
        self.base_path = base_path
        self.clip_builders: Dict[str, Callable] = {
            "image": self._build_image_clip,
            "text": self._build_text_clip,
            "video": self._build_video_clip
        }

    def _calculate_project_hash(self, json_path: str) -> str:
        """
        Calculate hash of clips.json file.

        Args:
            json_path (str): Path to clips.json file

        Returns:
            str: MD5 hash of the clips.json file
        """
        try:
            hasher = hashlib.md5()
            with open(json_path, 'rb') as f:
                hasher.update(f.read())
            return hasher.hexdigest()
        except FileNotFoundError:
            return ""

    def _get_cache_file_path(self) -> str:
        """Get path to cache file."""
        return os.path.join(self.base_path, '.video_cache.json')

    def _load_cache_data(self) -> Dict[str, Any]:
        """Load cache data from file."""
        cache_file = self._get_cache_file_path()
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_cache_data(self, project_hash: str, output_path: str):
        """Save cache data to file."""
        cache_file = self._get_cache_file_path()
        cache_data = {
            'project_hash': project_hash,
            'output_path': output_path
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)

    def _should_skip_generation(self, json_path: str, args) -> Tuple[bool, Optional[str]]:
        """
        Determine if video generation should be skipped.

        Args:
            json_path (str): Path to clips.json
            args: Command line arguments

        Returns:
            Tuple[bool, Optional[str]]: (should_skip, existing_output_path)
        """
        if getattr(args, 'force', False):
            return False, None

        # Calculate current project hash
        current_hash = self._calculate_project_hash(json_path)
        if not current_hash:
            return False, None

        # Load cache data
        cache_data = self._load_cache_data()
        cached_hash = cache_data.get('project_hash')
        cached_output = cache_data.get('output_path')

        # Check if hashes match and output file exists
        if (current_hash == cached_hash and
            cached_output and
            os.path.exists(cached_output)):
            return True, cached_output

        return False, None

    def _resolve_path(self, filename: str) -> str:
        """
        Resolve full path for a given filename.

        Args:
            filename (str): Relative filename

        Returns:
            str: Full path to the file
        """
        return os.path.join(self.base_path, filename)

    def _load_audio(self, audio_path: Optional[str], duration: float) -> Optional[AudioFileClip]:
        """
        Load and process audio clip.

        Args:
            audio_path (Optional[str]): Path to audio file
            duration (float): Desired clip duration

        Returns:
            Optional[AudioFileClip]: Processed audio clip
        """
        if not audio_path:
            return None

        # Construct full audio path
        full_audio_path = os.path.join(self.base_path, "audio", audio_path)

        if not os.path.exists(full_audio_path):
            full_audio_path = os.path.join("tts_audio_lib", audio_path)
            if not os.path.exists(full_audio_path):
                raise VideoGenerationError(f"audio file not exist: {full_audio_path}")

        # Load audio clip
        audio_clip = AudioFileClip(full_audio_path)

        # Handle audio duration
        if audio_clip.duration > duration:
            # Trim audio if longer than clip
            return audio_clip.subclipped(0, duration)

        # Return full audio if shorter or equal to duration
        return audio_clip

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """
        Convert hex color to RGB tuple.

        Args:
            hex_color (str): Hex color code

        Returns:
            Tuple[int, int, int]: RGB color values
        """
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _build_image_clip(self, event: Dict[str, Any], size: Tuple[int, int]) -> ImageClip:
        """
        Create an image or color clip.

        Args:
            event (Dict[str, Any]): Clip configuration
            size (Tuple[int, int]): Video frame size

        Returns:
            ImageClip: Generated clip

        Raises:
            VideoGenerationError: If required parameters are missing
        """
        # Validate required parameters
        if "duration" not in event:
            raise VideoGenerationError("Duration is required for image clips")

        # Create base clip
        if "file" in event:
            # Image file clip
            image_path = self._resolve_path(event["file"])

            # If file doesn't exist in main directory, try assets folder
            if not os.path.exists(image_path):
                image_path = os.path.join("assets", event["file"])

            clip = ImageClip(image_path).resized(size)
        else:
            # Solid color clip
            bgcolor = self._hex_to_rgb(event.get("bgcolor", "#000000"))
            clip = ColorClip(size=size, color=tuple(bgcolor))

        # Set duration
        clip = clip.with_duration(event["duration"])

        # Add audio if specified
        audio_clip = self._load_audio(event.get("audio"), event["duration"])
        if audio_clip:
            clip = clip.with_audio(audio_clip)

        # Set start time
        return clip.with_start(event["start"])

    def _build_text_clip(self, event: Dict[str, Any], size: Tuple[int, int]) -> ImageClip:
        """
        Create a text clip.

        Args:
            event (Dict[str, Any]): Clip configuration
            size (Tuple[int, int]): Video frame size

        Returns:
            ImageClip: Generated text clip

        Raises:
            VideoGenerationError: If required parameters are missing
        """
        # Validate required parameters
        if "duration" not in event or "sentences" not in event:
            raise VideoGenerationError("Duration and sentences are required for text clips")

        # Handle background image
        background_image = None
        if background := event.get("background"):
            background_path = self._resolve_path(background)

            # If file doesn't exist in main directory, try assets folder
            if not os.path.exists(background_path):
                background_path = os.path.join("assets", background)

            if os.path.exists(background_path):
                from PIL import Image
                background_image = Image.open(background_path).convert("RGB").resize(size)

        # Extract text rendering parameters
        sentences = event["sentences"]
        text_lines = [s["text"] for s in sentences]
        positions = [[s["x"], s["y"]] for s in sentences]
        font_sizes = [s["font_size"] for s in sentences]
        font_paths = [s["font"] for s in sentences]
        font_colors = [s.get("font_color", "#000000") for s in sentences]
        bold_flags = [s.get("bold", False) for s in sentences]
        italic_flags = [s.get("italic", False) for s in sentences]

        # Render text block
        img = render_text_block(
            text_lines=text_lines,
            positions=positions,
            font_paths=font_paths,
            font_sizes=font_sizes,
            font_colors=font_colors,
            bold_flags=bold_flags,
            italic_flags=italic_flags,
            bg_color=event.get("bgcolor", "#000000"),
            size=size,
            background_image=background_image
        )

        # Create clip
        clip = ImageClip(np.array(img))

        # Add audio if specified
        audio_clip = self._load_audio(event.get("audio"), event["duration"])
        if audio_clip:
            clip = clip.with_audio(audio_clip)

        clip = clip.with_start(event["start"]).with_duration(event["duration"])

        return clip

    def _build_video_clip(self, event: Dict[str, Any], size: Tuple[int, int]) -> VideoFileClip:
        """
        Create a video clip.

        Args:
            event (Dict[str, Any]): Clip configuration
            size (Tuple[int, int]): Video frame size

        Returns:
            VideoFileClip: Generated video clip

        Raises:
            VideoGenerationError: If required parameters are missing
        """
        # Validate required parameters
        if "file" not in event:
            raise VideoGenerationError("File is required for video clips")

        video_file = event["file"]
        # Construct full video path
        full_video_path = os.path.join(self.base_path, "video", video_file)

        if not os.path.exists(full_video_path):
            raise VideoGenerationError(f"video file not exist: {full_video_path}")

        # Create video clip
        clip = VideoFileClip(full_video_path)

        # Trim clip if duration specified
        if duration := event.get("duration"):
            clip = clip.subclipped(0, duration)

        # Set start time
        return clip.with_start(event["start"])

    def generate_video(
        self,
        data: Dict[str, Any],
        args
    ) -> str:
        """
        Generate video from configuration data.

        Args:
            data (Dict[str, Any]): Video configuration
            args.preview_start (Optional[float]): Start time for preview
            args.preview_duration (Optional[float]): Duration of preview
            args.audio_only (Optional[bool]): generate audio file only
            args.output_folder (Optional[str]): output softlink path

        Returns:
            str: Path to generated video file
        """
        # Validate video size configuration
        if "size" not in data:
            raise VideoGenerationError("Missing required 'size' field in JSON")

        # Extract video configuration
        size = tuple(data["size"])
        fps = data.get("fps", 24)  # Default to 24 fps if not specified
        events = data.get("events", data)  # Fallback for backward compatibility

        # Build clips
        clips = []
        for i, event in enumerate(events):
            try:
                print(f"Processing clip #{i} ({event.get('type', 'unknown')})")
                # Build clip using appropriate method
                builder = self.clip_builders.get(event["type"])
                if not builder:
                    print(f"Unsupported clip type: {event['type']} for clip #{i}")
                    continue

                clip = builder(event, size)
                clips.append(clip)
            except Exception as e:
                print(f"Error processing clip #{i} : {e}")
                print(f"Clip details: {event}")
                raise # Rethrows the original exception

        for i in range(1, len(clips)):
            if clips[i].start < clips[i-1].end:
                print(f"Warning: Clip {i} overlaps with previous clip.")

        # Create composite video from clips
        video = CompositeVideoClip(clips, size=size)

        # Add background music if specified
        video = self._add_background_music(video, data)

        preview_start = args.preview_start
        preview_duration = args.preview_duration
        audio_only = args.audio_only
        output_ln_folder = Path(args.output_folder)

        # Handle video preview if specified
        if preview_start is not None and preview_duration is not None:
            video = video.subclipped(preview_start, preview_start + preview_duration)

        if audio_only:
            output_path = os.path.join(self.base_path, "output_audio.mp3")
            video.audio.write_audiofile(output_path, codec="mp3")
            print(f"Audio generated successfully: {output_path}")
        else:
            output_path = os.path.join(self.base_path, "output.mp4")
            video.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")

            try:
                output_ln_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Error creating output directory {output_ln_folder}: {str(e)}")

            target = Path(output_path).resolve()
            link = output_ln_folder / (os.path.basename(self.base_path)+'.mp4')
            create_symlink(target, link)
            print(f"Video generated successfully: {output_path}")
        return output_path

    def _add_background_music(
        self,
        video: CompositeVideoClip,
        data: Dict[str, Any]
    ) -> CompositeVideoClip:
        """
        Add background music to video.

        Args:
            video (CompositeVideoClip): Original video
            data (Dict[str, Any]): Configuration data

        Returns:
            CompositeVideoClip: Video with background music
        """
        bgm_data = data.get("bgm")
        if not isinstance(bgm_data, dict):
            return video

        bgm_file = bgm_data.get("file")
        if not bgm_file:
            raise VideoGenerationError("file attribute is missing in bgm")

        try:
            # Try loading from audio folder
            bgm_paths = [
                os.path.join(self.base_path, "audio", bgm_file),
                os.path.join("assets", "audio", bgm_file),
                os.path.join("assets", bgm_file)
            ]

            # Find first existing path
            bgm_audio_path = next((path for path in bgm_paths if os.path.exists(path)), None)

            if not bgm_audio_path:
                raise FileNotFoundError(f"Background music file not found: {bgm_file}")

            # Load and process background music
            bgm_audio = AudioFileClip(bgm_audio_path)
            bgm_volume = bgm_data.get("volume", 1.0)

            # Determine start time - error if both fields are present
            has_start_time = "start_time" in bgm_data
            has_start_clip = "start_clip" in bgm_data

            if has_start_time and has_start_clip:
                raise VideoGenerationError("Cannot specify both start_time and start_clip in bgm configuration")
            elif has_start_clip:
                # Use clip index to find start time
                clip_index = int(bgm_data["start_clip"])
                print(f"bgm start from clip {clip_index}")
                if hasattr(video, 'clips') and clip_index < len(video.clips):
                    bgm_start = video.clips[clip_index].start
                else:
                    raise VideoGenerationError(f"Clip index {clip_index} not found in video")
            elif has_start_time:
                # Use time directly
                bgm_start = float(bgm_data["start_time"])
            else:
                # Default to start of video
                bgm_start = 0.0

            print(f"bgm start from {bgm_start} sec")

            # Apply volume and start time
            bgm_audio = bgm_audio.with_effects([afx.MultiplyVolume(bgm_volume)]).with_start(bgm_start)

            # Ensure background music doesn't exceed video duration
            max_bgm_duration = max(0, video.duration - bgm_start)
            if max_bgm_duration <= 0:
                return video  # No room for background music

            bgm_audio = bgm_audio.subclipped(0, min(bgm_audio.duration, max_bgm_duration))

            # Add background music to video
            if video.audio:
                return video.with_audio(CompositeAudioClip([video.audio, bgm_audio]))
            else:
                return video.with_audio(bgm_audio)

        except Exception as e:
            raise VideoGenerationError(f"Failed to add background music: {e}")

def create_symlink(target, link_name):
    try:
        # Using pathlib (recommended)
        link_path = Path(link_name)
        target_path = Path(target).resolve()

        # Check if target exists
        if not target_path.exists():
            print(f"Warning: Target '{target}' does not exist")

        # Remove existing link if it exists
        if link_path.is_symlink():
            link_path.unlink()

        # Create the symbolic link
        link_path.symlink_to(target_path)
        print(f"Created symbolic link: {link_name} -> {target}")

    except OSError as e:
        print(f"Error creating symbolic link: {e}")

def generate_video_from_json(args) -> str:
    """
    Main function to generate video from JSON configuration.

    Args:
        args.folder (str): Path to folder containing clips.json
        args.preview_start(Optional[float]): Start time for preview
        args.preview_duration (Optional[float]): Duration of preview
        args.audio_only (Optional[bool]): generate audio file only
        args.output_folder (Optional[str]): output softlink path
        args.force (Optional[bool]): force regeneration even if cached

    Returns:
        str: Path to generated video file
    """
    # Construct full path to project folder
    folder_path = args.folder
    full_path = os.path.join("workspace", folder_path)
    json_file = "clips.json"
    json_path = os.path.join(full_path, json_file)

    # Create video generator
    generator = VideoGenerator(full_path)

    # Check if generation should be skipped
    should_skip, existing_output = generator._should_skip_generation(json_path, args)

    if should_skip:
        print("Project hasn't changed since last generation. Using cached output.")
        print(f"Use --force to regenerate anyway.")
        print(f"Input:  {json_path}")
        print(f"Output: {existing_output} (existing)")

        # Still create symlink if needed
        if not args.audio_only:
            output_ln_folder = Path(args.output_folder)
            try:
                output_ln_folder.mkdir(parents=True, exist_ok=True)
                target = Path(existing_output).resolve()
                link = output_ln_folder / (os.path.basename(full_path) + '.mp4')
                create_symlink(target, link)
            except Exception as e:
                print(f"Warning: Could not create symlink: {e}")

        return existing_output

    # Load JSON configuration
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading JSON: {e}")
        raise VideoGenerationError(f"Failed to load configuration: {e}")

    # Generate video
    output_path = generator.generate_video(data, args)

    # Save cache data
    project_hash = generator._calculate_project_hash(json_path)
    generator._save_cache_data(project_hash, output_path)

    return output_path

def parse_arguments():
    """
    Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Generate video from event JSON.")
    parser.add_argument(
        "folder",
        help="Subfolder under workspace containing clips.json and assets"
    )
    parser.add_argument(
        "--preview-start",
        type=float,
        help="Start time in seconds for preview clip"
    )
    parser.add_argument(
        "--preview-duration",
        type=float,
        help="Duration in seconds for preview clip"
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Generate audio only"
    )
    parser.add_argument(
        "--output-folder",
        help="Folder to save softlink of output video (defaults to output)",
        default="output"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration even if project hasn't changed"
    )
    return parser.parse_args()

def main():
    """
    Command-line interface for video generation.
    Parses arguments and calls video generation function.
    """
    try:
        # Parse arguments
        args = parse_arguments()

        # Generate video based on command-line arguments
        generate_video_from_json(args)
    except Exception as e:
        print(f"Video generation failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()