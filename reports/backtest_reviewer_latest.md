# Salarium Backtest Reviewer Agent Report

**Status:** warn

**Summary:** Backtest review status: warn. Overall avg net excess 5D return: 0.001446. Overall Spearman IC: 0.006883. Overall long/short 5D return: 0.001887. Diagnosis: Promising but not proven. The ranking signal appears positive overall, but weak periods need investigation. Warnings: 4. Errors: 0.

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
| `avg_turnover` | 1.082609 |
| `avg_transaction_cost` | 0.001083 |
| `net_hit_rate` | 0.565217 |
| `excess_hit_rate` | 0.510870 |
| `annualized_net_return` | 0.202255 |
| `net_sharpe` | 0.738870 |
| `excess_sharpe` | 0.362395 |
| `max_drawdown` | -0.502249 |

## Weak Periods

- **2021**: negative_net_excess, negative_spearman_ic, negative_long_short, bottom10_beats_top10
- **2022**: negative_net_excess, negative_spearman_ic, negative_long_short, bottom10_beats_top10
- **2024**: negative_net_excess
- **2026**: negative_spearman_ic, negative_long_short, bottom10_beats_top10

## Top Feature Importances

| Feature | Importance |
|---|---:|
| `surprise_num` | 0.113848 |
| `macro_signal_score` | 0.099349 |
| `price_vs_ma50` | 0.088557 |
| `macro_tone_score` | 0.079520 |
| `momentum_5d` | 0.074742 |
| `momentum_20d` | 0.070021 |
| `volatility_20d` | 0.066428 |
| `price_vs_ma20` | 0.065425 |
| `relative_strength` | 0.064841 |
| `rsi_14d` | 0.052530 |
| `liquidity_num` | 0.049985 |
| `five_day_market_bias_score` | 0.047156 |
| `return_1d` | 0.032768 |
| `reaction_quality_num` | 0.022999 |
| `growth_num` | 0.022259 |

## Warnings

- Overall Spearman IC is positive but weak.
- Overall max drawdown is worse than -15%.
- Average turnover is high; transaction costs may be understated.
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
      "avg_spearman_ic": 0.0068833980452429,
      "avg_turnover": 1.082608695652174,
      "avg_transaction_cost": 0.0010826086956521,
      "net_hit_rate": 0.5652173913043478,
      "excess_hit_rate": 0.5108695652173914,
      "annualized_net_return": 0.2022548862013262,
      "net_sharpe": 0.7388699754621311,
      "excess_sharpe": 0.3623946317566217,
      "max_drawdown": -0.5022489201869706
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
    "selected_model_scope": "macro_model_only",
    "top_15_features": [
      {
        "feature": "surprise_num",
        "importance": 0.1138484033719946
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
        "feature": "price_vs_ma20",
        "importance": 0.0654248142575871
      },
      {
        "feature": "relative_strength",
        "importance": 0.0648408455064529
      },
      {
        "feature": "rsi_14d",
        "importance": 0.0525302418282831
      },
      {
        "feature": "liquidity_num",
        "importance": 0.0499846564266092
      },
      {
        "feature": "five_day_market_bias_score",
        "importance": 0.0471559179072824
      },
      {
        "feature": "return_1d",
        "importance": 0.032767500482838
      },
      {
        "feature": "reaction_quality_num",
        "importance": 0.0229991726954077
      },
      {
        "feature": "growth_num",
        "importance": 0.022259158744012
      }
    ],
    "macro_like_features_in_top_15": [
      "surprise_num",
      "macro_signal_score",
      "macro_tone_score",
      "liquidity_num",
      "growth_num"
    ]
  }
}
```
