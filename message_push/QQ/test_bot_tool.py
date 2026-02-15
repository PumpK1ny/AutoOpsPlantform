import os
import json
import tempfile
import shutil
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from message_push.QQ.bot_tool import bio_update, bio_delete


class TestBotTool(unittest.TestCase):
    """测试 bot_tool.py 中的记忆管理功能"""
    
    def setUp(self):
        """每个测试前创建临时目录"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_bio_dir = None
        
        import message_push.QQ.bot_tool as bot_tool_module
        self.original_bio_dir = bot_tool_module.BIO_DIR
        bot_tool_module.BIO_DIR = self.temp_dir
    
    def tearDown(self):
        """每个测试后清理临时目录"""
        import message_push.QQ.bot_tool as bot_tool_module
        bot_tool_module.BIO_DIR = self.original_bio_dir
        shutil.rmtree(self.temp_dir)
    
    def test_bio_update_new_user(self):
        """测试新用户添加记忆"""
        result = bio_update("测试记忆内容", "test_user_001")
        
        self.assertTrue(result["success"])
        
        file_path = os.path.join(self.temp_dir, "test_user_001.json")
        self.assertTrue(os.path.exists(file_path))
        
        with open(file_path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        self.assertEqual(memories["000001"], "测试记忆内容")
    
    def test_bio_update_existing_user(self):
        """测试已有用户添加新记忆"""
        bio_update("第一条记忆", "test_user_002")
        result = bio_update("第二条记忆", "test_user_002")
        
        self.assertTrue(result["success"])
        
        file_path = os.path.join(self.temp_dir, "test_user_002.json")
        with open(file_path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        self.assertEqual(len(memories), 2)
        self.assertEqual(memories["000001"], "第一条记忆")
        self.assertEqual(memories["000002"], "第二条记忆")
    
    def test_bio_delete(self):
        """测试删除记忆"""
        bio_update("记忆1", "test_user_003")
        bio_update("记忆2", "test_user_003")
        bio_update("记忆3", "test_user_003")
        
        result = bio_delete("test_user_003", "000002")
        self.assertTrue(result["success"])
        
        file_path = os.path.join(self.temp_dir, "test_user_003.json")
        with open(file_path, "r", encoding="utf-8") as f:
            memories = json.load(f)
        
        self.assertEqual(len(memories), 2)
        self.assertEqual(memories["000001"], "记忆1")
        self.assertEqual(memories["000002"], "记忆3")
    
    def test_bio_delete_nonexistent_key(self):
        """测试删除不存在的记忆key"""
        bio_update("记忆1", "test_user_004")
        result = bio_delete("test_user_004", "000999")
        
        self.assertFalse(result["success"])


if __name__ == "__main__":
    unittest.main()
