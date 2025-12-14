"""为现有模式添加annotations标注数据"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import StockDatabase
import json

def main():
    # 初始化数据库
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, '..', '..', 'data', 'stocks.db')
    db = StockDatabase(db_path=db_path)

    # 定义annotations数据（基于characteristics和key_features手动标注）
    annotations_data = {
        "缩量震荡后放量突破": {
            "regions": [
                {
                    "start_index": -15,
                    "end_index": -5,
                    "label": "横盘震荡期",
                    "type": "consolidation",
                    "color": "rgba(147, 197, 253, 0.2)"
                }
            ],
            "points": [
                {
                    "index": -1,
                    "label": "放量突破",
                    "type": "price_breakout",
                    "position": "above"
                },
                {
                    "index": -1,
                    "label": "成交量放大1.5倍",
                    "type": "volume_spike",
                    "position": "volume"
                }
            ],
            "lines": [
                {
                    "price": 0,  # 将由前端计算前期高点
                    "label": "前期高点压力位",
                    "type": "resistance",
                    "style": "dashed"
                }
            ]
        },

        "V型反转放量上攻": {
            "regions": [
                {
                    "start_index": -10,
                    "end_index": -5,
                    "label": "快速下跌期",
                    "type": "decline",
                    "color": "rgba(252, 165, 165, 0.2)"
                },
                {
                    "start_index": -4,
                    "end_index": -1,
                    "label": "快速反弹期",
                    "type": "rise",
                    "color": "rgba(134, 239, 172, 0.2)"
                }
            ],
            "points": [
                {
                    "index": -5,
                    "label": "V型底部",
                    "type": "pattern_signal",
                    "position": "below"
                },
                {
                    "index": -2,
                    "label": "放量反弹",
                    "type": "volume_spike",
                    "position": "volume"
                }
            ],
            "lines": []
        },

        "连续放量上攻": {
            "regions": [
                {
                    "start_index": -5,
                    "end_index": -1,
                    "label": "连续放量上涨",
                    "type": "rise",
                    "color": "rgba(134, 239, 172, 0.2)"
                }
            ],
            "points": [
                {
                    "index": -5,
                    "label": "启动放量",
                    "type": "volume_spike",
                    "position": "volume"
                },
                {
                    "index": -3,
                    "label": "持续放量",
                    "type": "volume_spike",
                    "position": "volume"
                },
                {
                    "index": -1,
                    "label": "延续放量",
                    "type": "volume_spike",
                    "position": "volume"
                }
            ],
            "lines": []
        },

        "中低位放量突破上升": {
            "regions": [
                {
                    "start_index": -14,
                    "end_index": -5,
                    "label": "震荡整理期",
                    "type": "consolidation",
                    "color": "rgba(147, 197, 253, 0.2)"
                },
                {
                    "start_index": -4,
                    "end_index": -1,
                    "label": "突破上升期",
                    "type": "breakout",
                    "color": "rgba(167, 139, 250, 0.2)"
                }
            ],
            "points": [
                {
                    "index": -4,
                    "label": "放量突破2.5倍",
                    "type": "volume_spike",
                    "position": "volume"
                },
                {
                    "index": -4,
                    "label": "突破前高15%",
                    "type": "price_breakout",
                    "position": "above"
                }
            ],
            "lines": [
                {
                    "price": 0,
                    "label": "前期整理平台",
                    "type": "support",
                    "style": "solid"
                }
            ]
        },

        "低波动震荡后温和反弹": {
            "regions": [
                {
                    "start_index": -14,
                    "end_index": -2,
                    "label": "低波动横盘期",
                    "type": "consolidation",
                    "color": "rgba(147, 197, 253, 0.2)"
                }
            ],
            "points": [
                {
                    "index": -1,
                    "label": "温和放量突破",
                    "type": "price_breakout",
                    "position": "above"
                },
                {
                    "index": -1,
                    "label": "成交量增长20%",
                    "type": "volume_spike",
                    "position": "volume"
                }
            ],
            "lines": [
                {
                    "price": 0,
                    "label": "整理平台高点",
                    "type": "resistance",
                    "style": "dashed"
                }
            ]
        }
    }

    # 更新数据库
    conn = db.get_connection()
    cursor = conn.cursor()

    update_count = 0
    for pattern_name, annotations in annotations_data.items():
        annotations_json = json.dumps(annotations, ensure_ascii=False)
        cursor.execute('''
            UPDATE rising_patterns
            SET annotations = ?
            WHERE pattern_name = ?
        ''', (annotations_json, pattern_name))
        update_count += cursor.rowcount

    conn.commit()
    conn.close()

    print(f"SUCCESS: Updated {update_count} patterns with annotations")

if __name__ == '__main__':
    main()
