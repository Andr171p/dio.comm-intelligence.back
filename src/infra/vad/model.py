import numpy as np
import numpy.typing as npt
import onnxruntime as ort

type FloatArray = npt.NDArray[np.float32]


class SileroOnnxStream:
    """Stateful inference stream Silero VAD для 16 kHz audio."""

    SAMPLE_RATE = 16_000
    WINDOW_SAMPLES = 512
    CONTEXT_SAMPLES = 64

    def __init__(self, session: ort.InferenceSession) -> None:
        self._session = session
        self._state = np.zeros((2, 1, 128), dtype=np.float32,)
        self._context = np.zeros((1, self.CONTEXT_SAMPLES), dtype=np.float32,)

    def reset(self) -> None:
        """Сбрасывает recurrent state перед новым аудио."""
        self._state.fill(0)
        self._context.fill(0)

    def predict(self, samples: FloatArray) -> float:
        """Получает вероятность речи для одного окна.

        Args:
            samples: Mono float32 PCM из ровно 512 samples
                при частоте 16 kHz.

        Returns:
            Вероятность наличия речи от 0.0 до 1.0.

        Raises:
            ValueError: Если размер или форма окна некорректны.
        """

        if samples.ndim != 1:
            raise ValueError("Silero input must be one-dimensional")

        if len(samples) != self.WINDOW_SAMPLES:
            raise ValueError(f"Silero expects exactly {self.WINDOW_SAMPLES} samples, got {len(samples)}")

        if samples.dtype != np.float32:
            samples = samples.astype(np.float32, copy=False)

        current = samples.reshape(1, -1)

        model_input = np.concatenate((self._context, current), axis=1)

        output, state = self._session.run(
            None,
            {
                "input": model_input,
                "state": self._state,
                "sr": np.array(self.SAMPLE_RATE, dtype=np.int64),
            },
        )

        self._state = state
        self._context = model_input[:, -self.CONTEXT_SAMPLES:].copy()

        return float(np.asarray(output).squeeze())


class SileroOnnxModel:
    """ONNX Runtime представление Silero VAD.

    Объект хранит только загруженную ONNX session и не содержит
    состояния конкретного аудиопотока.

    Для обработки каждого независимого аудио необходимо создавать
    отдельный ``SileroOnnxStream`` через ``create_stream``.
    """

    def __init__(self, model_path: str) -> None:
        options = ort.SessionOptions()

        options.inter_op_num_threads = 1
        options.intra_op_num_threads = 1

        self._session = ort.InferenceSession(
            model_path,
            sess_options=options,
            providers=["CPUExecutionProvider"],
        )

    def create_stream(self) -> SileroOnnxStream:
        """Создаёт независимое состояние для одного аудиопотока."""
        return SileroOnnxStream(self._session)
