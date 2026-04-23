# 国家游泳中心 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.2051
- issue_rate：0.4286
- negative_rate：0.6250
- dissatisfaction：0.5268
- performance：0.4732
- priority_index：0.1081
- quadrant：低重要性低表现 = 次级改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |     0.205128 |    0.428571  |        0.625    |               0.526786  |      0.473214 |         0.108059 | 低重要性低表现 = 次级改进   |
|                      2 | 交通与开放空间体验       |     0.395604 |    0.0462963 |        0.101852 |               0.0740741 |      0.925926 |         0.029304 | 高重要性高表现 = 继续保持   |
|                      3 | 现场服务与导览体验       |     0.025641 |    0.142857  |        0.142857 |               0.142857  |      0.857143 |         0.003663 | 低重要性高表现 = 低优先级观察 |