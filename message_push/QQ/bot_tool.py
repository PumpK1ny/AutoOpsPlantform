import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIO_DIR = os.path.join(BASE_DIR, "bio")

os.makedirs(BIO_DIR, exist_ok=True)


def bio_update(message: str, user_openid: str):
    """
    更新用户记忆
    
    Args:
        message: 记忆内容
        user_openid: 用户openid
    
    Returns:
        dict: {"success": True, "key": "000003"}
    """
    try:
        file_path = os.path.join(BIO_DIR, f"{user_openid}.json")
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                memories = json.load(f)
        else:
            memories = {}
        
        if memories:
            last_key = max(memories.keys())
            next_num = int(last_key) + 1
            next_key = f"{next_num:06d}"
        else:
            next_key = "000001"
        
        memories[next_key] = message
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(memories, f, ensure_ascii=False, indent=2)
        
        return {"success": True}
    except:
        return {"success": False}
def bio_delete(user_openid: str, key: str):
    """
    删除用户记忆并重新排序
    
    Args:
        user_openid: 用户openid
        key: 记忆key
    
    Returns:
        dict: {"success": True}
    """
    try:
        file_path = os.path.join(BIO_DIR, f"{user_openid}.json")
        
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                memories = json.load(f)
        else:
            return {"success": False}
        
        if key in memories:
            del memories[key]
            
            # 重新排序
            sorted_keys = sorted(memories.keys())
            new_memories = {}
            for i, old_key in enumerate(sorted_keys):
                new_key = f"{i + 1:06d}"
                new_memories[new_key] = memories[old_key]
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(new_memories, f, ensure_ascii=False, indent=2)
        else:
            return {"success": False}
        
        return {"success": True}
    except:
        return {"success": False}