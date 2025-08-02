import os
import json
import argparse
import numpy as np
from typing import Dict, Any, Tuple, Optional, List, Callable

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
    all video creation logic.
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

            clip = ImageClip(image_path).resized(height=size[1])
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
        font_path = os.path.join("assets", "fonts", sentences[0]["font"]) if sentences else ""
        font_colors = [s.get("font_color", "#000000") for s in sentences]
        bold_flags = [s.get("bold", False) for s in sentences]
        italic_flags = [s.get("italic", False) for s in sentences]

        # Render text block
        img = render_text_block(
            text_lines=text_lines,
            positions=positions,
            font_path=font_path,
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

        # Create video clip
        clip = VideoFileClip(self._resolve_path(event["file"]))

        # Trim clip if duration specified
        if duration := event.get("duration"):
            clip = clip.subclipped(0, duration)

        # Set start time
        return clip.with_start(event["start"])

    def generate_video(
        self,
        data: Dict[str, Any],
        preview_start: Optional[float] = None,
        preview_duration: Optional[float] = None
    ) -> str:
        """
        Generate video from configuration data.

        Args:
            data (Dict[str, Any]): Video configuration
            preview_start (Optional[float]): Start time for preview
            preview_duration (Optional[float]): Duration of preview

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
        anyError = False
        for i, event in enumerate(events):
            try:
                # Build clip using appropriate method
                builder = self.clip_builders.get(event["type"])
                if not builder:
                    print(f"Unsupported clip type: {event['type']} for clip #{i}")
                    anyError = True
                    continue

                clip = builder(event, size)
                clips.append(clip)
            except VideoGenerationError as e:
                anyError = True
                print(f"Skipping invalid clip #{i} ({event.get('type', 'unknown')}): {e}")
                print(f"Clip details: {event}")
            except Exception as e:
                anyError = True
                print(f"Error processing clip #{i} ({event.get('type', 'unknown')}): {e}")
                print(f"Clip details: {event}")
                print(f"Skipping clip and continuing...")

        if anyError:
            raise VideoGenerationError("Stop because of error")

        # Create composite video from clips
        video = CompositeVideoClip(clips, size=size)

        # Add background music if specified
        video = self._add_background_music(video, data)

        # Handle video preview if specified
        if preview_start is not None and preview_duration is not None:
            video = video.subclipped(preview_start, preview_start + preview_duration)

        print("##############debug##################")
        # Output final video
        output_path = os.path.join(self.base_path, "output.mp4")
        video.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")

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
            # Load and process background music
            bgm_audio = AudioFileClip(os.path.join(self.base_path, "audio", bgm_file))
            bgm_volume = bgm_data.get("volume", 1.0)
            bgm_start = bgm_data.get("start", 0.0)

            # Apply volume and start time
            bgm_audio = bgm_audio.with_effects([afx.MultiplyVolume(bgm_volume)]).with_start(bgm_start)

            # Ensure background music doesn't exceed video duration
            max_bgm_duration = max(0, video.duration - bgm_start)
            bgm_audio = bgm_audio.subclipped(0, min(bgm_audio.duration, max_bgm_duration))

            # Add background music to video
            if video.audio:
                return video.with_audio(CompositeAudioClip([video.audio, bgm_audio]))
            return video.with_audio(bgm_audio)

        except Exception as e:
            raise VideoGenerationError(f"Failed to add background music: {e}")

def generate_video_from_json(
    folder_path: str,
    preview_start: Optional[float] = None,
    preview_duration: Optional[float] = None
) -> str:
    """
    Main function to generate video from JSON configuration.

    Args:
        folder_path (str): Path to folder containing clips.json
        preview_start (Optional[float]): Start time for preview
        preview_duration (Optional[float]): Duration of preview

    Returns:
        str: Path to generated video file
    """
    # Construct full path to project folder
    full_path = os.path.join("workspace", folder_path)
    json_file = "clips.json"

    # Load JSON configuration
    try:
        with open(os.path.join(full_path, json_file), 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading JSON: {e}")
        raise VideoGenerationError(f"Failed to load configuration: {e}")

    # Create video generator and generate video
    generator = VideoGenerator(full_path)
    return generator.generate_video(data, preview_start, preview_duration)

def main():
    """
    Command-line interface for video generation.
    Parses arguments and calls video generation function.
    """
    parser = argparse.ArgumentParser(description="Generate video from event JSON.")
    parser.add_argument("folder", help="Subfolder under workspace containing clips.json and assets")
    parser.add_argument("--preview-start", type=float, help="Start time in seconds for preview clip")
    parser.add_argument("--preview-duration", type=float, help="Duration in seconds for preview clip")
    args = parser.parse_args()

    try:
        # Generate video based on command-line arguments
        generate_video_from_json(args.folder, args.preview_start, args.preview_duration)
    except Exception as e:
        print(f"Video generation failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()