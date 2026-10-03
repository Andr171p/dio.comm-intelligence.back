from src.infra.s3 import S3Client, S3Config
from src.infra.services.communications import SrvCommunicationsClient, SrvCommunicationsConfig
from src.infra.services.media import SrvMediaClient, SrvMediaConfig
from src.infra.temporal.config import AudioConfig
from src.infra.whisper import WhisperConfig, WhisperRecognizer

audio_config = AudioConfig()

communications_config = SrvCommunicationsConfig()  # type: ignore
communications_client = SrvCommunicationsClient(communications_config)

media_config = SrvMediaConfig()  # type: ignore
media_client = SrvMediaClient(media_config)

s3_config = S3Config()  # type: ignore
s3_client = S3Client(s3_config)

whisper_config = WhisperConfig()  # type: ignore
speech_recognizer = whisper_recognizer = WhisperRecognizer(whisper_config)
