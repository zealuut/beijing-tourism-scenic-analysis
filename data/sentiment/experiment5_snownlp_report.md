# Experiment 5 SnowNLP Scenic Sentiment Report

## 1. Method
- This experiment does not simply replace a sentiment lexicon.
- SnowNLP is retrained with scenic-domain review text from the current 6000-review project corpus.
- The domain score is then mapped into `positive / neutral / negative` with calibrated thresholds.

## 2. Training Corpus
- Positive training reviews: 405
- Negative training reviews: 405

## 3. Threshold Comparison
                     scheme_name  pos_threshold  neg_threshold  pseudo_accuracy  pseudo_macro_f1  manual_accuracy  positive_share  neutral_share  negative_share  high_rating_negative_rate  high_rating_no_issue_negative_rate  five_star_no_issue_negative_rate  low_rating_negative_rate  is_recommended
scheme_h_pos_ge_0.85_neg_le_0.10           0.85           0.10         0.716877         0.508130         0.541667        0.613833       0.176000        0.210167                   0.149635                            0.111111                          0.100275                  0.984615               1
scheme_f_pos_ge_0.80_neg_le_0.15           0.80           0.15         0.731664         0.498781         0.541667        0.633167       0.137833        0.229000                   0.168248                            0.128623                          0.117026                  0.996154               0
scheme_g_pos_ge_0.85_neg_le_0.15           0.85           0.15         0.715497         0.494501         0.541667        0.613833       0.157167        0.229000                   0.168248                            0.128623                          0.117026                  0.996154               0
scheme_e_pos_ge_0.80_neg_le_0.20           0.80           0.20         0.730087         0.489462         0.541667        0.633167       0.127833        0.239000                   0.178285                            0.137480                          0.125516                  0.996154               0
scheme_d_pos_ge_0.75_neg_le_0.25           0.75           0.25         0.743297         0.485142         0.541667        0.649000       0.102333        0.248667                   0.188139                            0.146739                          0.133547                  0.996154               0
scheme_c_pos_ge_0.70_neg_le_0.30           0.70           0.30         0.753549         0.480797         0.541667        0.664000       0.078500        0.257500                   0.197445                            0.155193                          0.141808                  1.000000               0
scheme_b_pos_ge_0.65_neg_le_0.35           0.65           0.35         0.762224         0.473622         0.541667        0.676500       0.056000        0.267500                   0.208212                            0.165862                          0.153052                  1.000000               0
scheme_a_pos_ge_0.60_neg_le_0.40           0.60           0.40         0.767942         0.462449         0.541667        0.686333       0.036333        0.277333                   0.218978                            0.176731                          0.163378                  1.000000               0

## 4. Recommended Scheme
- Recommended threshold scheme: `scheme_h_pos_ge_0.85_neg_le_0.10`
- Selection principle: keep low-rating reviews negative, while reducing false negatives among high-rating no-issue reviews.

## 5. Overall Summary
 review_n  avg_default_score  avg_domain_score  positive_share  neutral_share  negative_share  avg_sentiment_index  high_rating_negative_rate  high_rating_no_issue_negative_rate  five_star_no_issue_negative_rate  low_rating_negative_rate
     6000           0.840016          0.695554        0.613833          0.176        0.210167             0.701833                   0.149635                            0.111111                          0.100275                  0.984615

## 6. Interpretation
- `snownlp_domain_score` closer to `1` means more positive; closer to `0` means more negative.
- `neutral` means the emotional polarity is mixed or not strong enough.