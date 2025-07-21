from typing import Dict, Any, Type, Optional, List
from .converters.base import SceneConverter
from .converters.image_converter import ImageSceneConverter
from .converters.text_converter import TextSceneConverter
from .converters.video_converter import VideoSceneConverter

class SceneConverterFactory:
    """
    Factory class to create appropriate scene converters
    """
    _converters: Dict[str, Type[SceneConverter]] = {
        "image": ImageSceneConverter,
        "text": TextSceneConverter,
        "video": VideoSceneConverter
    }

    @classmethod
    def get_converter(
        cls,
        scene_type: str,
        **kwargs
    ) -> SceneConverter:
        """
        Get the appropriate scene converter based on scene type

        Args:
            scene_type (str): Type of the scene
            **kwargs: Additional arguments to pass to the converter

        Returns:
            SceneConverter: Converter for the specific scene type

        Raises:
            ValueError: If no converter is found for the given scene type
        """
        if scene_type not in cls._converters:
            raise ValueError(f"No converter found for scene type: {scene_type}")

        # Get the converter class
        converter_class = cls._converters[scene_type]

        # Instantiate the converter, passing only valid arguments
        valid_init_params = ['screen_size', 'fps', 'default_duration']
        filtered_kwargs = {
            k: v for k, v in kwargs.items()
            if k in valid_init_params
        }

        return converter_class(**filtered_kwargs)

    @classmethod
    def register_converter(cls, scene_type: str, converter: Type[SceneConverter]):
        """
        Register a new scene converter

        Args:
            scene_type (str): Type of the scene
            converter (Type[SceneConverter]): Converter class for the scene type
        """
        cls._converters[scene_type] = converter