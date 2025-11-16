import os
import json
import argparse
import hashlib
import numpy as np
import subprocess
from typing import Dict, Any, Tuple, Optional, List, Callable
from pathlib import Path

from moviepy import (
    ImageClip,
    AudioFileClip,
    VideoFileClip,
    ColorClip,
    CompositeVideoClip,
    CompositeAudioClip,
    AudioClip,
    concatenate_audioclips
)
import moviepy.audio.fx as afx
from render_utils import render_text_block

class VideoGenerationError(Exception):
    """Custom exception for video generation errors."""
    pass

class VideoGenerator:
    """
    Comprehensive video generation class with per-clip caching.
    """
    def __init__(self, base_path: str):
        """
        Initialize video generator.

        Args:
            base_path (str): Base directory for project assets
        """
        self.base_path = base_path
        self.cache_dir = os.path.join(base_path, ".clip_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

        self.clip_builders: Dict[str, Callable] = {
            "image": self._build_image_clip,
            "text": self._build_text_clip,
            "video": self._build_video_clip
        }

    def _calculate_clip_hash(self, event: Dict[str, Any]) -> str:
        """
        Calculate hash for a single clip configuration.

        Args:
            event (Dict[str, Any]): Clip configuration

        Returns:
            str: MD5 hash of the clip configuration
        """
        # Create a copy without 'start' field since timing doesn't affect content
        clip_data = {k: v for k, v in event.items() if k != 'start'}
        clip_json = json.dumps(clip_data, sort_keys=True)
        return hashlib.md5(clip_json.encode()).hexdigest()

    def _get_clip_cache_path(self, clip_index: int, clip_hash: str) -> str:
        """Get path for cached clip."""
        return os.path.join(self.cache_dir, f"clip_{clip_index:03d}_{clip_hash}.mp4")

    def _resolve_path(self, filename: str) -> str:
        """
        Resolve full path for a given filename.

        Args:
            filename (str): Relative filename

        Returns:
            str: Full path to the file
        """
        return os.path.join(self.base_path, filename)

    def _load_audio(self,
            audio_path: Optional[str],
            duration: Optional[float],
            pregap: float = 0,
            postgap: float = 0,
            target_loudness: float = -16.0) -> Optional[AudioFileClip]:
        """
        Load and process audio clip with loudness normalization.

        Args:
            audio_path (Optional[str]): Path to audio file
            duration (float): Desired clip duration
            target_loudness (float): Target loudness in LUFS (default: -16.0)

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

        # Create normalized audio file
        normalized_path = os.path.join(self.cache_dir, f"norm_{os.path.basename(audio_path)}")

        # Apply loudness normalization using FFmpeg
        cmd = [
            'ffmpeg', '-y', '-i', full_audio_path,
            '-af', f'loudnorm=I={target_loudness}:TP=-1.5:LRA=11',
            normalized_path
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        # Load normalized audio clip
        audio_clip = AudioFileClip(normalized_path)

        # Handle audio duration
        if duration and audio_clip.duration > duration:
            audio_clip = audio_clip.subclipped(0, duration)

        # Add pregap (silence before)
        if pregap > 0:
            silence_before = AudioClip(lambda t: 0, duration=pregap)
            audio_clip = concatenate_audioclips([silence_before, audio_clip])

        # Add postgap (silence after)
        if postgap > 0:
            silence_after = AudioClip(lambda t: 0, duration=postgap)
            audio_clip = concatenate_audioclips([audio_clip, silence_after])

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
        if "total_duration" not in event:
            raise VideoGenerationError("total_duration is required for image clips")

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
        clip = clip.with_duration(event["total_duration"])

        # Add audio if specified
        audio_clip = self._load_audio(event.get("audio"),
                                    event.get("duration",None),
                                    event.get("pregap",0),
                                    event.get("postgap",0))
        if audio_clip:
            clip = clip.with_audio(audio_clip)

        # Set start time to 0 for individual clip
        return clip.with_start(0)

    def _build_text_clip(self, event: Dict[str, Any], size: Tuple[int, int]) -> ImageClip:
        """
        Create a text clip with optional images.

        Args:
            event (Dict[str, Any]): Clip configuration
            size (Tuple[int, int]): Video frame size

        Returns:
            ImageClip: Generated text clip

        Raises:
            VideoGenerationError: If required parameters are missing
        """
        # Validate required parameters
        if "total_duration" not in event or "sentences" not in event:
            raise VideoGenerationError("total_duration and sentences are required for text clips")

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
        line_spacings = [s["line_spacing"] for s in sentences]
        bold_flags = [s.get("bold", False) for s in sentences]
        italic_flags = [s.get("italic", False) for s in sentences]

        # Render text block
        img = render_text_block(
            text_lines=text_lines,
            positions=positions,
            font_paths=font_paths,
            font_sizes=font_sizes,
            font_colors=font_colors,
            line_spacings=line_spacings,
            bold_flags=bold_flags,
            italic_flags=italic_flags,
            bg_color=event.get("bgcolor", "#000000"),
            size=size,
            background_image=background_image
        )

        # Handle images if present in the event
        if "image" in event and isinstance(event["image"], list):
            from PIL import Image

            for img_data in event["image"]:
                # Get image file path
                img_file = img_data.get("file")
                if not img_file:
                    continue

                # Try assets folder first, then workspace folder
                img_path = os.path.join("assets", img_file)
                if not os.path.exists(img_path):
                    img_path = self._resolve_path(img_file)

                if not os.path.exists(img_path):
                    raise VideoGenerationError(f"Image file not found: {img_file}")

                # Load and process image
                overlay_img = Image.open(img_path).convert("RGBA")

                # Get position (default to 0, 0)
                x = img_data.get("x", 0)
                y = img_data.get("y", 0)

                # Get size if specified (otherwise use original size)
                if "width" in img_data or "height" in img_data:
                    width = img_data.get("width", overlay_img.width)
                    height = img_data.get("height", overlay_img.height)
                    overlay_img = overlay_img.resize((width, height), Image.LANCZOS)

                # Get opacity (default to 1.0)
                opacity = img_data.get("opacity", 1.0)
                if opacity < 1.0:
                    # Adjust alpha channel for opacity
                    alpha = overlay_img.split()[3]
                    alpha = alpha.point(lambda p: int(p * opacity))
                    overlay_img.putalpha(alpha)

                # Paste overlay onto the main image
                # Convert main image to RGBA if needed
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # Paste with alpha compositing
                img.paste(overlay_img, (x, y), overlay_img)

        # Create clip
        clip = ImageClip(np.array(img))

        # Add audio if specified
        audio_clip = self._load_audio(event.get("audio"),
                                    event.get("duration",None),
                                    event.get("pregap",0),
                                    event.get("postgap",0))
        if audio_clip:
            clip = clip.with_audio(audio_clip)

        clip = clip.with_start(0).with_duration(event["total_duration"])

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

        # Potential video file paths to check
        video_paths = [
            os.path.join(self.base_path, "video", video_file),  # First, check project video directory
            os.path.join("assets", "video", video_file),        # Then, check assets/video
            os.path.join("assets", video_file)                  # Finally, check assets directly
        ]

        # Find the first existing path
        full_video_path = next((path for path in video_paths if os.path.exists(path)), None)
        print(f"Looking for video file: {video_file}, found: {full_video_path}")
        if not full_video_path:
            raise VideoGenerationError(f"Video file not found: {video_file}")

        # Create video clip and resize to match target size
        clip = VideoFileClip(full_video_path).resized(size)

        # Trim clip if duration specified
        if total_duration := event.get("total_duration"):
            clip = clip.subclipped(0, total_duration)

        # Set start time to 0 for individual clip
        return clip.with_start(0)

    def _generate_single_clip(
        self,
        event: Dict[str, Any],
        clip_index: int,
        size: tuple,
        fps: int
    ) -> Optional[str]:
        """Generate or retrieve cached MP4 for a single clip."""

        # Check if clip has zero duration - skip it
        duration = event.get("total_duration", 0)
        if duration <= 0:
            print(f"  Skipping clip #{clip_index} (zero duration)")
            return None

        # Calculate clip hash
        clip_hash = self._calculate_clip_hash(event)
        clip_path = self._get_clip_cache_path(clip_index, clip_hash)

        # Return cached clip if exists
        if os.path.exists(clip_path):
            print(f"  Using cached clip #{clip_index}")
            return clip_path

        print(f"  Generating clip #{clip_index} ({event.get('type', 'unknown')})")

        # Build clip using existing methods
        builder = self.clip_builders.get(event["type"])
        if not builder:
            raise VideoGenerationError(f"Unsupported clip type: {event['type']}")

        # Create clip with duration but start at 0 for individual file
        clip = builder(event, size)

        # Ensure clip has proper duration
        clip = clip.with_start(0).with_duration(duration)

        # Inject a silent audio track if this clip doesn't have audio
        if clip.audio is None:
            # Use a fixed FPS to avoid sample rate mismatch across clips.
            silent_fps = 44100
            silent_audio = AudioClip(lambda t: 0, duration=duration, fps=silent_fps)
            clip = clip.with_audio(silent_audio)

        clip.write_videofile(
            clip_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            logger=None  # Suppress moviepy progress bars for cleaner output
        )

        # Clean up old cached versions of this clip index
        self._cleanup_old_clip_versions(clip_index, clip_hash)

        return clip_path

    def _cleanup_old_clip_versions(self, clip_index: int, current_hash: str):
        """Remove old cached versions of a clip."""
        pattern = f"clip_{clip_index:03d}_"
        for filename in os.listdir(self.cache_dir):
            if filename.startswith(pattern) and current_hash not in filename:
                old_file = os.path.join(self.cache_dir, filename)
                try:
                    os.remove(old_file)
                    print(f"  Removed old cache: {filename}")
                except OSError:
                    pass

    def _concat_clips_ffmpeg(self, clip_paths: List[str], output_path: str):
        """Concatenate clips using FFmpeg (fast, no re-encoding)."""

        # Handle empty clip list
        if not clip_paths:
            raise VideoGenerationError("No clips to concatenate (all clips may have zero duration)")

        # Create concat file
        concat_file = os.path.join(self.cache_dir, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for path in clip_paths:
                # FFmpeg needs absolute paths or paths relative to concat file
                abs_path = os.path.abspath(path)
                f.write(f"file '{abs_path}'\n")

        # Use FFmpeg concat demuxer
        cmd = [
            'ffmpeg', '-y',
            '-fflags', '+genpts',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-movflags', '+faststart',
            output_path
        ]

        print("\nMerging clips...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VideoGenerationError(f"FFmpeg concat failed: {result.stderr}")

        print(f"Merged {len(clip_paths)} clips successfully")

    def _add_bgm_to_merged_video(
        self,
        video_path: str,
        data: Dict[str, Any],
        events: List[Dict[str, Any]]
    ) -> str:
        """Add background music to already-merged video."""

        bgm_data = data.get("bgm")
        if not isinstance(bgm_data, dict):
            return video_path

        bgm_file = bgm_data.get("file")
        if not bgm_file:
            return video_path

        print("\nAdding background music...")

        # Find BGM file
        bgm_paths = [
            os.path.join(self.base_path, "audio", bgm_file),
            os.path.join("assets", "audio", bgm_file),
            os.path.join("assets", bgm_file)
        ]
        bgm_path = next((p for p in bgm_paths if os.path.exists(p)), None)

        if not bgm_path:
            raise VideoGenerationError(f"BGM file not found: {bgm_file}")

        # Calculate BGM start time
        bgm_start = 0.0
        if "start_clip" in bgm_data:
            clip_index = int(bgm_data["start_clip"])
            if clip_index < len(events):
                bgm_start = events[clip_index].get("start", 0.0)
        elif "start_time" in bgm_data:
            bgm_start = float(bgm_data["start_time"])

        bgm_volume = bgm_data.get("volume", 1.0)

        # Output path for video with BGM
        output_with_bgm = video_path.replace(".mp4", "_with_bgm.mp4")

        # FFmpeg command to mix audio
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', bgm_path,
            '-filter_complex',
            f'[1:a]adelay={int(bgm_start*1000)}|{int(bgm_start*1000)},volume={bgm_volume}[bgm];'
            f'[0:a][bgm]amix=inputs=2:duration=first[aout]',
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',  # Copy video stream
            '-c:a', 'aac',
            output_with_bgm
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VideoGenerationError(f"BGM addition failed: {result.stderr}")

        # Replace original with BGM version
        os.replace(output_with_bgm, video_path)
        print("Background music added")

        return video_path

    def generate_video(self, data: Dict[str, Any], args) -> str:
        """
        Generate video with per-clip caching.

        Args:
            data (Dict[str, Any]): Video configuration
            args: Command line arguments

        Returns:
            str: Path to generated video file
        """
        # Clear cache if force flag is set
        if args.force and os.path.exists(self.cache_dir):
            import shutil
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir)
            print("Cleared clip cache (--force)\n")

        # Validate video size configuration
        if "size" not in data:
            raise VideoGenerationError("Missing required 'size' field in JSON")

        # Extract video configuration
        size = tuple(data["size"])
        fps = data.get("fps", 24)
        events = data.get("events", data)

        print(f"\nGenerating video with {len(events)} clips\n")

        # Generate or retrieve each clip
        clip_paths = []
        for i, event in enumerate(events):
            try:
                clip_path = self._generate_single_clip(event, i, size, fps)
                # Only add non-None paths (skip zero-duration clips)
                if clip_path:
                    clip_paths.append(clip_path)
            except Exception as e:
                print(f"Error processing clip #{i}: {e}")
                print(f"Clip details: {event}")
                raise

        # Handle preview mode
        preview_start = args.preview_start
        preview_duration = args.preview_duration
        audio_only = args.audio_only
        output_ln_folder = Path(args.output_folder)

        if preview_start is not None and preview_duration is not None:
            # For preview, load clips and use moviepy
            print("\nGenerating preview...")
            return self._generate_preview(clip_paths, events, size, fps,
                                         preview_start, preview_duration, data, args)

        # Concatenate all clips
        if audio_only:
            # Extract audio from clips and merge
            output_path = self._generate_audio_only(clip_paths, args)

            # Add BGM if specified
            if "bgm" in data:
                output_path = self._add_bgm_to_audio(output_path, data, events)

            print(f"\nAudio generated: {output_path}")
            return output_path
        else:
            output_path = os.path.join(self.base_path, "output.mp4")
            self._concat_clips_ffmpeg(clip_paths, output_path)

            # Add BGM if specified
            if "bgm" in data:
                output_path = self._add_bgm_to_merged_video(output_path, data, events)

            # Create symlink
            try:
                output_ln_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise RuntimeError(f"Error creating output directory {output_ln_folder}: {str(e)}")

            target = Path(output_path).resolve()
            link = output_ln_folder / (os.path.basename(self.base_path) + '.mp4')
            create_symlink(target, link)

            print(f"\nVideo generated: {output_path}")
            return output_path

    def _generate_preview(self, clip_paths, events, size, fps,
                         preview_start, preview_duration, data, args):
        """Generate preview using moviepy (for subclipping)."""
        # Filter out zero-duration events and their corresponding paths
        valid_clips = [(p, e) for p, e in zip(clip_paths, events) if p is not None]

        if not valid_clips:
            raise VideoGenerationError("No valid clips for preview")

        clips = [VideoFileClip(p).with_start(e["start"])
                for p, e in valid_clips]
        video = CompositeVideoClip(clips, size=size)
        video = video.subclipped(preview_start, preview_start + preview_duration)

        output_path = os.path.join(self.base_path, "output.mp4")
        video.write_videofile(output_path, fps=fps, codec="h264_videotoolbox", audio_codec="aac")
        return output_path

    def _generate_audio_only(self, clip_paths, args):
        """Extract and merge audio from clips."""
        # Filter out None paths (zero-duration clips)
        valid_paths = [p for p in clip_paths if p is not None]

        if not valid_paths:
            raise VideoGenerationError("No valid clips with audio to merge")

        audio_list = os.path.join(self.cache_dir, "audio_list.txt")
        with open(audio_list, 'w') as f:
            for path in valid_paths:
                f.write(f"file '{os.path.abspath(path)}'\n")

        output_path = os.path.join(self.base_path, "output_audio.mp3")
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', audio_list,
            '-vn',  # No video
            '-c:a', 'mp3',
            output_path
        ]

        subprocess.run(cmd, check=True)
        return output_path

    def _add_bgm_to_audio(
        self,
        audio_path: str,
        data: Dict[str, Any],
        events: List[Dict[str, Any]]
    ) -> str:
        """Add background music to audio-only output."""

        bgm_data = data.get("bgm")
        if not isinstance(bgm_data, dict):
            return audio_path

        bgm_file = bgm_data.get("file")
        if not bgm_file:
            return audio_path

        print("\nAdding background music to audio...")

        # Find BGM file
        bgm_paths = [
            os.path.join(self.base_path, "audio", bgm_file),
            os.path.join("assets", "audio", bgm_file),
            os.path.join("assets", bgm_file)
        ]
        bgm_path = next((p for p in bgm_paths if os.path.exists(p)), None)

        if not bgm_path:
            raise VideoGenerationError(f"BGM file not found: {bgm_file}")

        # Calculate BGM start time
        bgm_start = 0.0
        if "start_clip" in bgm_data:
            clip_index = int(bgm_data["start_clip"])
            if clip_index < len(events):
                bgm_start = events[clip_index].get("start", 0.0)
        elif "start_time" in bgm_data:
            bgm_start = float(bgm_data["start_time"])

        bgm_volume = bgm_data.get("volume", 1.0)

        # Output path for audio with BGM
        output_with_bgm = audio_path.replace(".mp3", "_with_bgm.mp3")

        # FFmpeg command to mix audio
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_path,
            '-i', bgm_path,
            '-filter_complex',
            f'[1:a]adelay={int(bgm_start*1000)}|{int(bgm_start*1000)},volume={bgm_volume}[bgm];'
            f'[0:a][bgm]amix=inputs=2:duration=first[aout]',
            '-map', '[aout]',
            '-c:a', 'mp3',
            output_with_bgm
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VideoGenerationError(f"BGM addition to audio failed: {result.stderr}")

        # Replace original with BGM version
        os.replace(output_with_bgm, audio_path)
        print("Background music added to audio")

        return audio_path


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

    # Load JSON configuration
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error loading JSON: {e}")
        raise VideoGenerationError(f"Failed to load configuration: {e}")

    # Create video generator
    generator = VideoGenerator(full_path)

    # Generate video
    output_path = generator.generate_video(data, args)

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
        help="Force regeneration of all clips even if cached"
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