# SnowNLP景区领域情感打分说明

## 1. 这一步做什么

本实验用于在当前 20 个景区、6000 条评论样本上生成：

- 连续情感得分 `sentiment_score`
- 三分类情感标签 `sentiment_class`
- 景区级情感汇总结果

## 2. 能不能直接换成景区词表

严格来说，SnowNLP 不是简单的“情感词典打分”工具，不能只替换一份词表就完成领域适配。  
它的情感模块本质上是一个二分类朴素贝叶斯模型，因此更合适的做法是：

1. 用当前项目里的景区评论构造领域正负训练语料
2. 重训 SnowNLP 情感模型
3. 再用重训后的模型给 6000 条评论打连续分数
4. 最后把连续分数映射为 `positive / neutral / negative`

所以，这一步不是“直接换词表”，而是“用景区评论重训 SnowNLP”。

## 3. 当前项目的落地口径

输入数据使用：

- `旅游景点分析/data/issue_labels/experiment4_llm_issue_output_merged.csv`

训练语料口径：

- 正向训练语料：`rating = 5` 且 `issue_flag = 0`
- 负向训练语料：`rating <= 2`，或 `rating = 3` 且 `issue_flag = 1`
- 只保留文本长度达到最低要求的评论

这样做的目的是尽量用“高置信”的景区评论去学习领域情感边界，而不是直接把全部评论硬切成正负。

## 4. 输出字段

评论级输出里最重要的是 4 个字段：

- `snownlp_default_score`：默认 SnowNLP 分数
- `snownlp_domain_score`：景区领域重训后的分数
- `sentiment_score`：当前正式使用的情感得分，等于 `snownlp_domain_score`
- `sentiment_class`：三分类结果

其中：

- `sentiment_score` 越接近 `1`，越偏正向
- `sentiment_score` 越接近 `0`，越偏负向
- `neutral` 不代表没有情绪，而代表情绪不够强烈，或者正负混合

## 5. 三分类阈值

项目不是直接使用 SnowNLP 默认阈值，而是对多组阈值方案进行比较。  
当前正式推荐的方案是：

- `positive`：`sentiment_score >= 0.85`
- `negative`：`sentiment_score <= 0.10`
- `neutral`：其余区间

选择这组阈值的原则是：

1. 低分评论仍然应主要落在负向
2. 尽量减少“高分且无问题评论”被误判为负向
3. 保留一部分真正的中性区间，不把所有评论都硬压成正负两端

## 6. 主要输出文件

输出目录：

- `旅游景点分析/data/sentiment`

核心文件包括：

- `experiment5_snownlp_scored.csv`
- `experiment5_snownlp_threshold_compare.csv`
- `experiment5_snownlp_overall_summary.csv`
- `experiment5_snownlp_scenic_summary.csv`
- `experiment5_snownlp_report.md`
- `snownlp_scenic_sentiment.marshal`

## 7. 和现有问题标签的关系

情感分数和 `issue_tags` 不是一回事：

- `issue_tags` 回答的是“评论里提到了哪些治理问题”
- `sentiment_score` 回答的是“这条评论整体情绪更偏正向还是负向”

两者结合后，可以继续做：

- 高评分但负向情绪的偏离识别
- 高评分但存在问题标签的景区识别
- 低评分且高频问题集中的景区识别
