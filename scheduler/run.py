#!/usr/bin/env python3
"""
定时任务调度器入口

使用方法:
    python scheduler/run.py              # 启动调度器
    python scheduler/run.py --status     # 查看任务状态
    python scheduler/run.py --run task_1 # 立即运行指定任务
    python scheduler/run.py --reload     # 重新加载配置
"""

import argparse
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scheduler import TaskScheduler


def main():
    parser = argparse.ArgumentParser(description='定时任务调度器')
    parser.add_argument('--status', action='store_true', help='查看任务状态')
    parser.add_argument('--run', metavar='TASK_ID', help='立即运行指定任务')
    parser.add_argument('--reload', action='store_true', help='重新加载配置')
    parser.add_argument('--config', default='scheduler/config.json', help='配置文件路径')
    
    args = parser.parse_args()
    
    scheduler = TaskScheduler(config_path=args.config)
    
    if args.status:
        print("=" * 80)
        print("任务状态")
        print("=" * 80)
        status_list = scheduler.get_task_status()
        for s in status_list:
            print(f"\n任务ID: {s['id']}")
            print(f"  名称: {s['name']}")
            print(f"  启用: {'是' if s['enabled'] else '否'}")
            print(f"  运行中: {'是' if s['running'] else '否'}")
            print(f"  最后运行: {s['last_run'] or '从未'}")
            print(f"  最后状态: {s['last_status'] or '无'}")
            if s['last_output']:
                print(f"  最后输出: {s['last_output'][:200]}...")
        print("=" * 80)
        return
    
    if args.run:
        try:
            print(f"正在立即运行任务: {args.run}")
            scheduler.run_task_now(args.run)
            time.sleep(2)
            print("任务已启动")
        except ValueError as e:
            print(f"错误: {e}")
            sys.exit(1)
        return
    
    if args.reload:
        scheduler.reload_config()
        print("配置已重新加载")
        return
    
    # 默认启动调度器
    print("=" * 80)
    print("定时任务调度器")
    print("=" * 80)
    print(f"配置文件: {args.config}")
    print(f"任务数量: {len(scheduler.tasks)}")
    print("-" * 80)
    
    for task_id, runner in scheduler.tasks.items():
        task = runner.task
        schedule_info = task.schedule
        schedule_type = schedule_info.get('type', 'unknown')
        
        if schedule_type == 'cron':
            schedule_desc = f"cron: {schedule_info.get('expression')}"
        elif schedule_type == 'interval':
            schedule_desc = f"每 {schedule_info.get('minutes')} 分钟"
        elif schedule_type == 'daily':
            schedule_desc = f"每天 {schedule_info.get('time')}"
        else:
            schedule_desc = schedule_type
            
        status = "启用" if task.enabled else "禁用"
        print(f"  [{status}] {task.name} ({task.id}) - {schedule_desc}")
    
    print("=" * 80)
    print("按 Ctrl+C 停止调度器")
    print()
    
    try:
        scheduler.start()
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n正在停止调度器...")
        scheduler.stop()
        print("调度器已停止")


if __name__ == "__main__":
    main()
