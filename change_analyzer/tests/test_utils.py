from PIL import ImageGrab

from change_analyzer.utils import image_pad_resize_to


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
