import os
import json
import argparse
import numpy as np
from moviepy import ImageClip, AudioFileClip, VideoFileClip, ColorClip, CompositeVideoClip, CompositeAudioClip
import moviepy.audio.fx as afx
from render_utils import render_text_block

def loadAudioFile(base_path, filename):
    return os.path.join(base_path, "audio", filename)

def build_clip(event, base_path, size=(1280, 720)):
    start = event["start"]

    def relpath(f):
        return os.path.join(base_path, f)

    if event["type"] == "image":
        if "file" in event:
            clip = ImageClip(relpath(event["file"])).resized(height=size[1])
        else:
            bgcolor = event.get("bgcolor", [0, 0, 0])
            clip = ColorClip(size=size, color=tuple(bgcolor))
        clip = clip.with_start(start)
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

    # Add background music if specified
    bgm_data = data.get("bgm")
    if isinstance(bgm_data, dict):
        bgm_file = bgm_data.get("file")
        bgm_volume = bgm_data.get("volume", 1.0)
        bgm_start = bgm_data.get("start", 0.0)
        if bgm_file:
            bgm_audio = AudioFileClip(loadAudioFile(full_path, bgm_file))
            bgm_audio = bgm_audio.with_effects([afx.MultiplyVolume(bgm_volume)]).with_start(bgm_start)
            max_bgm_duration = max(0, video.duration - bgm_start)
            bgm_audio = bgm_audio.subclipped(0, min(bgm_audio.duration, max_bgm_duration))
            if video.audio:
                video = video.with_audio(CompositeAudioClip([video.audio, bgm_audio]))
            else:
                video = video.with_audio(bgm_audio)

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
