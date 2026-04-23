# 景区边界、内部外部 POI 与景区面积说明

## 1. 这一步新增了什么

在原有周边 POI 采集基础上，这一步额外补了三层信息：

1. 景区边界
2. POI 属于景区内部还是景区外部
3. 景区面积

## 2. 当前判定逻辑

### 2.1 景区边界

优先使用 OSM 中与景区锚点对应的 `way / relation` 几何对象作为景区边界。

如果景区锚点本身只有点位、没有面边界，则暂不强行推断。

### 2.2 内部 / 外部

规则很直接：

- POI 点位落在景区边界面内 -> `internal`
- POI 点位落在景区边界面外 -> `external`
- 当前没有可用景区边界 -> `unknown`

### 2.3 景区面积

面积由景区边界面近似计算得到，输出为：

- `scenic_area_m2`
- `scenic_area_km2`

它更适合做：

- 景区间相对比较
- 内外部 POI 密度的分母

不建议把它直接当作官方法定面积。

## 3. 输出文件

- `旅游景点分析/data/poi/scenic_boundary_master.csv`
- `旅游景点分析/data/poi/scenic_poi_raw_all_zoned.csv`
- `旅游景点分析/data/poi/scenic_poi_zone_summary.csv`
- `旅游景点分析/data/poi/scenic_area_summary.csv`
- `旅游景点分析/data/poi/poi_boundary_report.md`

每个景区目录里也会补一份：

- `<景区名>_poi_raw_zoned.csv`

## 4. 当前限制

这一步依赖景区边界面。

因此：

- 有 `way / relation` 边界的景区，可以较稳地区分内部 / 外部
- 只有点位锚点、没有面边界的景区，会保留为 `unknown`

所以这一步的原则是：

- 宁可保留 `unknown`
- 不强行把不可靠的点位判成内部或外部
