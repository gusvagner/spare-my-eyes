import cv2
from PIL import Image

from spare_my_eyes.capture.camera_preview_feed import PreviewSnapshot

POINT_COLOR_RGB = (0, 230, 118)
POINT_RADIUS_PX = 2


def render_preview(snapshot: PreviewSnapshot, width: int) -> Image.Image:
    marked = snapshot.frame.copy()
    color_bgr = tuple(reversed(POINT_COLOR_RGB))
    for x, y in snapshot.eye_points:
        cv2.circle(marked, (round(x), round(y)), POINT_RADIUS_PX, color_bgr, thickness=-1)
    mirrored_rgb = cv2.cvtColor(cv2.flip(marked, 1), cv2.COLOR_BGR2RGB)
    image = Image.fromarray(mirrored_rgb)
    height = round(image.height * width / image.width)
    return image.resize((width, height))
