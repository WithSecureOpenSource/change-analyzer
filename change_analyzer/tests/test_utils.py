from PIL import ImageGrab

from change_analyzer.utils import image_pad_resize_to, iou


def test_image_pad_resize_to_wide():
    size = (800, 400)
    im = image_pad_resize_to(ImageGrab.grab(), size)
    im.show()
    assert im.size == size


# def test_image_pad_resize_to_square():
#     size = (800, 800)
#     im = image_pad_resize_to(ImageGrab.grab(), size)
#     # im.show()
#     assert im.size == size
#
#
# def test_image_pad_resize_to_tall():
#     size = (400, 800)
#     im = image_pad_resize_to(ImageGrab.grab(), size)
#     # im.show()
#     assert im.size == size


def test_zero_iou():
    rect0 = {"x": 0, "y": 0, "width": 100, "height": 100}
    rect1 = {"x": 101, "y": 101, "width": 100, "height": 100}
    assert iou(rect0, rect1) == 0


def test_full_iou():
    rect0 = {"x": 0, "y": 0, "width": 100, "height": 100}
    rect1 = {"x": 0, "y": 0, "width": 100, "height": 100}
    assert iou(rect0, rect1) == 1
