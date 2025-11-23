import os
from typing import Dict, Any
from unittest import result
from .engine_factory import register_tts_engine
from src.tts.base import TTSEngine

@register_tts_engine('azure')
class AzureTTSEngine(TTSEngine):
    """
    Azure Text-to-Speech Engine implementation with lazy importing.
    """

    def __init__(self):
        """
        Initialize the Azure TTS Engine.
        Client is created lazily when first needed.
        """
        self._speechsdk = None
        speech_key = os.getenv("AZURE_SPEECH_KEY")
        speech_endpoint = os.getenv("AZURE_ENDPOINT")
        self._speech_config = self.speechsdk.SpeechConfig(subscription=speech_key, endpoint=speech_endpoint)
        self._speech_config.set_speech_synthesis_output_format(self.speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3)
        self.name = self.__class__.__name__
        print(f"{self.name} Created")

    @property
    def speechsdk(self):
        """Lazy initialization of TTS client"""
        if self._speechsdk is None:
            print(f"dynamic importing texttospeech from Azure SDK...")
            import azure.cognitiveservices.speech as speechsdk
            self._speechsdk = speechsdk
        return self._speechsdk

    def generate_audio(
            self,
            text: str,
            output_path: str,
            **kwargs
        ) -> str:
        """
        Synthesize text to speech using Azure/OpenAI TTS.

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

        try:
            audio_config = self.speechsdk.audio.AudioOutputConfig(filename=output_path)
            self._speech_config.speech_synthesis_voice_name = kwargs.get('voice')
            synthesizer = self.speechsdk.SpeechSynthesizer(speech_config=self._speech_config, audio_config=audio_config)

            result = synthesizer.speak_text_async(text).get()

            if result.reason == self._speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"[{self.name}] Generated audio at: {output_path}")
            else:
                print("Error:", result.reason)
        except Exception as e:
            raise RuntimeError(f"{self.name} generation failed: {e}")

        return output_path

    def list_available_voices(self) -> Dict[str, Any]:
        """
        List available voices from Azure/OpenAI TTS.

        Returns:
            Dict[str, Any]: A dictionary of available voices with their details.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(f"{self.name}")

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate the configuration for Azure/OpenAI TTS.

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
