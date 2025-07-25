import os
from typing import Dict, Any, List
from .base import SceneConverter
from .text.strategy_factory import TextSceneStrategyFactory

class TextSceneConverter(SceneConverter):
    def convert(
        self,
        scene: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Convert a text scene to virtual clips

        Args:
            scene (Dict[str, Any]): Text scene details

        Returns:
            List[Dict[str, Any]]: Virtual clips for the text scene

        Raises:
            ValueError: If configuration is invalid
        """
        # Validate mode
        mode = scene.get('mode')

        # Validate background configuration
        if 'background' in scene and 'bgcolor' in scene:
            raise ValueError("Cannot specify both 'background' and 'bgcolor'")

        # Validate text configuration
        text_entries = scene.get('text', [])
        if not text_entries:
            raise ValueError("At least one text entry is required")

        # Extract scene-level configurations
        valign = scene.get('valign', 'center')
        padding = scene.get('padding', 40)
        line_spacing = scene.get('line_spacing', 20)

        # Validate text configuration
        for entry in text_entries:
            # Validate mutually exclusive duration and TTS
            if 'duration' in entry and 'tts' in entry:
                raise ValueError("Cannot specify both 'duration' and 'tts' for a text entry")

            # Validate font configuration
            if 'font' not in entry:
                raise ValueError("Font configuration is required for each text entry")

            font = entry['font']
            if 'file' not in font:
                raise ValueError("Font file is required")
            if 'size' not in font:
                raise ValueError("Font size is required")
            if 'color' not in font:
                raise ValueError("Font color is required")

        # Get the appropriate strategy
        strategy = TextSceneStrategyFactory.get_strategy(mode)

        # Calculate text positions using the strategy's method
        positioned_entries = strategy.calculate_text_positions(
            text_entries,
            self.screen_size,
            valign=valign,
            padding=padding,
            line_spacing=line_spacing
        )

        # Convert using the strategy
        return strategy.convert(scene, positioned_entries)