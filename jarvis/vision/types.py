from enum import Enum, auto
from typing import TypedDict, Optional, Dict, Any, Tuple

class AttentionState(Enum):
    USER_PRESENT = auto()
    USER_ENGAGED = auto()
    USER_DISTRACTED = auto()
    USER_FOCUSED = auto()
    USER_IDLE = auto()
    USER_ABSENT = auto()

class Point(TypedDict):
    x: float
    y: float
    z: float

class EyeData(TypedDict):
    landmarks: list[Point]
    iris_center: Optional[Point]
    bounding_box: Tuple[float, float, float, float]  # xmin, ymin, width, height
    confidence: float

class BlinkData(TypedDict):
    blink: bool
    type: str  # "none", "single", "double", "long"
    duration_ms: int
    confidence: float

class GazeData(TypedDict):
    direction: str  # "left", "right", "center", "up", "down", "unknown"
    confidence: float
    raw_horizontal_ratio: float
    raw_vertical_ratio: float

class AttentionData(TypedDict):
    attention_state: str
    confidence: float
    metrics: Dict[str, Any]
