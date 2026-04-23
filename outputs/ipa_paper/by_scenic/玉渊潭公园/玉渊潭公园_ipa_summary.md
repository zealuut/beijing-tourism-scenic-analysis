# 玉渊潭公园 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.5581
- issue_rate：0.1007
- negative_rate：0.0671
- dissatisfaction：0.0839
- performance：0.9161
- priority_index：0.0468
- quadrant：高重要性高表现 = 继续保持

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant       |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:---------------|
|                      1 | 票务预约与入园体验       |    0.558052  |     0.100671 |       0.0671141 |               0.0838926 |      0.916107 |       0.0468165  | 高重要性高表现 = 继续保持 |
|                      2 | 现场服务与导览体验       |    0.0149813 |     0.25     |       0.5       |               0.375     |      0.625    |       0.00561798 | 低重要性低表现 = 次级改进 |
|                      3 | 交通与开放空间体验       |    0.303371  |     0        |       0.0246914 |               0.0123457 |      0.987654 |       0.00374532 | 高重要性高表现 = 继续保持 |