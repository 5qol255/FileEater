import os
import sys
import ctypes
import stat
import shutil
import hashlib
import random


def get_random_bytes(text, num_bytes=32):
    """
    随机获取字符串的若干个字节
    """
    # 判断输入是否为有效文件路径
    if not os.path.exists(text) or not os.path.isfile(text):
        # 将字符串编码为字节序列（必须步骤）
        byte_data = text.encode("utf-8")
        # 使用random.choices从字节序列中随机选择指定数量的字节
        byte_list = random.choices(byte_data, k=num_bytes)
        # 返回字节数组
        return bytearray(byte_list)
    else:
        # 准备随机字节列表
        pos_list = []
        for _ in range(num_bytes):
            pos_list.append(random.randint(0, os.path.getsize(text) - 1))
        pos_list.sort()
        # 准备字节数组
        byte_list = bytearray()
        # 读取文件内容
        with open(text, "rb") as f:
            for pos in pos_list:
                f.seek(pos)
                byte_list += f.read(1)
        # 返回字节数组
        return byte_list


def force_delete(path):
    """
    强制删除文件或文件夹（支持长路径），将其转化为一些数据
    """
    remaining_data = bytearray()

    # 转换为长路径格式（支持特殊字符和超长路径）
    if not path.startswith("\\\\?\\"):
        if path.startswith("\\\\"):
            # UNC网络路径格式
            path = "\\\\?\\UNC\\" + path[2:]
        else:
            # 本地路径格式
            path = "\\\\?\\" + os.path.abspath(path)

    try:
        # 如果是文件
        if os.path.isfile(path):
            remaining_data += get_random_bytes(path)
            # 移除只读属性
            os.chmod(path, stat.S_IWRITE)
            os.remove(path)
            return True, remaining_data

        # 如果是文件夹
        if os.path.isdir(path):
            # 递归删除文件夹内容
            for root, dirs, files in os.walk(path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        remaining_data += get_random_bytes(file_path)
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    except Exception:
                        # 如果常规删除失败，尝试强制解除占用
                        try:
                            ctypes.windll.kernel32.SetFileAttributesW(file_path, 0)
                            remaining_data += get_random_bytes(file_path)
                            os.remove(file_path)
                        except Exception:
                            pass

                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        remaining_data += get_random_bytes(dir_path)
                        os.rmdir(dir_path)
                    except Exception:
                        # 如果常规删除失败，尝试强制解除占用
                        try:
                            ctypes.windll.kernel32.SetFileAttributesW(
                                dir_path, 0x80
                            )  # FILE_ATTRIBUTE_NORMAL
                            remaining_data += get_random_bytes(dir_path)
                            os.rmdir(dir_path)
                        except Exception:
                            pass

            # 删除主文件夹
            try:
                remaining_data += get_random_bytes(path)
                os.rmdir(path)
            except Exception:
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)
                    remaining_data += get_random_bytes(path)
                    os.rmdir(path)
                except Exception:
                    shutil.rmtree(path, ignore_errors=True)
            return True, remaining_data

    except Exception as e:
        print(f"删除失败: {e}", file=sys.stderr)
        return False, None

    return False, None


if __name__ == "__main__":
    # 隐藏控制台窗口（仅适用于Windows）
    if os.name == "nt":
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    # 获取拖放的文件/文件夹路径
    if len(sys.argv) > 1:
        target = sys.argv[1]
        result = force_delete(target)
        with open("log.txt", "ab") as log_file:
            if result[0]:
                log_file.write(result[1])
    else:
        # 如果没有参数，显示使用说明
        print("请将文件或文件夹拖放到此脚本上", file=sys.stderr)
        input("按回车键退出...")
