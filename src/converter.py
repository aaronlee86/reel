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
        ValueError: If any scene fails to convert
    """
    # Extract project-level parameters
    screen_size = input_json.get("screen_size", [1920, 1080])
    fps = input_json.get("fps", 24)

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
            scene_vclips = converter.convert(scene, project_name=project_name)

            # Extend the vclips list
            output["vclips"].extend(scene_vclips)

        except (ValueError, TypeError) as e:
            # Raise a more informative error that includes the scene index
            raise ValueError(f"Error processing scene {scene_index}: {str(e)}") from e

    return output