from typing import Protocol

import numpy as np
import numpy.typing as npt

Frame = npt.NDArray[np.uint8]


class FrameSource(Protocol):
    def open(self) -> None: ...

    def read(self) -> Frame: ...

    def close(self) -> None: ...
