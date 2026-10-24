import json
import argparse
import os
from datetime import datetime

def load_and_build_threads(file_path, as_of_date_str):
    print("👉 开始逐行读取 voices.jsonl 文件...")
    as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d")
    
    valid_messages = []
    message_map = {}
    
    line_count = 0
    success_count = 0
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line_count += 1
            if line_count % 5000 == 0:
                print(f"   已扫描 {line_count} 行...")
            
            try:
                data = json.loads(line.strip())
            except Exception:
                continue  # 忽略任何解析出错的行
                
            created_at_str = data.get("created_at")
            if not created_at_str:
                continue
                
            try:
                msg_date_str = created_at_str.split("T")[0]
                msg_date = datetime.strptime(msg_date_str, "%Y-%m-%d")
            except Exception:
                continue
            
            if msg_date <= as_of_date:
                valid_messages.append(data)
                msg_id = data.get("id")
                if msg_id:
                    message_map[msg_id] = data
                success_count += 1

    print(f"👉 读取完毕！共扫描 {line_count} 行，成功加载有效消息 {len(valid_messages)} 条。")
    
    parent_stats = {}
    for msg in valid_messages:
        parent_id = msg.get("parent_id")
        if parent_id and parent_id in message_map:
            parent_msg = message_map[parent_id]
            if parent_id not in parent_stats:
                parent_stats[parent_id] = {
                    "parent_content": parent_msg.get("content"),
                    "first_seen": parent_msg.get("created_at").split("T")[0],
                    "channels": set([parent_msg.get("channel")]),
                    "reply_count": 0,
                    "voice_ids": [parent_id]
                }
            parent_stats[parent_id]["reply_count"] += 1
            parent_stats[parent_id]["channels"].add(msg.get("channel"))
            parent_stats[parent_id]["voice_ids"].append(msg.get("id"))

    print(f"👉 上下文关联完成！共找到 {len(parent_stats)} 个活跃讨论串。")
    return valid_messages, parent_stats

def generate_local_trends(parent_stats, as_of_date_str):
    as_of_date = datetime.strptime(as_of_date_str, "%Y-%m-%d")
    sorted_threads = sorted(parent_stats.items(), key=lambda x: x[1]["reply_count"], reverse=True)
    
    trends = []
    for parent_id, stats in sorted_threads[:8]:
        content = stats["parent_content"] or "玩家讨论"
        
        category = "General discussion"
        if any(w in content for w in ["肝", "体力", "每日", "累", "钓鱼", "周常"]):
            category = "Daily grind & chores"
        elif any(w in content for w in ["抽", "保底", "歪", "金", "氪金", "概率", "非酋"]):
            category = "Gacha economy"
        elif any(w in content for w in ["削弱", "加强", "数值", "平衡", "角色"]):
            category = "Character balance"

        try:
            first_seen_date = datetime.strptime(stats["first_seen"], "%Y-%m-%d")
            days_diff = (as_of_date - first_seen_date).days
        except:
            days_diff = 0
        
        if stats["reply_count"] > 10 and len(stats["channels"]) > 1:
            status = "growing"
        elif days_diff <= 2:
            status = "new"
        else:
            status = "one-off"

        title = content[:20] + "..." if len(content) > 20 else content
        
        trend_item = {
            "title": f"关于「{title}」的讨论",
            "title_en": f"Discussion regarding player feedback",
            "category": category,
            "status": status,
            "first_seen": stats["first_seen"],
            "voice_ids": stats["voice_ids"][:3],
            "why": f"Observed across {len(stats['channels'])} channels with {stats['reply_count']} interactions, showing a {status} pattern."
        }
        trends.append(trend_item)
        
    return {
        "as_of": as_of_date_str,
        "trends": trends
    }

import argparse

if __name__ == "__main__":
    print("🚀 启动趋势猎人分析程序...")
    
    # 1. 使用 input() 在运行时动态让用户输入截止日期
    input_file = "voices.jsonl"
    as_of_date = input("请输入截止日期 (格式如 2026-07-24): ").strip()
    out_file = "trends.json"
    
    if not as_of_date:
        as_of_date = "2026-07-24"  # 如果直接回车，默认一个日期
        print(f"未输入日期，使用默认截止日期: {as_of_date}")

    print(f"👉 正在处理截至 {as_of_date} 之前的数据...")
    
    # 2. 运行核心过滤与上下文关联
    messages, parent_stats = load_and_build_threads(input_file, as_of_date)

    if not parent_stats:
        print("❌ 警告：未找到有效讨论串！")
    else:
        # 3. 运行本地规则提取趋势
        trend_result = generate_local_trends(parent_stats, as_of_date)
        
        # 4. 写入文件
        out_path = os.path.abspath(out_file)
        with open(out_path, "w", encoding="utf-8") as f_out:
            json.dump(trend_result, f_out, ensure_ascii=False, indent=2)
            
        print(f"🎉 成功！trends.json 已生成到: {out_path}")