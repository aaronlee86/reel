import argparse
import json
import os
from pathlib import Path
from convert_scenes_core import convert_scenes_to_clips

def main():
    parser = argparse.ArgumentParser(description="Convert scene description JSON to clips.json inside workspace")
    parser.add_argument("video_folder", type=str, help="Folder name under workspace (e.g. video001)")
    args = parser.parse_args()

    base_path = Path("workspace") / args.video_folder
    input_path = base_path / "input_scene.json"
    output_path = base_path / "clips.json"
    audio_dir = base_path / "audio"

    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return

    os.makedirs(audio_dir, exist_ok=True)

    with open(input_path, "r", encoding="utf-8") as f:
        scene_data = json.load(f)

    clips = convert_scenes_to_clips(scene_data, audio_dir=audio_dir)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clips, f, ensure_ascii=False, indent=2)

    print(f"✅ clips.json generated at: {output_path}")

if __name__ == "__main__":
    main()
