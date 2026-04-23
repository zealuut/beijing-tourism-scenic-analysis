# IPA与聚类说明

## 1. 本轮输入数据

本轮 IPA 与聚类使用三张现有结果表：

- `data/sentiment/experiment5_snownlp_scored.csv`
- `data/lda/experiment3_lda_topic_assignments.csv`
- `data/issue_labels/experiment4_llm_issue_output_merged.csv` 的字段已经包含在情感总表中

也就是说，这一步是在以下三层结果之上继续聚合：

1. `LDA` 一级主题
2. `LLM` 二级问题标签
3. `SnowNLP` 情感得分与三分类

## 2. 景区优先级口径

景区层 `priority_score` 沿用项目原来的混合优先级公式，不重新发明口径。

使用的特征有：

- `issue_review_rate_hybrid`
- `issue_divergence_rate`
- `high_rating_with_issue_rate`
- `queue_wait_rate`
- `reservation_entry_rate`
- `service_process_rate`
- `ticket_price_rate`
- `traffic_access_rate`
- `crowding_rate`

先对上述特征做 Min-Max 标准化，再按下列权重加权：

- `0.30 * issue_review_rate_hybrid`
- `0.20 * issue_divergence_rate`
- `0.15 * high_rating_with_issue_rate`
- `0.10 * queue_wait_rate`
- `0.10 * reservation_entry_rate`
- `0.06 * service_process_rate`
- `0.04 * ticket_price_rate`
- `0.03 * traffic_access_rate`
- `0.02 * crowding_rate`

## 3. 一级主题IPA口径

本轮 IPA 不是直接用 11 个细标签作图，而是继续沿用项目主线：

`LDA 一级主题 -> IPA -> 细标签解释`

当前 LDA 输出里有重复命名的“票务预约与入园体验”子主题，所以在 IPA 阶段按同名一级主题合并。  
满意主题 `整体满意与感知评价` 保留在主题结构里，但不进入治理优先级 IPA。

### Importance

Importance 不是手工指定，而是根据某一级主题在景区层的主题问题强度，与景区优先级指标的相关性计算：

`Importance_raw = 0.40*|corr(theme_issue_share, issue_divergence_rate)| + 0.35*|corr(theme_issue_share, high_rating_with_issue_rate)| + 0.25*|corr(theme_issue_share, priority_score)|`

然后再做 Min-Max 标准化得到最终 `Importance`。

### Gap

Gap 使用一级主题问题强度的标准化值：

- 整体 IPA：`gap = minmax(theme_issue_share_mean)`
- 单景区 IPA：`scenic_gap = minmax(theme_issue_share_total)`

其中：

- `theme_issue_share_mean` 表示该主题在全部景区中的平均问题评论占比
- `theme_issue_share_total` 表示某景区该主题的问题评论占该景区正式样本的比例

### Performance

- `performance = 1 - gap`

## 4. 单景区输出

每个景区都有一个独立文件夹，放在：

- `outputs/ipa/by_scenic/<景区名>/`

每个文件夹内包含：

- 该景区 IPA 图
- 该景区 IPA 结果表
- 该景区 IPA 简述

## 5. 聚类口径

聚类单位是 20 个景区。  
特征使用：

- 景区优先级和问题强度
- 情感表现
- 一级主题问题占比

本轮聚类特征包括：

- `priority_score`
- `issue_review_rate_hybrid`
- `issue_divergence_rate`
- `high_rating_with_issue_rate`
- `negative_sentiment_rate`
- `avg_sentiment_index`
- 各一级治理主题的 `theme_issue_share_total`

处理方式：

1. 标准化特征
2. 比较 `k=2` 到 `k=5`
3. 用轮廓系数选择最终 `k`
4. 使用 `KMeans`
5. 再用 `PCA` 降到二维做可视化

## 6. 输出位置

IPA 输出：

- `outputs/ipa/overall`
- `outputs/ipa/by_scenic`

聚类输出：

- `outputs/clustering`
