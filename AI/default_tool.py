import os
import subprocess
import shlex


def write_file(file_path, content):
    """
    写入文件内容
    :param file_path: 文件路径
    :param content: 要写入的内容
    :return: 执行结果
    """
    try:
        # 确保目录存在
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "status": "success",
            "message": f"文件写入成功：{file_path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"文件写入失败：{str(e)}"
        }
def read_file(file_path, start_line=None, end_line=None):
    """
    读取文件内容，支持指定行范围
    :param file_path: 文件路径
    :param start_line: 起始行号（可选，默认从第1行开始）
    :param end_line: 结束行号（可选，默认到文件末尾）
    :return: 执行结果
    """
    try:
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"文件不存在：{file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # 处理行号参数
        if start_line is None:
            start_line = 1
        
        if end_line is None:
            end_line = total_lines
        
        # 转换为基于0的索引
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line)
        
        # 获取指定范围的内容
        content = ''.join(lines[start_idx:end_idx])
        
        return {
            "status": "success",
            "message": f"文件读取成功：{file_path}",
            "content": content,
            "total_lines": total_lines,
            "start_line": start_line,
            "end_line": end_line
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"文件读取失败：{str(e)}"
        }
def update_file(file_path, content, start_line, end_line=None):
    """
    更新文件内容，根据行范围参数来更新
    :param file_path: 文件路径
    :param content: 要更新的内容
    :param start_line: 起始行号
    :param end_line: 结束行号（可选，默认只更新start_line一行）
    :return: 执行结果
    """
    try:
        if not os.path.exists(file_path):
            return {
                "status": "error",
                "message": f"文件不存在：{file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # 处理行号参数
        if end_line is None:
            end_line = start_line
        
        # 转换为基于0的索引
        start_idx = max(0, start_line - 1)
        end_idx = min(total_lines, end_line)
        
        # 更新指定范围的内容
        new_lines = content.splitlines(keepends=True)
        # 确保最后一行有换行符，除非它是空行
        if new_lines and not new_lines[-1].endswith(('\n', '\r\n')):
            new_lines[-1] += '\n'
        lines[start_idx:end_idx] = new_lines
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return {
            "status": "success",
            "message": f"文件更新成功：{file_path}",
            "updated_lines": f"{start_line}-{end_line}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"文件更新失败：{str(e)}"
        }
def list_files(dir_path='.'):
    """
    查看目录下的文件
    :param dir_path: 目录路径（可选，默认当前目录）
    :return: 执行结果
    """
    try:
        if not os.path.exists(dir_path):
            return {
                "status": "error",
                "message": f"目录不存在：{dir_path}"
            }
        
        if not os.path.isdir(dir_path):
            return {
                "status": "error",
                "message": f"路径不是目录：{dir_path}"
            }
        
        # 获取目录下的所有文件和子目录
        entries = os.listdir(dir_path)
        
        # 分类文件和目录
        files = []
        dirs = []
        for entry in entries:
            entry_path = os.path.join(dir_path, entry)
            if os.path.isfile(entry_path):
                files.append(entry)
            elif os.path.isdir(entry_path):
                dirs.append(entry)
        
        return {
            "status": "success",
            "message": f"目录读取成功：{dir_path}",
            "directories": dirs,
            "files": files,
            "total_entries": len(entries),
            "total_files": len(files),
            "total_directories": len(dirs)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"目录读取失败：{str(e)}"
        }
def run_command(command, timeout=60, cwd=None):
    """
    安全地运行命令
    :param command: 要执行的命令
    :param timeout: 超时时间（秒），默认60秒
    :param cwd: 工作目录（可选）
    :return: 执行结果
    """
    try:
        # 危险命令黑名单
        dangerous_commands = [
            'rm -rf /',
            'rm -rf ~',
            'mkfs',
            'dd if=',
            ':(){:|:}&:;',
            'format',
            'fdisk',
            'shutdown',
            'reboot',
            'halt',
            'poweroff',
            'del /f /q',
            'del /s /q',
            'rmdir /s /q'
        ]
        
        # 检查是否包含危险命令
        command_lower = command.lower()
        for dangerous in dangerous_commands:
            if dangerous in command_lower:
                return {
                    "status": "error",
                    "message": f"拒绝执行危险命令：{dangerous}"
                }
        
        # 检查是否包含管道和重定向到敏感路径
        sensitive_paths = ['/etc/passwd', '/etc/shadow', 'C:\\Windows\\System32', 'C:\\Windows']
        for path in sensitive_paths:
            if path in command:
                return {
                    "status": "error",
                    "message": f"拒绝访问敏感路径：{path}"
                }
        
        # 使用subprocess安全执行命令
        # 在Windows上使用shell=True，在Unix上使用shell=False
        use_shell = os.name == 'nt'
        
        # 设置工作目录
        if cwd is None:
            cwd = os.getcwd()
        
        # 执行命令
        result = subprocess.run(
            command,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            encoding='utf-8',
            errors='replace'
        )
        
        return {
            "status": "success",
            "message": f"命令执行成功",
            "command": command,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timeout": timeout,
            "cwd": cwd
        }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": f"命令执行超时（{timeout}秒）",
            "command": command,
            "timeout": timeout
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"命令执行失败：{str(e)}",
            "command": command
        }

class Todo:
    def __init__(self):
        self.todos={}
        self._is_running=False
    def _log(self,finish=False):
        if finish: # 当最后结束时，检查所有任务是否完成，如果还有任务没有标记为done，则执行后面的for循环
            if not all(i == "done" for i in self.todos.values()):
                pass
            else:
                return "success"

        for todo in self.todos:
            if self.todos[todo] == "wait":
                print(f"⚪️ {todo}")
            elif self.todos[todo] == "doing":
                print(f"🚶 {todo}")
            elif self.todos[todo] == "done":
                print(f"✔ {todo}")
    
    def create(self,task_list):
        try:
            for task in task_list:
                self.todos[task] = "wait"
            self._is_running=True # 有任务在运行
            self._log()
        except Exception as e:
            print(f"创建任务失败：{str(e)}")
        return self.todos
    
    def update(self,task):
        try:
            if task in self.todos:
                self.todos[task] = "done"
                self._log()
        except Exception as e:
            print(f"更新任务失败：{str(e)}")
        return self.todos
    
    def finish(self):
        try:
            for task in self.todos:
                self.todos[task] = "done"
            self._log(True)
            self._is_running=False # 任务完成
            return "success"
        except Exception as e:
            print(f"完成任务失败：{str(e)}")
        return self.todos
    def is_running(self):
        if all(i == "done" for i in self.todos.values()):
            return False
        else:
            return self._is_running


if __name__ == "__main__":
    print(read_file("example.txt"))
