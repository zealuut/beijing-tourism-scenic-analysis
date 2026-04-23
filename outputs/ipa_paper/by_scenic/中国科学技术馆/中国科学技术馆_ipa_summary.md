# 中国科学技术馆 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：现场服务与导览体验
- importance：0.7096
- issue_rate：0.1347
- negative_rate：0.1917
- dissatisfaction：0.1632
- performance：0.8368
- priority_index：0.1158
- quadrant：高重要性高表现 = 继续保持

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 现场服务与导览体验       |    0.709559  |     0.134715 |         0.19171 |                0.163212 |      0.836788 |       0.115809   | 高重要性高表现 = 继续保持   |
|                      2 | 票务预约与入园体验       |    0.147059  |     0.55     |         0.675   |                0.6125   |      0.3875   |       0.0900735  | 低重要性低表现 = 次级改进   |
|                      3 | 交通与开放空间体验       |    0.0367647 |     0.2      |         0.2     |                0.2      |      0.8      |       0.00735294 | 低重要性高表现 = 低优先级观察 |