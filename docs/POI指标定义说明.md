# POI 指标定义说明

## 1. 这份文档解决什么问题

这份文档专门解释当前 POI 模块里各个类别和各个指标的含义，包括：

- `attractions`、`parking`、`commercial`、`public_service` 等类别到底是什么意思
- 每个字段怎么计算
- 哪些字段来自周边缓冲圈
- 哪些字段来自景区边界与内部外部划分

## 2. 当前 POI 数据的层级

当前 POI 模块主要有 4 层结果：

1. `scenic_poi_raw_all.csv`
   每行一个 POI 点位
2. `scenic_poi_summary_all.csv`
   每行是“景区-半径-类别”组合
3. `scenic_poi_feature_panel.csv`
   每行一个景区，适合直接做景区级分析
4. `scenic_poi_zone_summary.csv`
   每行是“景区-内部/外部分区”组合

另外还有边界与面积表：

- `scenic_boundary_master.csv`
- `scenic_area_summary.csv`

## 3. 景区锚点与距离怎么算

### 3.1 景区锚点

每个景区先有一个锚点坐标：

- `lat`
- `lng`

这个锚点是景区周边 POI 采集的中心点。

### 3.2 `distance_m`

每个 POI 到景区锚点的距离记为：

- `distance_m`

计算方法是：

- 以景区锚点经纬度为起点
- 以 POI 经纬度为终点
- 用球面距离公式近似计算两点间距离

所以 `distance_m` 表示：

- 该 POI 与景区锚点的直线距离，单位为米

## 4. 当前 7 个 POI 一级类别怎么定义

### 4.1 `transport`

中文建议写法：

- `交通接驳类`

当前大致包含：

- 公交站
- 公交枢纽
- 公共交通站台
- 火车/轨道站点
- 地铁入口
- 有轨电车站

当前脚本对应的 OSM 标签主要包括：

- `highway=bus_stop`
- `amenity=bus_station`
- `public_transport in {platform, station, stop_position}`
- `railway in {station, halt, subway_entrance, tram_stop}`
- `station=subway`

### 4.2 `parking`

中文建议写法：

- `停车与自驾支持类`

当前大致包含：

- 停车场
- 停车入口
- 停车位

当前脚本对应的 OSM 标签主要包括：

- `amenity in {parking, parking_entrance, parking_space}`

### 4.3 `food_retail`

中文建议写法：

- `餐饮与基础零售类`

当前大致包含：

- 餐馆
- 快餐
- 咖啡店
- 便利店
- 超市
- 小卖部

当前脚本对应的 OSM 标签主要包括：

- `amenity in {restaurant, fast_food, cafe, food_court}`
- `shop in {convenience, supermarket, kiosk}`

### 4.4 `lodging`

中文建议写法：

- `住宿与过夜服务类`

当前大致包含：

- 酒店
- 民宿
- 青旅
- 汽车旅馆
- 公寓式住宿

当前脚本对应的 OSM 标签主要包括：

- `tourism in {hotel, guest_house, hostel, motel, apartment}`

### 4.5 `commercial`

中文建议写法：

- `商业经营与消费压力类`

当前大致包含：

- 商场
- 百货
- 礼品店
- 纪念品店
- 集市

当前脚本对应的 OSM 标签主要包括：

- `amenity=marketplace`
- `shop in {mall, department_store, gift, souvenir}`

注意：

- 这个类别更偏“消费与售卖”空间
- 不是所有零售点都归到这里
- 便利店、超市、小卖部目前被归到 `food_retail`

### 4.6 `public_service`

中文建议写法：

- `公共服务与游客支持类`

当前大致包含：

- 公共厕所
- 药店
- 诊所
- 医院
- 医疗点
- 银行
- ATM
- 饮水点
- 游客信息点

当前脚本对应的 OSM 标签主要包括：

- `amenity in {toilets, pharmacy, clinic, hospital, doctors, bank, atm, drinking_water}`
- `tourism=information`

### 4.7 `nearby_attractions`

中文建议写法：

- `周边吸引物类`

你提到的 `attractions`，当前正式字段名是：

- `nearby_attractions`

它表示：

- 景区周边的其他旅游吸引点或游憩点

当前大致包含：

- 景点
- 博物馆
- 主题乐园
- 动物园
- 画廊
- 水族馆
- 观景点

当前脚本对应的 OSM 标签主要包括：

- `tourism in {attraction, museum, theme_park, zoo, gallery, aquarium, viewpoint}`

## 5. 一个 POI 是否只能属于一个类别

不是。

当前规则是：

- 一个 POI 会根据自身标签被映射到一个或多个类别

这意味着：

- `transport_count_1000m`
- `parking_count_1000m`
- `food_retail_count_1000m`

这些类别计数之间**不是互斥的**

所以要特别注意：

- 不要把所有类别计数直接相加后，当成 POI 总数

更准确的理解是：

- 这些是按类别视角统计出来的景区级特征

## 6. 缓冲圈指标怎么计算

当前正式缓冲圈是：

- `1000m`
- `2000m`

对每个景区、每个半径、每个类别，都计算两类核心指标：

### 6.1 `*_count_1000m / *_count_2000m`

例如：

- `transport_count_1000m`
- `parking_count_2000m`

计算规则是：

1. 先保留距离景区锚点不超过指定半径的 POI
2. 再在该半径内，筛出属于某一类别的 POI
3. 按 `element_uid` 去重后计数

所以：

`X_count_rm = 半径 r 内，属于类别 X 的唯一 POI 数量`

其中：

- `X` 可以是 `transport / parking / food_retail / lodging / commercial / public_service / nearby_attractions`
- `r` 可以是 `1000m / 2000m`

### 6.2 `nearest_*_dist_m_1000m / nearest_*_dist_m_2000m`

例如：

- `nearest_transport_dist_m_1000m`
- `nearest_public_service_dist_m_2000m`

计算规则是：

1. 在指定半径内筛出某类别所有 POI
2. 取其中距离景区锚点最近的一条

所以：

`nearest_X_dist_m_r = 半径 r 内，类别 X POI 到景区锚点的最小距离`

如果该半径内没有该类 POI，则该字段为空。

### 6.3 `poi_diversity_1000m / poi_diversity_2000m`

例如：

- `poi_diversity_1000m`

计算规则是：

- 在该半径内，7 个一级类别里有多少个类别的 `count > 0`

所以：

`poi_diversity_r = sum(1(X_count_r > 0))`

它反映的是：

- 景区周边配套结构是否更丰富

## 7. 景区边界、面积与内部外部怎么定义

### 7.1 `has_boundary_polygon`

取值：

- `1`：当前景区拿到了可用边界面
- `0`：当前景区没有可靠边界面

### 7.2 `scenic_area_m2`

表示：

- 景区边界面的近似面积，单位为平方米

计算逻辑是：

1. 读取景区边界面
2. 计算外环面积
3. 扣除内环面积

即：

`scenic_area_m2 = outer_area - inner_area`

### 7.3 `scenic_area_km2`

表示：

- 景区边界面的近似面积，单位为平方千米

公式是：

`scenic_area_km2 = scenic_area_m2 / 1,000,000`

注意：

- 它适合做相对比较和密度分母
- 不建议直接当作官方公布面积

### 7.4 `poi_zone`

取值有 3 种：

- `internal`
- `external`
- `unknown`

定义如下：

- `internal`：POI 点位落在景区边界面内部
- `external`：POI 点位落在景区边界面外部
- `unknown`：当前景区没有可靠边界面，无法判定

## 8. 内部外部汇总指标怎么计算

这部分输出在：

- `scenic_poi_zone_summary.csv`

每行是：

- 一个景区
- 一个分区状态（`internal / external / unknown`）

### 8.1 `poi_n`

表示：

- 该景区在对应分区里的 POI 总数

### 8.2 `transport_n / parking_n / food_retail_n ...`

例如：

- `transport_n`
- `public_service_n`
- `nearby_attractions_n`

表示：

- 该景区在对应分区里的该类 POI 数量

仍要注意：

- 因为一个 POI 可以同时落到多个类别
- 所以各类 `*_n` 之和不一定等于 `poi_n`

## 9. 论文里怎么写这些指标

推荐写法是：

1. 先说明以景区锚点为中心构建 `1000m / 2000m` 周边缓冲圈。
2. 再说明围绕交通、停车、餐饮零售、住宿、商业、公共服务和周边吸引物构造类别计数与最近距离指标。
3. 最后说明在具备边界面的景区上，进一步区分景区内部与景区外部 POI，并估算景区边界面积。

## 10. 当前最值得直接使用的字段

如果你下一步要继续做分析，我建议优先看这些字段：

- `transport_count_1000m`
- `parking_count_1000m`
- `public_service_count_1000m`
- `commercial_count_1000m`
- `nearby_attractions_count_2000m`
- `nearest_transport_dist_m_1000m`
- `nearest_parking_dist_m_1000m`
- `poi_diversity_1000m`
- `has_boundary_polygon`
- `scenic_area_km2`

如果你要解释“景区内部 vs 外部”，再进一步看：

- `poi_zone`
- `poi_n`
- `transport_n`
- `parking_n`
- `public_service_n`

## 11. 相关文件

- `旅游景点分析/data/poi/scenic_poi_feature_panel.csv`
- `旅游景点分析/data/poi/scenic_poi_zone_summary.csv`
- `旅游景点分析/data/poi/scenic_boundary_master.csv`
- `旅游景点分析/data/poi/scenic_area_summary.csv`
