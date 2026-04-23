# IPA总体报告

## 1. 计算口径
- 景区优先级沿用项目原有混合口径：先在景区层计算 `priority_score`，再把一级主题的主题问题强度与景区优先级指标做相关，得到 IPA 的 `Importance`。
- `Importance_raw = 0.40*|corr(theme_issue_share, issue_divergence_rate)| + 0.35*|corr(theme_issue_share, high_rating_with_issue_rate)| + 0.25*|corr(theme_issue_share, priority_score)|`。
- `Gap` 使用主题问题强度 `theme_issue_share_mean` 的 Min-Max 标准化结果；`Performance = 1 - Gap`。
- 当前景区样本的满意主题不进入 IPA 排序，被剔除的满意主题为：整体满意与感知评价

## 2. 整体一级主题IPA
|   overall_priority_rank | theme_name_cn   |   importance |      gap |   performance |   theme_issue_share_mean |   theme_negative_share_mean | quadrant       |
|------------------------:|:----------------|-------------:|---------:|--------------:|-------------------------:|----------------------------:|:---------------|
|                       1 | 票务预约与入园体验       |    1         | 1        |      0        |               0.0713333  |                  0.103      | 高重要性高缺口 = 优先改进 |
|                       2 | 交通与开放空间体验       |    0.0060483 | 0        |      1        |               0.00433333 |                  0.00616667 | 低重要性低缺口 = 观察即可 |
|                       3 | 现场服务与导览体验       |    0         | 0.171642 |      0.828358 |               0.0158333  |                  0.0216667  | 低重要性低缺口 = 观察即可 |

## 3. 20个景区的首要治理主题
### 慕田峪长城
- priority_rank: 1
- priority_score: 0.7839
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 北京动物园
- priority_rank: 2
- priority_score: 0.7837
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 八达岭长城
- priority_rank: 3
- priority_score: 0.6833
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 天坛公园
- priority_rank: 4
- priority_score: 0.6697
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 中国科学技术馆
- priority_rank: 5
- priority_score: 0.5905
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=0.8333, priority_index=0.8333, quadrant=高重要性高缺口 = 优先改进

### 奥林匹克塔
- priority_rank: 6
- priority_score: 0.5774
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 明十三陵
- priority_rank: 7
- priority_score: 0.5624
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 北京天文馆
- priority_rank: 8
- priority_score: 0.5505
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 司马台长城
- priority_rank: 9
- priority_score: 0.4778
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 恭王府
- priority_rank: 10
- priority_score: 0.4503
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 国家游泳中心
- priority_rank: 11
- priority_score: 0.4211
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 香山公园
- priority_rank: 12
- priority_score: 0.4112
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 潭柘寺
- priority_rank: 13
- priority_score: 0.3741
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 故宫博物院
- priority_rank: 14
- priority_score: 0.3066
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 颐和园
- priority_rank: 15
- priority_score: 0.2525
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 玉渊潭公园
- priority_rank: 16
- priority_score: 0.2396
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 景山公园
- priority_rank: 17
- priority_score: 0.2100
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 居庸关长城
- priority_rank: 18
- priority_score: 0.1835
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 红螺寺
- priority_rank: 19
- priority_score: 0.1299
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进

### 首都博物馆
- priority_rank: 20
- priority_score: 0.0476
- 首要治理主题: 票务预约与入园体验
- importance=1.0000, gap=1.0000, priority_index=1.0000, quadrant=高重要性高缺口 = 优先改进
