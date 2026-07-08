# Salarium Backtest Reviewer Agent Report

**Status:** warn

**Summary:** Backtest review status: warn. Overall avg net excess 5D return: 0.001446. Overall Spearman IC: 0.006883. Overall long/short 5D return: 0.001887. Diagnosis: Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation. Warnings: 2. Errors: 0.

## Diagnosis

Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation.

## Overall Walk-Forward Metrics

| Metric | Value |
|---|---:|
| `num_rebalances` | 276.000000 |
| `avg_gross_top10_5d` | 0.005749 |
| `avg_net_top10_5d` | 0.004666 |
| `avg_universe_5d` | 0.003221 |
| `avg_net_excess_5d` | 0.001446 |
| `avg_bottom10_5d` | 0.003862 |
| `avg_long_short_5d` | 0.001887 |
| `avg_spearman_ic` | 0.006883 |

## Weak Periods

- **2021**: negative_net_excess, negative_spearman_ic, negative_long_short, bottom10_beats_top10
- **2022**: negative_net_excess, negative_spearman_ic, negative_long_short, bottom10_beats_top10
- **2024**: negative_net_excess
- **2026**: negative_spearman_ic, negative_long_short, bottom10_beats_top10

## Top Feature Importances

| Feature | Importance |
|---|---:|
| `relative_strength` | 0.159223 |
| `price_vs_ma50` | 0.154306 |
| `momentum_5d` | 0.151726 |
| `volatility_20d` | 0.134328 |
| `price_vs_ma20` | 0.125531 |
| `surprise_num` | 0.113848 |
| `momentum_20d` | 0.106605 |
| `rsi_14d` | 0.102467 |
| `macro_signal_score` | 0.099349 |
| `price_vs_ma50` | 0.088557 |
| `macro_tone_score` | 0.079520 |
| `momentum_5d` | 0.074742 |
| `momentum_20d` | 0.070021 |
| `volatility_20d` | 0.066428 |
| `return_1d` | 0.065813 |

## Warnings

- Overall Spearman IC is positive but weak.
- Weak walk-forward periods detected: [{'period': '2021', 'flags': ['negative_net_excess', 'negative_spearman_ic', 'negative_long_short', 'bottom10_beats_top10']}, {'period': '2022', 'flags': ['negative_net_excess', 'negative_spearman_ic', 'negative_long_short', 'bottom10_beats_top10']}, {'period': '2024', 'flags': ['negative_net_excess']}, {'period': '2026', 'flags': ['negative_spearman_ic', 'negative_long_short', 'bottom10_beats_top10']}]

## Raw Metrics

```json
{
  "walkforward": {
    "rows": 7,
    "columns": [
      "period",
      "num_rebalances",
      "avg_gross_top10_5d",
      "avg_net_top10_5d",
      "avg_universe_5d",
      "avg_net_excess_5d",
      "avg_bottom10_5d",
      "avg_long_short_5d",
      "avg_spearman_ic",
      "avg_turnover",
      "avg_transaction_cost",
      "net_hit_rate",
      "excess_hit_rate",
      "annualized_net_return",
      "net_sharpe",
      "excess_sharpe",
      "max_drawdown"
    ],
    "overall": {
      "num_rebalances": 276.0,
      "avg_gross_top10_5d": 0.0057489062247421,
      "avg_net_top10_5d": 0.0046662975290899,
      "avg_universe_5d": 0.0032206925294704,
      "avg_net_excess_5d": 0.0014456049996195,
      "avg_bottom10_5d": 0.0038615486070645,
      "avg_long_short_5d": 0.0018873576176775,
      "avg_spearman_ic": 0.0068833980452429
    },
    "yearly_periods": 6,
    "weak_periods": [
      {
        "period": "2021",
        "flags": [
          "negative_net_excess",
          "negative_spearman_ic",
          "negative_long_short",
          "bottom10_beats_top10"
        ]
      },
      {
        "period": "2022",
        "flags": [
          "negative_net_excess",
          "negative_spearman_ic",
          "negative_long_short",
          "bottom10_beats_top10"
        ]
      },
      {
        "period": "2024",
        "flags": [
          "negative_net_excess"
        ]
      },
      {
        "period": "2026",
        "flags": [
          "negative_spearman_ic",
          "negative_long_short",
          "bottom10_beats_top10"
        ]
      }
    ],
    "diagnosis": "Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation."
  },
  "macro_comparison": {
    "rows": 2,
    "columns": [
      "model",
      "train_rows",
      "test_rows",
      "test_start",
      "test_end",
      "accuracy",
      "auc",
      "avg_all_5d_return",
      "avg_top5_5d_return",
      "excess_top5_return"
    ],
    "model_column": "model",
    "models": [
      "baseline_technical_only",
      "technical_plus_macro_llm"
    ],
    "metric_columns": [
      "accuracy",
      "auc",
      "avg_all_5d_return",
      "avg_top5_5d_return",
      "excess_top5_return"
    ],
    "model_metrics": [
      {
        "model": "baseline_technical_only",
        "accuracy": 0.5508,
        "auc": 0.5082,
        "avg_all_5d_return": 0.00528,
        "avg_top5_5d_return": 0.00615,
        "excess_top5_return": 0.00087
      },
      {
        "model": "technical_plus_macro_llm",
        "accuracy": 0.5408,
        "auc": 0.51,
        "avg_all_5d_return": 0.00528,
        "avg_top5_5d_return": 0.00646,
        "excess_top5_return": 0.00118
      }
    ]
  },
  "feature_importance": {
    "rows": 28,
    "columns": [
      "feature",
      "importance",
      "model"
    ],
    "feature_column": "feature",
    "importance_column": "importance",
    "top_15_features": [
      {
        "feature": "relative_strength",
        "importance": 0.1592231974319241
      },
      {
        "feature": "price_vs_ma50",
        "importance": 0.1543055171452665
      },
      {
        "feature": "momentum_5d",
        "importance": 0.1517257809957416
      },
      {
        "feature": "volatility_20d",
        "importance": 0.1343278433923035
      },
      {
        "feature": "price_vs_ma20",
        "importance": 0.1255314609065023
      },
      {
        "feature": "surprise_num",
        "importance": 0.1138484033719946
      },
      {
        "feature": "momentum_20d",
        "importance": 0.1066054867975335
      },
      {
        "feature": "rsi_14d",
        "importance": 0.1024672505849132
      },
      {
        "feature": "macro_signal_score",
        "importance": 0.0993492080110417
      },
      {
        "feature": "price_vs_ma50",
        "importance": 0.0885572080598438
      },
      {
        "feature": "macro_tone_score",
        "importance": 0.0795195713018625
      },
      {
        "feature": "momentum_5d",
        "importance": 0.0747415938328065
      },
      {
        "feature": "momentum_20d",
        "importance": 0.0700210074180897
      },
      {
        "feature": "volatility_20d",
        "importance": 0.066427948061625
      },
      {
        "feature": "return_1d",
        "importance": 0.065813462745815
      }
    ],
    "macro_like_features_in_top_15": [
      "surprise_num",
      "macro_signal_score",
      "macro_tone_score"
    ]
  }
}
```
