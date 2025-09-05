import os
import sys
import ctypes
import stat
import shutil
import hashlib


def get_string_md5(text):
    """
    计算字符串的 MD5 哈希值

    参数:
        text: 要计算 MD5 的字符串

    返回:
        32 位十六进制 MD5 哈希值
    """
    # 将字符串编码为字节序列（必须步骤）
    byte_data = text.encode("utf-8")

    # 创建 MD5 对象并更新数据
    md5_hash = hashlib.md5()
    md5_hash.update(byte_data)

    # 返回十六进制格式的哈希值
    return md5_hash.hexdigest()


def get_file_md5(file_path, chunk_size=8192, threshold=104857600):  # 默认阈值100MB
    """
    计算文件的 MD5 哈希值

    参数:
        file_path: 文件路径
        chunk_size: 分块读取的大小(字节)
        threshold: 使用分块读取的阈值(字节)，默认100MB以上的文件使用分块读取

    返回:
        文件的 MD5 哈希值(32位十六进制字符串)
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 检查是否为文件
    if not os.path.isfile(file_path):
        raise ValueError(f"路径不是文件: {file_path}")

    file_size = os.path.getsize(file_path)

    # 根据文件大小选择读取方式
    if file_size > threshold:
        # 大文件使用分块读取
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    else:
        # 小文件一次性读取
        with open(file_path, "rb") as f:
            file_data = f.read()
            return hashlib.md5(file_data).hexdigest()


def force_delete(path):
    """强制删除文件或文件夹（支持长路径），将其转化为一些数据"""
    remaining_data = ""

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
            remaining_data += get_file_md5(path)
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
                        remaining_data += get_file_md5(file_path)
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    except Exception:
                        # 如果常规删除失败，尝试强制解除占用
                        try:
                            ctypes.windll.kernel32.SetFileAttributesW(file_path, 0)
                            remaining_data += get_file_md5(file_path)
                            os.remove(file_path)
                        except Exception:
                            pass

                for name in dirs:
                    dir_path = os.path.join(root, name)
                    try:
                        remaining_data += get_string_md5(dir_path)
                        os.rmdir(dir_path)
                    except Exception:
                        # 如果常规删除失败，尝试强制解除占用
                        try:
                            ctypes.windll.kernel32.SetFileAttributesW(
                                dir_path, 0x80
                            )  # FILE_ATTRIBUTE_NORMAL
                            remaining_data += get_string_md5(dir_path)
                            os.rmdir(dir_path)
                        except Exception:
                            pass

            # 删除主文件夹
            try:
                remaining_data += get_string_md5(path)
                os.rmdir(path)
            except Exception:
                try:
                    ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)
                    remaining_data += get_string_md5(path)
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
        with open("log.txt", "a") as log_file:
            if result[0]:
                log_file.write(result[1])
    else:
        # 如果没有参数，显示使用说明
        print("请将文件或文件夹拖放到此脚本上", file=sys.stderr)
        input("按回车键退出...")
