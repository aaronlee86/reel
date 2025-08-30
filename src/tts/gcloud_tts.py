import os
from typing import Dict, Any, Optional
from .engine_factory import register_tts_engine
from src.tts.base import TTSEngine

@register_tts_engine('gcloud')
class GoogleCloudTTSEngine(TTSEngine):
    """
    Google Cloud Text-to-Speech Engine implementation with lazy importing.
    """

    def __init__(self):
        """
        Initialize the Google Cloud TTS Engine.
        Client is created lazily when first needed.
        """
        self._client = None
        self._texttospeech = None
        self.name = self.__class__.__name__
        print(f"{self.name} Created")

    @property
    def texttospeech(self):
        """Lazy import of texttospeech module"""
        if self._texttospeech is None:
            print(f"dynamic importing texttospeech from google.cloud")
            from google.cloud import texttospeech
            self._texttospeech = texttospeech
        return self._texttospeech

    @property
    def client(self):
        """Lazy initialization of TTS client"""
        if self._client is None:
            self._client = self.texttospeech.TextToSpeechClient()
        return self._client

    def call_api(self, payload):
        # Now using the lazy-loaded module
        synthesis_input = self.texttospeech.SynthesisInput(text=payload['text'])

        # Build the voice request
        audio_config = self.texttospeech.AudioConfig(
            audio_encoding = self.texttospeech.AudioEncoding.MP3,
            speaking_rate = payload['speed']
        )

        lang = "-".join(payload['voice'].split("-")[:2])
        voice = self.texttospeech.VoiceSelectionParams(
            language_code = lang,
            name = payload['voice']
        )

        response = self.client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )

        return response

    def generate_audio(
            self,
            text: str,
            output_path: str,
            **kwargs
        ) -> str:
        """
        Synthesize text to speech using Google Cloud TTS.

        Args:
            text (str): Text to convert to speech
            output_path (str): Path to save audio file
            **kwargs: Additional arguments

        Returns:
            str: Path to the generated audio file
        """
        if os.path.exists(output_path):
            print(f"[{self.__class__.__name__}] Audio already exists at: {output_path}. Skipping generation.")
            return output_path

        # Prepare payload with default values
        payload = {
            'text': text,
            'speed': kwargs.get('speed', 1.0),
            'voice': kwargs.get('voice')
        }

        try:
            response = self.call_api(payload)
            with open(output_path, 'wb') as file:
                file.write(response.audio_content)
                print(f"[{self.name}] Generated audio at: {output_path}")
        except Exception as e:
            raise RuntimeError(f"{self.name} generation failed: {e}")

        return output_path

    def list_available_voices(self) -> Dict[str, Any]:
        """
        List available voices from Google Cloud TTS.

        Returns:
            Dict[str, Any]: A dictionary of available voices with their details.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(f"{self.name}")

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for Google Cloud TTS.

        Args:
            config (Dict[str, Any]): Configuration dictionary to validate

        Returns:
            bool: True if configuration is valid, False otherwise
        """
        keys_to_check =['tts_engine','voice','text']
        for key in keys_to_check:
            if key not in config.keys():
                raise ValueError(f"Invalid configuration for TTS engine '{self.name}': lack of {key}")
        return True

    def gen_filename(self, **kwargs: Any) -> str:
        try:
            engine_name, voice, speed = kwargs['tts_engine'], kwargs['voice'], kwargs['speed']
            return super().gen_filename(**kwargs)+f"_{engine_name}_{voice}_{speed}.mp3"
        except Exception as e:
            raise ValueError(f"gen_filename in {self.name} failed: {e}")
