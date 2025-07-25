from typing import Dict, Any
from .base import TextSceneStrategy
from .all_mode import AllModeStrategy
from .all_with_highlight_mode import AllWithHighlightModeStrategy
from .append_center_mode import AppendCenterModeStrategy

class TextSceneStrategyFactory:
    """
    Factory for creating text scene conversion strategies
    """
    _strategies: Dict[str, TextSceneStrategy] = {
        'all': AllModeStrategy(),
        'all_with_highlight': AllWithHighlightModeStrategy(),
        'append_center': AppendCenterModeStrategy()
    }

    @classmethod
    def get_strategy(cls, mode: str) -> TextSceneStrategy:
        """
        Get the appropriate strategy for a given mode

        Args:
            mode (str): Scene mode

        Returns:
            TextSceneStrategy: Conversion strategy for the mode

        Raises:
            ValueError: If no strategy is found for the mode
        """
        if mode not in cls._strategies:
            raise ValueError(f"No strategy found for mode: {mode}")

        return cls._strategies[mode]

    @classmethod
    def register_strategy(cls, mode: str, strategy: TextSceneStrategy):
        """
        Register a new strategy for a mode

        Args:
            mode (str): Scene mode
            strategy (TextSceneStrategy): Conversion strategy to register
        """
        cls._strategies[mode] = strategy