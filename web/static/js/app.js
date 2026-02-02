// 全局状态
let currentFolder = null;
let currentFile = null;
let fileData = {};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initApp();
});

async function initApp() {
    // 初始化文件夹点击事件
    document.querySelectorAll('.folder-item').forEach(item => {
        item.addEventListener('click', function() {
            const folder = this.dataset.folder;
            selectFolder(folder);
        });
    });

    // 预先加载所有文件夹的文件计数
    await loadAllFolderCounts();

    // 默认选择第一个文件夹
    const firstFolder = document.querySelector('.folder-item');
    if (firstFolder) {
        const folderName = firstFolder.dataset.folder;
        await selectFolder(folderName);
    }
}

// 加载所有文件夹的文件计数
async function loadAllFolderCounts() {
    const folderItems = document.querySelectorAll('.folder-item');
    for (const item of folderItems) {
        const folderName = item.dataset.folder;
        try {
            const response = await fetch(`/api/files/${folderName}`);
            const files = await response.json();
            const countEl = document.getElementById(`count-${folderName}`);
            if (countEl) {
                countEl.textContent = files.length;
            }
        } catch (error) {
            console.error(`加载文件夹 ${folderName} 计数失败:`, error);
        }
    }
}

// 选择文件夹
async function selectFolder(folderName) {
    if (currentFolder === folderName) return;
    
    currentFolder = folderName;
    currentFile = null;
    
    // 更新UI状态
    document.querySelectorAll('.folder-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.folder === folderName) {
            item.classList.add('active');
        }
    });
    
    // 更新文件夹标题
    const folderItem = document.querySelector(`.folder-item[data-folder="${folderName}"]`);
    if (folderItem) {
        const folderNameEl = folderItem.querySelector('.folder-name').textContent;
        document.getElementById('currentFolderName').textContent = folderNameEl;
    }
    
    // 加载文件列表
    await loadFiles(folderName);
}

// 加载文件列表
async function loadFiles(folderName) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '<div class="loading"></div>';
    
    try {
        const response = await fetch(`/api/files/${folderName}`);
        const files = await response.json();
        
        fileData[folderName] = files;
        
        // 更新文件计数
        document.getElementById(`count-${folderName}`).textContent = files.length;
        document.getElementById('fileCount').textContent = `共 ${files.length} 个文件`;
        
        // 渲染文件列表
        if (files.length === 0) {
            fileList.innerHTML = `
                <div class="empty-state">
                    <p>📂 该文件夹暂无文件</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        files.forEach((file, index) => {
            html += `
                <div class="file-item" data-folder="${folderName}" data-file="${file.name}" onclick="selectFile('${folderName}', '${file.name}')">
                    <span class="file-icon">📄</span>
                    <div class="file-info">
                        <div class="file-date">${file.display_date}</div>
                        <div class="file-meta">${file.size}</div>
                    </div>
                </div>
            `;
        });
        fileList.innerHTML = html;
        
    } catch (error) {
        console.error('加载文件列表失败:', error);
        fileList.innerHTML = `
            <div class="empty-state">
                <p>❌ 加载失败</p>
            </div>
        `;
    }
}

// 选择文件
async function selectFile(folderName, fileName) {
    if (currentFolder === folderName && currentFile === fileName) return;
    
    currentFolder = folderName;
    currentFile = fileName;
    
    // 更新UI状态
    document.querySelectorAll('.file-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.folder === folderName && item.dataset.file === fileName) {
            item.classList.add('active');
        }
    });
    
    // 更新文件标题
    const fileInfo = fileData[folderName]?.find(f => f.name === fileName);
    if (fileInfo) {
        document.getElementById('currentFileName').textContent = `📄 ${fileInfo.display_date} - ${fileInfo.name}`;
    }
    
    // 加载文件内容
    await loadContent(folderName, fileName);
}

// 加载文件内容
async function loadContent(folderName, fileName) {
    const viewer = document.getElementById('contentViewer');
    viewer.innerHTML = '<div class="loading"></div>';
    
    try {
        const response = await fetch(`/api/content/${folderName}/${fileName}`);
        const data = await response.json();
        
        if (data.error) {
            viewer.innerHTML = `
                <div class="empty-state">
                    <p>❌ ${data.error}</p>
                </div>
            `;
            return;
        }
        
        // 渲染 Markdown 内容
        const html = renderMarkdown(data.content);
        viewer.innerHTML = `
            <div class="markdown-body">
                ${html}
            </div>
        `;
        
    } catch (error) {
        console.error('加载文件内容失败:', error);
        viewer.innerHTML = `
            <div class="empty-state">
                <p>❌ 加载失败</p>
            </div>
        `;
    }
}

// 渲染 Markdown
function renderMarkdown(content) {
    // 配置 marked
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                try {
                    return hljs.highlight(code, { language: lang }).value;
                } catch (err) {
                    console.error(err);
                }
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true
    });
    
    // 解析 Markdown
    const html = marked.parse(content);
    
    // 使用 DOMPurify 清理 HTML
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'hr',
            'strong', 'em', 'del', 'ins', 'code', 'pre',
            'ul', 'ol', 'li',
            'blockquote',
            'table', 'thead', 'tbody', 'tr', 'th', 'td',
            'a', 'img',
            'div', 'span'
        ],
        ALLOWED_ATTR: ['href', 'title', 'src', 'alt', 'class', 'style']
    });
}

// 刷新当前文件
async function refreshCurrentFile() {
    if (currentFolder && currentFile) {
        await loadContent(currentFolder, currentFile);
    }
}

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + R 刷新
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        refreshCurrentFile();
    }
    
    // 左右箭头切换文件
    if (currentFolder && fileData[currentFolder]) {
        const files = fileData[currentFolder];
        const currentIndex = files.findIndex(f => f.name === currentFile);
        
        if (e.key === 'ArrowRight' && currentIndex > 0) {
            selectFile(currentFolder, files[currentIndex - 1].name);
        } else if (e.key === 'ArrowLeft' && currentIndex < files.length - 1) {
            selectFile(currentFolder, files[currentIndex + 1].name);
        }
    }
});

// 全屏功能
let isFullscreen = false;

function toggleFullscreen() {
    const wrapper = document.getElementById('contentWrapper');
    
    if (!isFullscreen) {
        // 进入全屏
        if (wrapper.requestFullscreen) {
            wrapper.requestFullscreen();
        } else if (wrapper.webkitRequestFullscreen) {
            wrapper.webkitRequestFullscreen();
        } else if (wrapper.msRequestFullscreen) {
            wrapper.msRequestFullscreen();
        }
        wrapper.classList.add('fullscreen-mode');
        isFullscreen = true;
    } else {
        // 退出全屏
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        wrapper.classList.remove('fullscreen-mode');
        isFullscreen = false;
    }
}

// 监听全屏变化事件
document.addEventListener('fullscreenchange', function() {
    const wrapper = document.getElementById('contentWrapper');
    isFullscreen = !!document.fullscreenElement;
    if (!isFullscreen) {
        wrapper.classList.remove('fullscreen-mode');
    }
});

document.addEventListener('webkitfullscreenchange', function() {
    const wrapper = document.getElementById('contentWrapper');
    isFullscreen = !!document.webkitFullscreenElement;
    if (!isFullscreen) {
        wrapper.classList.remove('fullscreen-mode');
    }
});
