# POI 周边采集说明

## 1. 这一步做什么

本步骤对应项目的 POI 空间解释层。  
它不是重新识别评论问题，而是为景区补充周边空间供给信息。

当前先做最小可行版本：

- 当前正式 20 个景区
- 周边 `1000m / 2000m`
- 每个景区一个结果目录
- 同时导出全景区汇总表

## 2. 当前采集口径

由于本机当前没有可直接复用的高德 Web 服务 key，这一版先采用无 key 的 OSM / Overpass 方案做周边 POI 采集。  
这样可以先把 POI 层接进项目，后续如果补上高德 key，再把数据源切回高德即可。

当前输出仍然按你们 POI 文档里的分析口径组织，核心类别保留为：

1. `transport`
2. `parking`
3. `food_retail`
4. `lodging`
5. `commercial`
6. `public_service`
7. `nearby_attractions`

## 3. 锚点怎么来

脚本先从当前 20 景区主表里读取：

- `official_scenic_id`
- `scenic_name`
- `category_name`

然后用 OSM Nominatim 做景区锚点解析，并把锚点缓存到：

- `旅游景点分析/data/poi/scenic_anchor_master.csv`

需要注意：

- 这一版锚点是自动解析结果
- 仍然建议后续人工复核一次

## 4. 周边 POI 怎么抓

脚本对每个景区的锚点做一次最大半径抓取，然后再切分出：

- `1000m`
- `2000m`

这样做的好处是：

- 请求次数更少
- 后续想再补 `1500m` 或 `3000m` 也容易扩展

## 5. 当前每景区会输出什么

每个景区一个文件夹，位置在：

- `旅游景点分析/data/poi/by_scenic/<景区名>/`

其中包含：

- `<景区名>_poi_raw.csv`
  原始长表，每行一个 POI 点位
- `<景区名>_poi_summary.csv`
  汇总表，按半径和类别统计数量、最近距离

## 6. 当前全量汇总输出

全景区汇总结果在：

- `旅游景点分析/data/poi/scenic_poi_raw_all.csv`
- `旅游景点分析/data/poi/scenic_poi_summary_all.csv`
- `旅游景点分析/data/poi/scenic_poi_feature_panel.csv`
- `旅游景点分析/data/poi/poi_collection_report.md`

## 7. 结果怎么用于后续分析

当前这批结果已经可以直接支持：

- 看每个景区 `1000m / 2000m` 内交通接驳和停车支持是否偏弱
- 看每个景区近场商业和公共服务是否集中
- 后续并到景区级面板，用来解释 `traffic_access`、`commercialization`、`facility_hygiene` 等标签

## 8. 当前限制

这一版是可直接运行的最小可行版本，但要注意：

1. 当前数据源不是高德，而是 OSM fallback
2. 景区锚点还没有人工复核
3. 中国景区周边 POI 覆盖可能不如高德完整

所以这版更适合：

- 先把 POI 层接进项目
- 先看景区间相对差异

后续如果补上高德 key，再把数据源切回高德，会更贴合你们原始 POI 设计文档。
