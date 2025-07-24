from typing import Dict, Any
from .factory import SceneConverterFactory

def convert_video_project(input_json: Dict[str, Any], project_name: str = 'default') -> Dict[str, Any]:
    """
    Convert input video project JSON to output format

    Args:
        input_json (Dict[str, Any]): Input video project JSON
        project_name (str): Name of the project

    Returns:
        Dict[str, Any]: Converted video project JSON

    Raises:
        ValueError: If screen size or fps is not specified or if any scene fails to convert
    """
    # Validate screen size
    if 'screen_size' not in input_json:
        raise ValueError("Screen size must be specified in the top-level JSON")

    screen_size = input_json['screen_size']

    # Validate screen size format
    if not isinstance(screen_size, list) or len(screen_size) != 2:
        raise ValueError("Screen size must be a list of two integers [width, height]")

    # Validate fps
    if 'fps' not in input_json:
        raise ValueError("FPS must be specified in the top-level JSON")

    fps = input_json['fps']

    # Create the base output structure
    output = {
        "size": screen_size,
        "fps": fps,
        "bgm": input_json.get("bgm", {}),
        "vclips": []
    }

    # Convert each scene
    for scene_index, scene in enumerate(input_json.get("scenes", []), 1):
        # Determine scene type
        scene_type = scene.get("type", "unknown").lower()

        try:
            # Get the appropriate converter and convert the scene
            converter = SceneConverterFactory.get_converter(
                scene_type,
                screen_size=screen_size,
                fps=fps
            )
            scene_vclips = converter.convert(scene)

            # Extend the vclips list
            output["vclips"].extend(scene_vclips)

        except (ValueError, TypeError) as e:
            # Raise a more informative error that includes the scene index
            raise ValueError(f"Error processing scene {scene_index}: {str(e)}") from e

    return output