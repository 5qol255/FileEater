import os  # For file and directory operations
import sys  # For system-specific parameters and functions
import stat  # For file status and permission handling
import ctypes  # For Windows API calls
import shutil  # For deleting file operations
import random  # For random byte selection
import subprocess  # For executing system commands
from typing import Tuple, Callable, Any  # For type hinting


class FileEater:
    def __init__(self):
        pass

    def extract_data(self, text_or_path: str, num_bytes=32) -> bytearray:
        """
        随机获取字符串或文件的若干个字节
        """
        # 准备字节数组
        byte_list = bytearray()
        # 如果不是有效路径或者不是文件，则视为字符串
        if not os.path.exists(text_or_path) or not os.path.isfile(text_or_path):
            # 将字符串编码为字节序列（必须步骤）
            byte_data = text_or_path.encode("utf-8")
            # 使用random.choices从字节序列中随机选择的字节并添加到列表中
            byte_list.extend(random.choices(byte_data, k=num_bytes))
        else:
            # 准备随机字节列表
            pos_list = []
            for _ in range(num_bytes):
                pos_list.append(random.randint(0, os.path.getsize(text_or_path) - 1))
            pos_list.sort()
            # 读取文件内容
            with open(text_or_path, "rb") as f:
                for pos in pos_list:
                    # 定位到指定位置并读取一个字节
                    f.seek(pos)
                    byte_list += f.read(1)
        # 返回字节数组
        return byte_list

    def eat_file(self, path: str) -> Tuple[bool, bytearray | None]:
        """
        删除文件（支持长路径），将其转化为一些数据
        """
        # 准备字节数组
        remaining_data = bytearray()
        # 收集数据
        remaining_data += self.extract_data(path)
        # Windows需要移除只读属性
        if os.name == "nt":
            try:
                # 移除只读属性
                os.chmod(path, stat.S_IWRITE)
            except Exception as err:
                print(f"{os.name} - 移除只读属性失败: {path}\n{err}", file=sys.stderr)
                # 如果常规方法失败，尝试强制解除只读属性
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(path, 0)
                except Exception as err:
                    print(f"{os.name} - 解除只读失败: {path}\n{err}", file=sys.stderr)
        # 尝试删除文件
        try:
            os.remove(path)
        except Exception as err:
            print(f"{os.name} - 删除文件失败: {path}\n{err}", file=sys.stderr)
            # 尝试执行系统调用删除
            try:
                if os.name == "nt":
                    subprocess.run(
                        ["cmd", "/c", "del", "/f", "/q", "/a", path],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                else:
                    subprocess.run(
                        ["rm", "-f", path],
                        capture_output=True,
                        text=True,
                        check=True,
                    )
            except Exception as err:
                print(f"{os.name} - 系统调用删除失败: {path}\n{err}", file=sys.stderr)
                return False, None
            else:
                return True, remaining_data
        else:
            return True, remaining_data

            # 设置回调函数

    def __on_rm_error(
        self,
        func: Callable[[str], None],
        path: str,
        exc_info: Tuple[Any, BaseException, Any],
    ) -> None:
        """
        删除文件夹时的错误处理函数
        """
        # 尝试系统调用删除
        try:
            if os.name == "nt":
                subprocess.run(
                    ["cmd", "/c", "rd", "/s", "/q", path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
            else:
                subprocess.run(
                    ["rm", "-rf", path],
                    capture_output=True,
                    text=True,
                    check=True,
                )
        except Exception as err:
            print(f"{os.name} - 删除失败: {path}\n{exc_info}\n{err}", file=sys.stderr)

    def eat_folder(self, path: str) -> Tuple[bool, bytearray | None]:
        """
        递归删除文件夹（支持长路径），将其转化为一些数据
        """
        # 准备字节数组
        remaining_data = bytearray()
        # 收集数据
        for root, dirs, files in os.walk(path):
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    remaining_data += self.extract_data(file_path)
                except Exception as err:
                    print(
                        f"{os.name} - 获取文件数据失败: {file_path}\n{err}",
                        file=sys.stderr,
                    )
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                try:
                    remaining_data += self.extract_data(dir_path)
                except Exception as err:
                    print(
                        f"{os.name} - 获取文件夹数据失败: {dir_path}\n{err}",
                        file=sys.stderr,
                    )
        # 尝试使用shutil.rmtree删除
        try:
            shutil.rmtree(path, onerror=self.__on_rm_error)
        except Exception as err:
            print(f"{os.name} - 删除失败: {path}\n{err}", file=sys.stderr)
            return False, None
        else:
            return True, remaining_data


if __name__ == "__main__":
    # 隐藏控制台窗口（仅适用于Windows）
    if os.name == "nt":
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    # 获取拖放的文件/文件夹路径
    if len(sys.argv) > 1:
        file_eater = FileEater()
        for arg in sys.argv[1:]:
            if os.path.isfile(arg):
                result, data = file_eater.eat_file(sys.argv[1])
            else:
                result, data = file_eater.eat_folder(sys.argv[1])
            if result:
                with open("log.txt", "ab") as f:
                    f.write(data)
    # 如果没有参数，显示使用说明
    else:
        print("请将文件或文件夹拖放到此脚本上", file=sys.stderr)
        input("按回车键退出...")
