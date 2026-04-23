# Beijing Tourism Scenic Analysis

北京旅游景区评论与空间解释项目。

当前仓库包含：

- 评论数据整理与实验脚本
- LDA 一级主题结果
- LLM 二级问题标签结果
- SnowNLP 情感打分结果
- 论文口径 IPA 与聚类结果
- 景区周边 POI、景区边界、内部外部 POI 与面积结果

## 目录结构

- `scripts/`
  项目实验脚本
- `docs/`
  方法说明、指标说明、全流程文档
- `dicts/`
  标签与规则字典
- `prompts/`
  LLM 标注 prompt 与 few-shot 示例
- `data/`
  项目中间数据、结果数据与 POI 数据
- `outputs/`
  IPA、聚类等图表与结果输出

## 当前核心分析链路

1. 原始景区评论整理
2. LDA 一级主题提取
3. LLM 11 个二级问题标签标注
4. SnowNLP 情感打分
5. 论文口径 IPA
6. 论文口径聚类
7. 景区周边 POI 与空间解释层

## 关键说明文档

- `docs/全流程文档.md`
- `docs/LDA一级主题与11个二级标签对应说明.md`
- `docs/POI指标定义说明.md`
- `docs/景区边界_内部外部POI_面积说明.md`

## 说明

- 当前仓库用于小组协作与数据互通，因此保留了 `data/` 目录。
- `outputs/` 中的副本目录和压缩包未纳入版本控制。
