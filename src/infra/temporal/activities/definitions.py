from src.infra.aitunnel import AiTunnelRecognizer, AiTunnelRecognizerConfig
from src.infra.s3 import S3Client, S3Config
from src.infra.services.communications import SrvCommunicationsClient, SrvCommunicationsConfig
from src.infra.services.media import SrvMediaClient, SrvMediaConfig
from src.infra.temporal.config import AudioConfig

audio_config = AudioConfig()

communications_config = SrvCommunicationsConfig()  # type: ignore
communications_client = SrvCommunicationsClient(communications_config)

media_config = SrvMediaConfig()  # type: ignore
media_client = SrvMediaClient(media_config)

s3_config = S3Config()  # type: ignore
s3_client = S3Client(s3_config)

aitunnel_recognizer_config = AiTunnelRecognizerConfig()  # type: ignore
speech_recognizer = aitunnel_recognizer = AiTunnelRecognizer(aitunnel_recognizer_config)
