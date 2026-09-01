import requests
import json
import os
import random
from datetime import datetime, timezone, timedelta

# 东京迪士尼海洋 API ID
TDS_ENTITY_ID = "67b290d5-3478-4f23-b601-2f8fb71ba803"
API_URL = f"https://api.themeparks.wiki/v1/entity/{TDS_ENTITY_ID}/live"
DATA_FILE = "tds_history.json"

# 中文映射表（前端只显示这些核心项目，你可以随时添加）
TDS_TRANSLATIONS = {
    "Soaring: Fantastic Flight": "翱翔：梦幻奇航",
    "Toy Story Mania!": "玩具总动员疯狂游戏屋",
    "Journey to the Center of the Earth": "地心探险之旅",
    "Tower of Terror": "惊魂古塔",
    "Indiana Jones® Adventure: Temple of the Crystal Skull": "印第安纳琼斯冒险旅程",
    "Raging Spirits": "忿怒双神",
    "Aquatopia": "水上逗趣船",
    "Turtle Talk": "龟龟漫谈"
}

def fetch_data():
    # 设置时区为东京时间 (UTC+9)
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    date_str = now.strftime("%Y-%m-%d")
    
    # 强制将时间规整为整点，例如 14:05 -> 14:00，适配前端拉杆
    hour_str = f"{now.hour:02d}:00"
    
    # 在非营业时间（通常 22:00 到次日 08:00）不记录数据，节省资源
    if not (8 <= now.hour <= 22):
        print(f"当前东京时间 {hour_str}，非营业时段，跳过抓取。")
        return

    # 1. 读取历史数据
    history_data = {}
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception:
            pass

    if date_str not in history_data:
        history_data[date_str] = {}

    # 2. 抓取实时数据
    headers = {"User-Agent": "TDS-Queue-Tracker/2.0 (GitHub Actions)"}
    try:
        response = requests.get(API_URL, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"获取 API 失败: {e}")
        return

    # 3. 解析并重组数据
    hour_rides = []
    for item in data.get("liveData", []):
        en_name = item.get("name")
        
        # 只记录映射表里存在的热门项目
        if en_name in TDS_TRANSLATIONS:
            cn_name = TDS_TRANSLATIONS[en_name]
            status = item.get("status")
            wait_time = 0
            
            if status == "OPERATING" and "queue" in item:
                standby = item["queue"].get("STANDBY")
                if standby and "waitTime" in standby:
                    wait_time = standby["waitTime"]
            
            # 模拟 DPA 状态 (API 无真实数据，根据时间模拟：越晚越容易售罄)
            dpa_sold_out = False
            if now.hour >= 15:
                dpa_sold_out = random.choice([True, False])
            if now.hour >= 18:
                dpa_sold_out = True

            hour_rides.append({
                "name_en": en_name,
                "name_cn": cn_name,
                "wait_time": wait_time if status == "OPERATING" else "Closed",
                "dpa_sold_out": dpa_sold_out
            })

    # 4. 存入 JSON 并写回文件
    history_data[date_str][hour_str] = hour_rides
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)
        
    print(f"✅ 成功记录东京时间 {date_str} {hour_str} 的排队数据。")

if __name__ == "__main__":
    fetch_data()