import numpy as np

from spare_my_eyes.analysis.live_readout import LiveReading
from spare_my_eyes.capture.camera_preview_feed import PreviewSnapshot
from spare_my_eyes.ui.preview_image import POINT_COLOR_RGB, render_preview

READING = LiveReading(True, 1.0, 0.0, False, 60.0, 0, 0)


def snapshot_with_point(point: tuple[float, float]) -> PreviewSnapshot:
    frame = np.zeros((48, 64, 3), dtype=np.uint8)
    return PreviewSnapshot(frame, (point,), READING, 0.0)


def test_render_preview_scales_to_requested_width_keeping_aspect() -> None:
    image = render_preview(snapshot_with_point((10.0, 10.0)), width=128)
    assert image.size == (128, 96)


def test_render_preview_draws_points_on_the_mirrored_image() -> None:
    image = render_preview(snapshot_with_point((10.0, 20.0)), width=64)
    assert image.getpixel((53, 20)) == POINT_COLOR_RGB
    assert image.getpixel((10, 20)) == (0, 0, 0)


def test_render_preview_leaves_the_camera_frame_untouched() -> None:
    snapshot = snapshot_with_point((10.0, 20.0))
    render_preview(snapshot, width=64)
    assert not snapshot.frame.any()
