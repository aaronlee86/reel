import os
import hashlib
import random
from typing import List, Dict, Tuple
from dataclasses import dataclass

DEFAULT_PADDING = 40
DEFAULT_LINE_SPACING = 20

@dataclass
class Screen:
    width: int
    height: int

def hash_text(text: str) -> str:
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]

def simulate_tts_audio(text: str, audio_dir: str) -> Tuple[str, float]:
    filename = f"tts_{hash_text(text)}.mp3"
    filepath = os.path.join(audio_dir, filename)
    duration = round(1.0 + len(text.split()) * 0.4 + random.uniform(0.0, 0.3), 2)
    return filename, duration

# convert_scenes_to_clips returns a dict with size, fps, and clips

def convert_scenes_to_clips(scene_data: Dict, audio_dir: str = "audio") -> Dict:
    screen = Screen(*scene_data["screen_size"])
    clips = []
    current_time = 0.0

    def compute_y_positions(mode: str, screen: Screen, sentences: List[Dict], padding: int, spacing: int, alignment: str = "center") -> List[int]:
        font_heights = [s["font_size"] for s in sentences]
        total_height = sum(font_heights) + spacing * (len(sentences) - 1)

        if mode == "append_center":
            last_y = screen.height // 2
            return [last_y - (len(sentences) - 1 - i) * (sentences[i]["font_size"] + spacing) for i in range(len(sentences))]

        if mode == "append_top":
            return [padding + i * (sentences[i]["font_size"] + spacing) for i in range(len(sentences))]

        if mode in ("all", "all_with_highlight"):
            if alignment == "top":
                start_y = padding
            elif alignment == "bottom":
                start_y = screen.height - total_height - padding
            else:
                start_y = (screen.height - total_height) // 2
            return [start_y + i * (sentences[i]["font_size"] + spacing) for i in range(len(sentences))]

        return [screen.height // 2] * len(sentences)

    def compute_x_position(alignment: str, screen_width: int, padding: int) -> int:
        if alignment == "left":
            return padding
        elif alignment == "right":
            return screen_width - padding
        else:
            return screen_width // 2

    def process_text_scene(scene: Dict, screen: Screen, audio_dir: str, clip_list: List[Dict], current_time: float) -> float:
        mode = scene["mode"]
        padding = scene.get("padding", DEFAULT_PADDING)
        spacing = scene.get("line_spacing", DEFAULT_LINE_SPACING)
        alignment = scene.get("alignment", "center")
        highlight_style = scene.get("highlight_style", {})

        base_sentences = []
        for s in scene["text"]:
            audio_file, duration = simulate_tts_audio(s["text"], audio_dir)
            base_sentences.append({
                "text": s["text"],
                "font": s.get("font", "default.ttf"),
                "font_size": s.get("font_size", 40),
                "font_color": s.get("font_color", "#000000"),
                "horizontal_alignment": s.get("horizontal_alignment", "center"),
                "audio_file": audio_file,
                "audio_duration": duration
            })

        if mode in ("append_center", "append_top"):
            for i in range(len(base_sentences)):
                sub_sentences = base_sentences[:i+1]
                y_positions = compute_y_positions(mode, screen, sub_sentences, padding, spacing)
                clip = {
                    "type": "text",
                    "background": scene.get("background"),
                    "audio": sub_sentences[-1]["audio_file"],
                    "start": current_time,
                    "duration": sub_sentences[-1]["audio_duration"],
                    "sentences": []
                }
                for idx, s in enumerate(sub_sentences):
                    clip["sentences"].append({
                        "text": s["text"],
                        "font": s["font"],
                        "font_size": s["font_size"],
                        "font_color": s["font_color"],
                        "x": compute_x_position(s["horizontal_alignment"], screen.width, padding),
                        "y": y_positions[idx],
                        "bold": False,
                        "italic": False
                    })
                clip_list.append(clip)
                current_time += clip["duration"]

        elif mode == "all_with_highlight":
            for h_idx in range(len(base_sentences)):
                y_positions = compute_y_positions("all_with_highlight", screen, base_sentences, padding, spacing, alignment)
                clip = {
                    "type": "text",
                    "background": scene.get("background"),
                    "audio": base_sentences[h_idx]["audio_file"],
                    "start": current_time,
                    "duration": base_sentences[h_idx]["audio_duration"],
                    "sentences": []
                }
                for idx, s in enumerate(base_sentences):
                    highlighted = (idx == h_idx)
                    clip["sentences"].append({
                        "text": s["text"],
                        "font": highlight_style.get("font", s["font"]) if highlighted else s["font"],
                        "font_size": s["font_size"],
                        "font_color": highlight_style.get("font_color", s["font_color"]) if highlighted else s["font_color"],
                        "x": compute_x_position(s["horizontal_alignment"], screen.width, padding),
                        "y": y_positions[idx],
                        "bold": highlighted and highlight_style.get("bold", False),
                        "italic": highlighted and highlight_style.get("italic", False)
                    })
                clip_list.append(clip)
                current_time += clip["duration"]

        elif mode == "all":
            y_positions = compute_y_positions("all", screen, base_sentences, padding, spacing, alignment)
            duration = sum(s["audio_duration"] for s in base_sentences)
            clip = {
                "type": "text",
                "background": scene.get("background"),
                "audio": base_sentences[0]["audio_file"],
                "start": current_time,
                "duration": duration,
                "sentences": []
            }
            for idx, s in enumerate(base_sentences):
                clip["sentences"].append({
                    "text": s["text"],
                    "font": s["font"],
                    "font_size": s["font_size"],
                    "font_color": s["font_color"],
                    "x": compute_x_position(s["horizontal_alignment"], screen.width, padding),
                    "y": y_positions[idx],
                    "bold": False,
                    "italic": False
                })
            clip_list.append(clip)
            current_time += clip["duration"]

        return current_time

    for scene in scene_data["scenes"]:
        if scene["type"] == "text":
            current_time = process_text_scene(scene, screen, audio_dir, clips, current_time)

        elif scene["type"] == "image":
            if "tts_engine" in scene and "text" in scene:
                audio_file, duration = simulate_tts_audio(scene["text"], audio_dir)
                audio = audio_file
            else:
                audio = scene.get("audio")
                duration = scene.get("duration", 3)
            clip = {
                "type": "image",
                "start": current_time,
                "duration": duration,
                "file": scene["file"],
                "audio": audio
            }
            clips.append(clip)
            current_time += clip["duration"]

        elif scene["type"] == "audio":
            clip = {
                "type": "audio",
                "file": scene["file"],
                "start": current_time,
                "duration": scene.get("duration", 3),
                "volume": scene.get("volume", 1.0)
            }
            clips.append(clip)
            current_time += clip["duration"]

        elif scene["type"] == "color":
            if "tts_engine" in scene and "text" in scene:
                audio_file, duration = simulate_tts_audio(scene["text"], audio_dir)
                audio = audio_file
            else:
                audio = scene.get("audio")
                duration = scene.get("duration", 3)
            color_val = scene["color"]
            if isinstance(color_val, str) and color_val.startswith("#"):
                rgb = tuple(int(color_val[i:i+2], 16) for i in (1, 3, 5))
            else:
                rgb = color_val
            clip = {
                "type": "color",
                "start": current_time,
                "duration": duration,
                "color": rgb,
                "audio": audio
            }
            clips.append(clip)
            current_time += clip["duration"]

    return {
        "size": [screen.width, screen.height],
        "fps": scene_data.get("fps", 24),
        "events": clips
    }
