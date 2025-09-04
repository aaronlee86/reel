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
        halign = scene.get('halign', 'center')
        v_padding = scene.get('v_padding')
        h_padding = scene.get('h_padding')
        para_spacing = scene.get('para_spacing')
        lin_spacing = scene.get('line_spacing')

        # Validate horizontal alignment
        if halign not in ['left', 'center', 'right']:
           raise ValueError(f"Invalid halign value: {halign}. Must be 'left', 'center', or 'right'.")

        # Validate vertical alignment
        if valign not in ['top', 'center', 'bottom']:
           raise ValueError(f"Invalid valign value: {valign}. Must be 'top', 'center', or 'bottom'.")

        # Validate text configuration
        for entry in text_entries:
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

            # Validate font file exists in assets/fonts directory
            font_file = font['file']
            font_path = os.path.join("assets", "fonts", font_file)
            if not os.path.isfile(font_path):
                raise ValueError(f"Font file does not exist: {font_path}")

            font['file'] = font_path

        # Get the appropriate strategy
        strategy = TextSceneStrategyFactory.get_strategy(mode)

        # Calculate text positions using the strategy's method
        positioned_sentences = strategy.calculate_text_positions(
            text_entries,
            self.screen_size,
            valign=valign,
            halign=halign,
            v_padding=v_padding,
            h_padding=h_padding,
            para_spacing=para_spacing,
            line_spacing=lin_spacing
        )

        # Convert using the strategy
        return strategy.convert(scene, positioned_sentences)