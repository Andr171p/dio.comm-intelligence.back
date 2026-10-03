"""
CommunicationAnalysisWorkflow
│
│ communication_id + processing_id
│
├─ 1. prepare_audio
│      ├─ load Communication
│      ├─ download original media
│      ├─ ffprobe
│      ├─ extract/normalize audio → FLAC
│      ├─ VAD
│      ├─ plan_audio_chunks()
│      ├─ upload prepared full audio → tmp S3
│      └─ return AudioPreparationResult
│
├─ 2. prepare_audio_chunks
│      ├─ download prepared FLAC once
│      ├─ materialize chunk 0 → upload → delete
│      ├─ materialize chunk 1 → upload → delete
│      └─ ...
│
├──────────── parallel ──────────────┐
│                                    │
│ 3a. transcribe_chunk × N           │ 3b. diarize_audio
│     → cloud ASR                    │     → full audio
│     → store partial transcript     │     → speaker turns
│                                    │
└──────────────────┬─────────────────┘
                   │
├─ 4. build_transcript
│      ├─ load partial transcripts
│      ├─ convert local → absolute timestamps
│      ├─ remove overlap by accepted range
│      ├─ assign global speakers
│      └─ persist final transcript
│
├─ 5. analyze_communication
│
├─ 6. complete_communication
│
└─ 7. cleanup_processing_artifacts   (best effort)
"""

from .client import connect
from .config import TemporalConfig
from .publisher import create_temporal_publisher

__all__ = ["TemporalConfig", "connect", "create_temporal_publisher"]
