from PIL import Image
from math import sqrt, ceil
from random import choices
from itertools import chain
import sys
import os
import ctypes

DEBUG = False
_print = print


def print(*args, **kwargs):
    if DEBUG:
        _print(*args, **kwargs)
    return print


class ImageTomb:
    def __init__(self, filename: str = "image.png"):
        # 设置文件名
        self.filename = filename
        # 打开文件，文件不存在则创建
        try:
            raw_image = Image.open(filename)
        except FileNotFoundError:
            print("Error: Could not open file, creating a new one.")
            raw_image = Image.new("RGBA", (2, 2), (0, 0, 0, 1))
        except Exception as e:
            print("Error: Could not open file:", e)
            exit(1)
        # 强制转换为 RGBA 格式
        self.image = raw_image.convert("RGBA")
        # 获取图片边长
        self.side_length = self.image.size[0]
        # 获取图片最大像素数量
        self.max_pixel_num = self.side_length**2
        # 获取第一个像素的 RGBA 值
        r, g, b, a = self.image.getpixel((0, 0))
        # 计算下一个可用像素的位置
        self.current_pixel_num = (r << 24) + (g << 16) + (b << 8) + a
        print(self.current_pixel_num)

    @staticmethod
    def __pixel_num_to_bytes(pixel_num: int) -> bytes:
        return bytes(
            (
                pixel_num >> 24 & 0xFF,
                pixel_num >> 16 & 0xFF,
                pixel_num >> 8 & 0xFF,
                pixel_num & 0xFF,
            )
        )

    @staticmethod
    def __pixels_to_bytes(pixels: list[tuple[int, int, int, int]]) -> bytes:
        pixel_bytes = bytes(chain.from_iterable(pixels))
        expected_size = len(pixels) * 4
        if len(pixel_bytes) != expected_size:
            raise ValueError("All pixels must be RGBA tuples with 4 bytes.")
        return pixel_bytes

    def fill_pixel(self, pixels: list[tuple[int, int, int, int]]):
        fill_size = len(pixels)
        if fill_size == 0:
            return

        required_pixel_num = self.current_pixel_num + fill_size
        image_bytes = bytearray(self.image.tobytes())

        if required_pixel_num > self.max_pixel_num:
            new_side_length = ceil(sqrt(required_pixel_num))
            new_max_pixel_num = new_side_length**2
            image_bytes.extend(b"\x00" * ((new_max_pixel_num - self.max_pixel_num) * 4))
            self.side_length = new_side_length
            self.max_pixel_num = new_max_pixel_num

        start = self.current_pixel_num * 4
        end = start + fill_size * 4
        image_bytes[start:end] = self.__pixels_to_bytes(pixels)
        self.current_pixel_num = required_pixel_num
        image_bytes[:4] = self.__pixel_num_to_bytes(self.current_pixel_num)
        self.image = Image.frombytes(
            "RGBA", (self.side_length, self.side_length), bytes(image_bytes)
        )
        self.save()

    def save(self):
        self.image.save(self.filename)

    def __str__(self):
        image_bytes = self.image.tobytes()
        rows = []
        for y in range(self.side_length):
            row_start = y * self.side_length * 4
            row_end = row_start + self.side_length * 4
            rows.append(
                "".join(
                    str(tuple(image_bytes[i : i + 4]))
                    for i in range(row_start, row_end, 4)
                )
            )
        return "\n".join(rows) + "\n"


class Undertaker:
    def __init__(self, remains: list[tuple], left_bytes_num: int = 4):
        self.__left_bytes_num = left_bytes_num
        self.__remains = remains
        self.__dir_list = []

    def add_dir(self, *dirs: str):
        self.__dir_list.extend(dirs)

    def execute(self):
        if not self.__dir_list:
            print("No directory to bury. Please add some first.")
            return
        for directory in self.__dir_list:
            self.bury(directory)

    def bury(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"{filepath} dose not exist.")
        if not os.path.isdir(filepath):
            self.eat_from_file(filepath)
            try:
                os.remove(filepath)
            except PermissionError:
                try:
                    # 1. 清除只读属性（Windows 专用）
                    ctypes.windll.kernel32.SetFileAttributesW(
                        filepath, 0x00000080
                    )  # FILE_ATTRIBUTE_NORMAL
                    os.remove(filepath)
                    print(f"✅ Forced deleted: {filepath}")
                except Exception as e:
                    print(f"❌ Failed to force delete {filepath}: {str(e)}")
            except Exception as e:
                print(f"❌ Failed to delete {filepath}: {str(e)}")
            return

        files_to_delete = []
        dirs_to_delete = []
        # 自底向上遍历目录树（先处理子目录，再处理父目录）
        for root, dirs, files in os.walk(filepath, topdown=False):
            for file_ in files:
                target_file = os.path.join(root, file_)
                self.eat_from_file(target_file)
                files_to_delete.append(target_file)
            self.eat_from_str(root)
            dirs_to_delete.append(root)
        print(files_to_delete)
        print(dirs_to_delete)
        # 删除文件和目录
        for file_ in files_to_delete:
            try:
                os.remove(file_)
            except PermissionError:
                try:
                    # 1. 清除只读属性（Windows 专用）
                    ctypes.windll.kernel32.SetFileAttributesW(
                        file_, 0x00000080
                    )  # FILE_ATTRIBUTE_NORMAL
                    os.remove(file_)
                    print(f"Forced deleted: {file_}")
                except Exception as e:
                    print(f"Failed to force delete {file_}: {str(e)}")
            except Exception as e:
                print(f"Failed to delete {file_}: {str(e)}")
        for directory in dirs_to_delete:
            os.rmdir(directory)

    def eat_from_str(self, data: str) -> None:
        bytelist = data.encode("utf-8")
        after_choices = choices(bytelist, k=self.__left_bytes_num)
        self.__remains.append(tuple(after_choices))

    def eat_from_file(self, filename: str) -> None:
        filesize = os.path.getsize(filename)
        if filesize <= 5:
            with open(filename, "rb") as f:
                self.eat_from_str(f.read().decode("utf-8") + filename)
        else:
            byte_pos = choices(range(filesize), k=self.__left_bytes_num)
            byte_pos.sort()
            byte_list = []
            with open(filename, "rb") as f:
                for pos in byte_pos:
                    f.seek(pos)
                    byte_list.append(int.from_bytes(f.read(1)))
            self.__remains.append(tuple(byte_list))


if __name__ == "__main__":
    tomb = ImageTomb("image.png")
    pixels = []
    undertaker = Undertaker(pixels, 4)
    undertaker.add_dir(*sys.argv[1:])
    undertaker.execute()
    print(pixels)
    tomb.fill_pixel(pixels)
    tomb.save()
    print(tomb)
