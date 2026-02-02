"""
数据分析结果展示 Web 应用
展示 data/result 下的 markdown 文件
"""

import os
import json
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory

app = Flask(__name__)

RESULT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "result")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")


def get_folders():
    """获取结果文件夹列表"""
    if not os.path.exists(RESULT_DIR):
        return []
    folders = []
    for item in os.listdir(RESULT_DIR):
        item_path = os.path.join(RESULT_DIR, item)
        if os.path.isdir(item_path):
            folders.append({
                "name": item,
                "display_name": get_folder_display_name(item)
            })
    return folders


def get_folder_display_name(folder_name):
    """获取文件夹显示名称"""
    names = {
        "final": "📊 最终结果",
        "fund_analysis": "💰 基金分析",
        "news": "📰 新闻资讯"
    }
    return names.get(folder_name, folder_name)


def get_files_by_folder(folder_name):
    """获取指定文件夹下的所有 md 文件"""
    folder_path = os.path.join(RESULT_DIR, folder_name)
    if not os.path.exists(folder_path):
        return []
    
    files = []
    for item in os.listdir(folder_path):
        if item.endswith(".md"):
            file_path = os.path.join(folder_path, item)
            stat = os.stat(file_path)
            date_str = item.replace(".md", "")
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = date.strftime("%Y年%m月%d日")
            except:
                formatted_date = date_str
            
            files.append({
                "name": item,
                "date": date_str,
                "display_date": formatted_date,
                "size": format_size(stat.st_size),
                "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    files.sort(key=lambda x: x["date"], reverse=True)
    return files


def format_size(size):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def read_markdown_content(folder_name, file_name):
    """读取 markdown 文件内容"""
    file_path = os.path.join(RESULT_DIR, folder_name, file_name)
    if not os.path.exists(file_path):
        return None
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/")
def index():
    """首页"""
    from datetime import datetime
    folders = get_folders()
    return render_template("index.html", folders=folders, result_dir=RESULT_DIR, now=datetime.now())


@app.route("/api/folders")
def api_folders():
    """获取文件夹列表 API"""
    return jsonify(get_folders())


@app.route("/api/files/<path:folder_name>")
def api_files(folder_name):
    """获取指定文件夹下的文件列表"""
    return jsonify(get_files_by_folder(folder_name))


@app.route("/api/content/<path:folder_name>/<file_name>")
def api_content(folder_name, file_name):
    """获取文件内容"""
    content = read_markdown_content(folder_name, file_name)
    if content is None:
        return jsonify({"error": "文件不存在"})
    return jsonify({
        "content": content,
        "folder": folder_name,
        "file": file_name
    })


@app.route("/static/<path:path>")
def serve_static(path):
    """静态文件服务"""
    return send_from_directory(STATIC_DIR, path)


@app.route("/themes")
def themes_preview():
    """配色方案预览页面"""
    return render_template("themes.html")


if __name__ == "__main__":
    print("=" * 50)
    print("  📊 数据分析结果展示系统")
    print("=" * 50)
    print(f"  结果目录: {RESULT_DIR}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
