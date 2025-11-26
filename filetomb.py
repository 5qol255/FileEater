from PIL import Image
from math import sqrt, ceil
from random import choices
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

    def fill_pixel(self, pixels: list[tuple[int, int, int, int]]):
        # 需要填充的像素数量
        fill_size = len(pixels)
        # 判断是否需要扩充图片
        if self.current_pixel_num + fill_size > self.max_pixel_num:
            # 计算新图片边长
            new_side_length = ceil(sqrt(self.current_pixel_num + fill_size))
            # 创建新图片
            new_image = Image.new(
                "RGBA", (new_side_length, new_side_length), (0, 0, 0, 0)
            )
            # 复制旧图片数据到新图片
            for x in range(self.side_length):
                for y in range(self.side_length):
                    itor = x + y * self.side_length
                    xx = itor % new_side_length
                    yy = itor // new_side_length
                    pixel = self.image.getpixel((x, y))
                    new_image.putpixel((xx, yy), pixel)
                    print(x, y, xx, yy)
            # 更新相关参数
            self.image = new_image
            self.side_length = new_side_length
            self.max_pixel_num = new_side_length**2

        for i in range(fill_size):
            x = (i + self.current_pixel_num) % self.side_length
            y = (i + self.current_pixel_num) // self.side_length
            self.image.putpixel((x, y), pixels[i])
            print(x, y)
        self.current_pixel_num += fill_size
        self.image.putpixel(
            (0, 0),
            (
                self.current_pixel_num >> 24 & 0xFF,
                self.current_pixel_num >> 16 & 0xFF,
                self.current_pixel_num >> 8 & 0xFF,
                self.current_pixel_num >> 0 & 0xFF,
            ),
        )
        self.save()

    def save(self):
        self.image.save(self.filename)

    def __str__(self):
        dest = ""
        for i in range(self.side_length):
            for j in range(self.side_length):
                dest += str(self.image.getpixel((j, i)))
            dest += "\n"
        return dest


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
                    print(f"✅ Forced deleted: {file_}")
                except Exception as e:
                    print(f"❌ Failed to force delete {file_}: {str(e)}")
            except Exception as e:
                print(f"❌ Failed to delete {file_}: {str(e)}")
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
