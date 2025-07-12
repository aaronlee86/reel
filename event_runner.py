import os
import json
import argparse
import numpy as np
from moviepy import ImageClip, AudioFileClip, VideoFileClip, ColorClip, CompositeVideoClip
from render_utils import render_text_block

def loadAudioFile(base_path, filename):
    return os.path.join(base_path, "audio", filename)

def build_clip(event, base_path, size=(1280, 720)):
    start = event["start"]

    def relpath(f):
        return os.path.join(base_path, f)

    if event["type"] == "image":
        clip = ImageClip(relpath(event["file"])).resize(height=size[1]) if hasattr(ImageClip(relpath(event["file"])), 'resize') else ImageClip(relpath(event["file"])).with_start(start)
        if "duration" in event:
            clip = clip.with_duration(event["duration"])
        if "audio" in event:
            clip = clip.with_audio(AudioFileClip(loadAudioFile(base_path, event["audio"])))
        return clip

    elif event["type"] == "text":
        sentences = event["sentences"]
        background = event.get("background", "#FFFFFF")
        duration = event.get("duration")
        audio_path = event.get("audio")
        text_lines = [s["text"] for s in sentences]
        positions = [[s["x"], s["y"]] for s in sentences]
        font_sizes = [s["font_size"] for s in sentences]
        font_path = os.path.join("assets", "fonts", sentences[0]["font"]) if sentences else ""
        font_colors = [s.get("font_color", "#000000") for s in sentences]
        bold_flags = [s.get("bold", False) for s in sentences]
        italic_flags = [s.get("italic", False) for s in sentences]

        img = render_text_block(
            text_lines=text_lines,
            positions=positions,
            font_path=font_path,
            font_sizes=font_sizes,
            font_colors=font_colors,
            bold_flags=bold_flags,
            italic_flags=italic_flags,
            bg_color=background,
            size=size
        )

        clip = ImageClip(np.array(img)).with_start(start)
        if audio_path:
            audio = AudioFileClip(loadAudioFile(base_path, audio_path))
            audio_duration = audio.duration
            clip_duration = event.get("duration", audio_duration)
            final_duration = min(audio_duration, clip_duration)
            clip = clip.with_audio(audio).with_duration(final_duration)
        else:
            clip = clip.with_duration(duration)
        return clip

    elif event["type"] == "video":
        clip = VideoFileClip(relpath(event["file"]))
        duration = event.get("duration")
        if duration:
            clip = clip.subclip(0, duration)
        return clip.with_start(start)

    elif event["type"] == "color":
        color = tuple(event["color"])
        duration = event.get("duration")
        clip = ColorClip(size=size, color=color).with_start(start)
        if "audio" in event:
            audio = AudioFileClip(loadAudioFile(base_path, event["audio"]))
            clip = clip.with_audio(audio).with_duration(audio.duration)
        else:
            clip = clip.with_duration(duration)
        return clip

    elif event["type"] == "audio":
        audio = AudioFileClip(loadAudioFile(base_path, event["file"]))
        audio_duration = audio.duration
        clip_duration = event.get("duration", audio_duration)
        final_duration = min(audio_duration, clip_duration)
        bg = ColorClip(size=size, color=(0, 0, 0)).with_duration(final_duration).with_audio(audio).with_start(start)
        return bg

    return None

def generate_video_from_json(folder_path, preview_start=None, preview_duration=None):
    full_path = os.path.join("workspace", folder_path)
    json_file = "clips.json"
    with open(os.path.join(full_path, json_file), 'r', encoding='utf-8') as f:
        data = json.load(f)

    if "size" not in data:
        raise ValueError("Missing required 'size' field in JSON. Please specify a resolution like [1280, 720].")

    size = tuple(data["size"])
    fps = data.get("fps", 24)
    events = data.get("events", data)  # fallback for backward compatibility

    clips = [build_clip(e, full_path, size=size) for e in events if build_clip(e, full_path, size=size) is not None]
    video = CompositeVideoClip(clips, size=size)

    if preview_start is not None and preview_duration is not None:
        video = video.subclip(preview_start, preview_start + preview_duration)

    output_path = os.path.join(full_path, "output.mp4")
    video.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")

def main():
    parser = argparse.ArgumentParser(description="Generate video from event JSON.")
    parser.add_argument("folder", help="Subfolder under workspace containing clips.json and assets")
    parser.add_argument("--preview-start", type=float, help="Start time in seconds for preview clip")
    parser.add_argument("--preview-duration", type=float, help="Duration in seconds for preview clip")
    args = parser.parse_args()

    generate_video_from_json(args.folder, args.preview_start, args.preview_duration)

if __name__ == "__main__":
    main()
