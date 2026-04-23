# Experiment 9 POI Collection Report

## 1. Scope

- scenic_n: 20
- resolved_anchor_n: 20
- radius_list_m: 1000, 2000

## 2. POI categories

- transport
- parking
- food_retail
- lodging
- commercial
- public_service
- nearby_attractions

## 3. Scenic summary

- 故宫博物院: 1000m[transport=53, parking=9, food_retail=41, lodging=10, commercial=12, public_service=48, nearby_attractions=24] | 2000m[transport=377, parking=31, food_retail=250, lodging=69, commercial=29, public_service=136, nearby_attractions=59]
- 颐和园: 1000m[transport=15, parking=4, food_retail=8, commercial=1, public_service=10, nearby_attractions=9] | 2000m[transport=123, parking=20, food_retail=33, lodging=1, commercial=6, public_service=30, nearby_attractions=32]
- 天坛公园: 1000m[transport=66, parking=11, food_retail=12, lodging=5, commercial=4, public_service=21, nearby_attractions=17] | 2000m[transport=398, parking=33, food_retail=104, lodging=41, commercial=12, public_service=66, nearby_attractions=27]
- 景山公园: 1000m[transport=80, parking=8, food_retail=63, lodging=7, commercial=9, public_service=36, nearby_attractions=26] | 2000m[transport=346, parking=33, food_retail=354, lodging=77, commercial=27, public_service=180, nearby_attractions=65]
- 恭王府: 1000m[transport=63, parking=14, food_retail=114, lodging=5, commercial=5, public_service=34, nearby_attractions=17] | 2000m[transport=446, parking=47, food_retail=338, lodging=59, commercial=17, public_service=138, nearby_attractions=47]
- 明十三陵: 1000m[transport=16, parking=2, public_service=1, nearby_attractions=5] | 2000m[transport=56, parking=4, food_retail=3, public_service=3, nearby_attractions=6]
- 八达岭长城: 1000m[transport=21, parking=2, food_retail=23, lodging=5, commercial=9, public_service=16, nearby_attractions=13] | 2000m[transport=42, parking=17, food_retail=29, lodging=12, commercial=13, public_service=28, nearby_attractions=47]
- 慕田峪长城: 1000m[transport=3, parking=5, food_retail=7, lodging=1, commercial=1, public_service=17, nearby_attractions=10] | 2000m[transport=14, parking=7, food_retail=8, lodging=2, commercial=1, public_service=18, nearby_attractions=19]
- 居庸关长城: 1000m[transport=5, parking=4, food_retail=4, lodging=2, commercial=5, public_service=12, nearby_attractions=21] | 2000m[transport=28, parking=4, food_retail=4, lodging=2, commercial=5, public_service=13, nearby_attractions=25]
- 司马台长城: 1000m[lodging=2, public_service=1, nearby_attractions=1] | 2000m[transport=1, food_retail=4, lodging=6, commercial=1, public_service=5, nearby_attractions=6]
- 潭柘寺: 1000m[transport=7, parking=3, public_service=3, nearby_attractions=1] | 2000m[transport=25, parking=5, food_retail=2, lodging=4, public_service=4, nearby_attractions=9]
- 红螺寺: 1000m[transport=12, parking=8, food_retail=2, lodging=1, commercial=1, public_service=3] | 2000m[transport=28, parking=10, food_retail=2, lodging=1, commercial=1, public_service=6, nearby_attractions=3]
- 首都博物馆: 1000m[transport=144, food_retail=14, lodging=3, public_service=8] | 2000m[transport=491, parking=33, food_retail=56, lodging=23, commercial=5, public_service=45, nearby_attractions=2]
- 北京天文馆: 1000m[transport=160, parking=15, food_retail=31, lodging=9, commercial=5, public_service=29, nearby_attractions=8] | 2000m[transport=549, parking=44, food_retail=130, lodging=27, commercial=11, public_service=89, nearby_attractions=19]
- 中国科学技术馆: 1000m[transport=87, parking=13, food_retail=106, lodging=8, commercial=6, public_service=42, nearby_attractions=4] | 2000m[transport=267, parking=83, food_retail=253, lodging=36, commercial=7, public_service=116, nearby_attractions=18]
- 香山公园: 1000m[transport=6, parking=8, food_retail=13, lodging=1, commercial=2, public_service=19, nearby_attractions=16] | 2000m[transport=20, parking=18, food_retail=18, lodging=2, commercial=2, public_service=42, nearby_attractions=30]
- 北京动物园: 1000m[transport=142, parking=20, food_retail=41, lodging=7, commercial=5, public_service=25, nearby_attractions=8] | 2000m[transport=487, parking=44, food_retail=126, lodging=26, commercial=11, public_service=88, nearby_attractions=19]
- 玉渊潭公园: 1000m[transport=54, parking=4, food_retail=4, lodging=2, public_service=6, nearby_attractions=1] | 2000m[transport=451, parking=17, food_retail=59, lodging=20, commercial=5, public_service=36, nearby_attractions=4]
- 国家游泳中心: 1000m[transport=73, parking=18, food_retail=55, lodging=4, commercial=3, public_service=19, nearby_attractions=7] | 2000m[transport=343, parking=90, food_retail=254, lodging=34, commercial=8, public_service=95, nearby_attractions=11]
- 奥林匹克塔: 1000m[transport=74, parking=13, food_retail=64, lodging=9, commercial=4, public_service=41, nearby_attractions=3] | 2000m[transport=231, parking=82, food_retail=232, lodging=33, commercial=7, public_service=112, nearby_attractions=16]

## 4. Files

- anchor: `C:\baidunetdiskdownload\比赛\旅游景点分析\data\poi\scenic_anchor_master.csv`
- raw_all: `C:\baidunetdiskdownload\比赛\旅游景点分析\data\poi\scenic_poi_raw_all.csv`
- summary_all: `C:\baidunetdiskdownload\比赛\旅游景点分析\data\poi\scenic_poi_summary_all.csv`
- feature_panel: `C:\baidunetdiskdownload\比赛\旅游景点分析\data\poi\scenic_poi_feature_panel.csv`
