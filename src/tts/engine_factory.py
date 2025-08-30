from typing import Dict, Any, Optional
from src.tts.base import TTSEngine

class TTSEngineFactory:
    """
    Factory class for creating TTS engines with caching mechanism.
    Ensures each engine is created only once and reused.
    """
    # Class-level registry of TTS engines
    _engines: Dict[str, type] = {}

    # Cached engine instances
    _engine_instances: Dict[str, TTSEngine] = {}

    @classmethod
    def register_engine(cls, name: str, engine_class: type) -> None:
        """
        Register a new TTS engine with the factory.

        Args:
            name (str): Lowercase name of the TTS engine
            engine_class (type): The TTS engine class to register
        """
        cls._engines[name.lower()] = engine_class

    @classmethod
    def create_engine(
        cls,
        tts_config: Dict[str, Any]
    ) -> TTSEngine:
        """
        Create or retrieve a cached TTS engine instance based on the configuration.

        Args:
            tts_config (Dict[str, Any]): Configuration for the TTS engine

        Returns:
            TTSEngine: Instantiated or cached TTS engine

        Raises:
            ValueError: If the specified engine is not registered or configuration is invalid
        """
        # Extract engine name (use 'tts_engine' key)
        engine_name = tts_config.get('tts_engine', '').lower()

        # Fallback to dummy engine if not specified or not found
        if not engine_name or engine_name not in cls._engines:
            engine_name = 'dummy'

        # Check if an instance already exists
        if engine_name in cls._engine_instances:
            cached_engine = cls._engine_instances[engine_name]

            # Validate configuration for the cached engine
            if not cached_engine.validate_configuration(tts_config):
                raise ValueError(f"Invalid configuration for TTS engine '{engine_name}'")

            return cached_engine

        # Retrieve the engine class
        engine_class = cls._engines[engine_name]

        # Create a new engine instance
        engine = engine_class()

        # Validate the configuration for this engine
        if not engine.validate_configuration(tts_config):
            raise ValueError(f"Invalid configuration for TTS engine '{engine_name}'")

        # Cache the engine instance
        cls._engine_instances[engine_name] = engine

        return engine

    @classmethod
    def list_engines(cls) -> list:
        """
        List all registered TTS engines.

        Returns:
            list: Names of registered TTS engines
        """
        return list(cls._engines.keys())

    @classmethod
    def clear_cached_engines(cls) -> None:
        """
        Clear all cached engine instances.
        Useful for resetting the factory or in testing scenarios.
        """
        cls._engine_instances.clear()

# Utility function to simplify engine registration
def register_tts_engine(name: str):
    """
    Decorator to register a TTS engine with the factory.

    Args:
        name (str): Name to register the engine under

    Returns:
        Callable: Decorator function
    """
    def decorator(engine_class: type):
        TTSEngineFactory.register_engine(name, engine_class)
        return engine_class
    return decorator

# Example of how to register a real TTS engine (to be implemented)
# @register_tts_engine('google')
# class GoogleTTSEngine(TTSEngine):
#     def generate_audio(self, text: str, **kwargs) -> str:
#         # Actual Google TTS implementation
#         pass
