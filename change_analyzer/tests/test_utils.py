from PIL import Image
import os

from change_analyzer.utils import image_pad_resize_to


def test_image_pad_resize_to_wide():
    size = (200, 200)
    cwd = os.getcwd()
    image_from_disk = Image.open(f"{cwd}/change_analyzer/tests/400x400.png")
    im = image_pad_resize_to(image_from_disk, size)
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
