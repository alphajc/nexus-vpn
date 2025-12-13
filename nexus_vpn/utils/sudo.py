"""sudo 辅助模块 - 在需要时自动添加 sudo"""
import os
import subprocess
import shutil


def need_sudo():
    """检查当前用户是否需要 sudo"""
    return os.geteuid() != 0


def sudo_run(cmd, **kwargs):
    """执行命令，如果需要 sudo 则自动添加
    
    Args:
        cmd: 命令列表，如 ["systemctl", "restart", "nginx"]
        **kwargs: 传递给 subprocess.run 的其他参数
    
    Returns:
        subprocess.CompletedProcess
    """
    if need_sudo() and shutil.which("sudo"):
        cmd = ["sudo"] + list(cmd)
    return subprocess.run(cmd, **kwargs)


def sudo_check_output(cmd, **kwargs):
    """执行命令并获取输出，如果需要 sudo 则自动添加
    
    Args:
        cmd: 命令列表
        **kwargs: 传递给 subprocess.check_output 的其他参数
    
    Returns:
        bytes: 命令输出
    """
    if need_sudo() and shutil.which("sudo"):
        cmd = ["sudo"] + list(cmd)
    return subprocess.check_output(cmd, **kwargs)


def sudo_write_file(path, content, mode='w'):
    """写入文件，如果需要 sudo 则使用 tee
    
    Args:
        path: 文件路径
        content: 文件内容
        mode: 'w' 覆盖写入, 'a' 追加写入
    """
    if need_sudo() and shutil.which("sudo"):
        # 使用 sudo tee 写入
        tee_args = ["sudo", "tee"]
        if mode == 'a':
            tee_args.append("-a")
        tee_args.append(path)
        
        proc = subprocess.run(
            tee_args,
            input=content.encode() if isinstance(content, str) else content,
            stdout=subprocess.DEVNULL,
            check=True
        )
    else:
        with open(path, mode) as f:
            f.write(content)


def sudo_read_file(path):
    """读取文件，如果需要 sudo 则使用 sudo cat
    
    Args:
        path: 文件路径
    
    Returns:
        str: 文件内容
    """
    if need_sudo() and shutil.which("sudo"):
        result = subprocess.run(
            ["sudo", "cat", path],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    else:
        with open(path, 'r') as f:
            return f.read()


def sudo_makedirs(path, mode=0o755):
    """创建目录，如果需要 sudo 则使用 sudo mkdir"""
    if os.path.exists(path):
        return
    if need_sudo() and shutil.which("sudo"):
        subprocess.run(["sudo", "mkdir", "-p", path], check=True)
        subprocess.run(["sudo", "chmod", oct(mode)[2:], path], check=True)
    else:
        os.makedirs(path, mode=mode, exist_ok=True)


def sudo_chmod(path, mode):
    """修改文件权限"""
    if need_sudo() and shutil.which("sudo"):
        subprocess.run(["sudo", "chmod", oct(mode)[2:], path], check=True)
    else:
        os.chmod(path, mode)


def sudo_move(src, dst):
    """移动文件"""
    if need_sudo() and shutil.which("sudo"):
        subprocess.run(["sudo", "mv", src, dst], check=True)
    else:
        shutil.move(src, dst)


def sudo_remove(path):
    """删除文件或目录"""
    if not os.path.exists(path):
        return
    if need_sudo() and shutil.which("sudo"):
        subprocess.run(["sudo", "rm", "-rf", path], stderr=subprocess.DEVNULL)
    else:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            os.remove(path)
