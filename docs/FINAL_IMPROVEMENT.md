# Final bounded improvement

{
  "outcome": "NO_VERIFIED_IMPROVEMENT \u2014 ORIGINAL_DEFAULT_RETAINED",
  "default": {
    "model_id": "sss-pipeline-v3",
    "native_sha256": "bc85c96c1d0300d59de166898fbc378f614aa9d478eaa7762827811af9fab597",
    "threshold": 0.6818633675575256,
    "source_nms_iou": 0.5,
    "tile_nms_iou": 0.7,
    "verifier": null,
    "preprocessing": "unchanged"
  },
  "before": {
    "class_id": 0,
    "class_name": "Pipeline",
    "labelled_boxes": 365,
    "images": 674,
    "positive_images": 365,
    "tp": 179,
    "fp": 129,
    "fn": 186,
    "precision": 0.5811688311688312,
    "recall": 0.4904109589041096,
    "f1": 0.5319465081723626,
    "mAP50": 0.5113593223695664,
    "mAP50_95": 0.17833362867731298,
    "AP_by_IoU": [
      0.5113593223695664,
      0.4393697230245116,
      0.3278145725351578,
      0.23297602789241992,
      0.1423935939321948,
      0.0736590946957828,
      0.0358784132158496,
      0.013728879526350752,
      0.006069426188353476,
      8.723339294281853e-05
    ],
    "false_positives_per_image": 0.1913946587537092,
    "operational_threshold": 0.6818633675575256,
    "matching_IoU": 0.5,
    "mean_matched_iou": 0.7258355911389629
  },
  "after_default": {
    "class_id": 0,
    "class_name": "Pipeline",
    "labelled_boxes": 365,
    "images": 674,
    "positive_images": 365,
    "tp": 179,
    "fp": 129,
    "fn": 186,
    "precision": 0.5811688311688312,
    "recall": 0.4904109589041096,
    "f1": 0.5319465081723626,
    "mAP50": 0.5113593223695664,
    "mAP50_95": 0.17833362867731298,
    "AP_by_IoU": [
      0.5113593223695664,
      0.4393697230245116,
      0.3278145725351578,
      0.23297602789241992,
      0.1423935939321948,
      0.0736590946957828,
      0.0358784132158496,
      0.013728879526350752,
      0.006069426188353476,
      8.723339294281853e-05
    ],
    "false_positives_per_image": 0.1913946587537092,
    "operational_threshold": 0.6818633675575256,
    "matching_IoU": 0.5,
    "mean_matched_iou": 0.7258355911389629
  },
  "candidates": [
    {
      "name": "threshold_v3_nms_0.4",
      "nms": 0.4,
      "threshold": 0.6818633675575256,
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 179,
        "fp": 129,
        "fn": 186,
        "precision": 0.5811688311688312,
        "recall": 0.4904109589041096,
        "f1": 0.5319465081723626,
        "mAP50": 0.5072837010949534,
        "mAP50_95": 0.17523872194898743,
        "AP_by_IoU": [
          0.5072837010949534,
          0.4335476076126299,
          0.31923918065545764,
          0.2275892078452032,
          0.13779531183493768,
          0.07151244979852138,
          0.035526362696564714,
          0.013736738370310178,
          0.006069426188353476,
          8.723339294281853e-05
        ],
        "false_positives_per_image": 0.1913946587537092,
        "operational_threshold": 0.6818633675575256,
        "matching_IoU": 0.5,
        "mean_matched_iou": 0.7258355911389629
      },
      "differences": {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "mAP50_95": -0.003094906728325547,
        "mean_matched_iou": 0.0
      },
      "quantitative_gates_pass": false
    },
    {
      "name": "threshold_v3_nms_0.5",
      "nms": 0.5,
      "threshold": 0.6818633675575256,
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 179,
        "fp": 129,
        "fn": 186,
        "precision": 0.5811688311688312,
        "recall": 0.4904109589041096,
        "f1": 0.5319465081723626,
        "mAP50": 0.5113593223695664,
        "mAP50_95": 0.17833362867731298,
        "AP_by_IoU": [
          0.5113593223695664,
          0.4393697230245116,
          0.3278145725351578,
          0.23297602789241992,
          0.1423935939321948,
          0.0736590946957828,
          0.0358784132158496,
          0.013728879526350752,
          0.006069426188353476,
          8.723339294281853e-05
        ],
        "false_positives_per_image": 0.1913946587537092,
        "operational_threshold": 0.6818633675575256,
        "matching_IoU": 0.5,
        "mean_matched_iou": 0.7258355911389629
      },
      "differences": {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "mAP50_95": 0.0,
        "mean_matched_iou": 0.0
      },
      "quantitative_gates_pass": false
    },
    {
      "name": "threshold_v3_nms_0.6",
      "nms": 0.6,
      "threshold": 0.7,
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 172,
        "fp": 114,
        "fn": 193,
        "precision": 0.6013986013986014,
        "recall": 0.4712328767123288,
        "f1": 0.5284178187403994,
        "mAP50": 0.5122325957812951,
        "mAP50_95": 0.1819743240836808,
        "AP_by_IoU": [
          0.5122325957812951,
          0.4439123057012267,
          0.33558015005521846,
          0.24190892864308844,
          0.15116627030486973,
          0.07742891446636276,
          0.03745587678124342,
          0.013907837861964518,
          0.0060631278485958374,
          8.723339294281853e-05
        ],
        "false_positives_per_image": 0.16913946587537093,
        "operational_threshold": 0.7,
        "matching_IoU": 0.5,
        "mean_matched_iou": 0.7285468341550981
      },
      "differences": {
        "tp": -7,
        "fp": -15,
        "fn": 7,
        "mAP50_95": 0.0036406954063678276,
        "mean_matched_iou": 0.002711243016135234
      },
      "quantitative_gates_pass": false
    },
    {
      "name": "raw",
      "nms": 0.5,
      "threshold": 0.6818633675575256,
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 179,
        "fp": 129,
        "fn": 186,
        "precision": 0.5811688311688312,
        "recall": 0.4904109589041096,
        "f1": 0.5319465081723626,
        "mAP50": 0.5113593223695664,
        "mAP50_95": 0.17833362867731298,
        "AP_by_IoU": [
          0.5113593223695664,
          0.4393697230245116,
          0.3278145725351578,
          0.23297602789241992,
          0.1423935939321948,
          0.0736590946957828,
          0.0358784132158496,
          0.013728879526350752,
          0.006069426188353476,
          8.723339294281853e-05
        ],
        "false_positives_per_image": 0.1913946587537092,
        "operational_threshold": 0.6818633675575256,
        "matching_IoU": 0.5,
        "mean_matched_iou": 0.7258355911389629
      },
      "differences": {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "mAP50_95": 0.0,
        "mean_matched_iou": 0.0
      },
      "quantitative_gates_pass": false
    },
    {
      "name": "generic",
      "nms": 0.5,
      "threshold": 1.0,
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 0,
        "fp": 0,
        "fn": 365,
        "precision": null,
        "recall": 0.0,
        "f1": 0.0,
        "mAP50": 0.3908922137286406,
        "mAP50_95": 0.145060329899601,
        "AP_by_IoU": [
          0.3908922137286406,
          0.34331048394048425,
          0.27806995405328955,
          0.2005959335857895,
          0.12302601034981045,
          0.06447919297308219,
          0.03090215768384293,
          0.01350914389188425,
          0.0057187013510048785,
          9.950743818100404e-05
        ],
        "false_positives_per_image": 0.0,
        "operational_threshold": 1.0,
        "matching_IoU": 0.5,
        "mean_matched_iou": null
      },
      "differences": {
        "tp": -179,
        "fp": -129,
        "fn": 179,
        "mAP50_95": -0.033273298777711985,
        "mean_matched_iou": null
      },
      "quantitative_gates_pass": false
    },
    {
      "name": "acoustic",
      "nms": 0.5,
      "threshold": 1.0,
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 0,
        "fp": 0,
        "fn": 365,
        "precision": null,
        "recall": 0.0,
        "f1": 0.0,
        "mAP50": 0.39251853521814145,
        "mAP50_95": 0.1463745791732751,
        "AP_by_IoU": [
          0.39251853521814145,
          0.34089824857166723,
          0.2758538796207492,
          0.2000721786368042,
          0.1260203224390999,
          0.06969186540672552,
          0.03577441694728529,
          0.015598739557920972,
          0.007198316297019982,
          0.00011928903733746869
        ],
        "false_positives_per_image": 0.0,
        "operational_threshold": 1.0,
        "matching_IoU": 0.5,
        "mean_matched_iou": null
      },
      "differences": {
        "tp": -179,
        "fp": -129,
        "fn": 179,
        "mAP50_95": -0.031959049504037884,
        "mean_matched_iou": null
      },
      "quantitative_gates_pass": false
    }
  ],
  "optional_development_candidate": null,
  "reason": "Only one survey and repeatedly used validation exist. Verifier fitting is exploratory on detector-training observations; no independent generalization confirmation. Optional candidates must pass frozen numeric and localization gates.",
  "physics_beat_generic_at_same_budget": false,
  "training": {
    "status": "SKIPPED",
    "reason": "candidate ceiling and failure mix do not justify another detector recipe",
    "GPU_seconds": 0
  },
  "frozen_grid_physics_minus_generic_TP": 0,
  "descriptive_exact_score_comparison": {
    "scope": "Descriptive full-score PR operating points; NOT used to change the frozen threshold-grid selection or fit any model. The frozen grid under-resolves saturated verifier scores. No promotion from this secondary diagnostic.",
    "comparisons": {
      "raw": {
        "budgets": {
          "67": {
            "threshold": 0.7457579970359802,
            "tp": 139,
            "fp": 65,
            "fn": 226,
            "precision": 0.6813725490196079,
            "recall": 0.38082191780821917,
            "mean_matched_iou": 0.7209122135731199
          },
          "129": {
            "threshold": 0.6818633675575256,
            "tp": 179,
            "fp": 129,
            "fn": 186,
            "precision": 0.5811688311688312,
            "recall": 0.4904109589041096,
            "mean_matched_iou": 0.7258355911389629
          },
          "134": {
            "threshold": 0.6818633675575256,
            "tp": 179,
            "fp": 129,
            "fn": 186,
            "precision": 0.5811688311688312,
            "recall": 0.4904109589041096,
            "mean_matched_iou": 0.7258355911389629
          },
          "337": {
            "threshold": 0.4457051753997803,
            "tp": 224,
            "fp": 329,
            "fn": 141,
            "precision": 0.4050632911392405,
            "recall": 0.6136986301369863,
            "mean_matched_iou": 0.7221547783468083
          }
        },
        "maximum_pool_greedy_recall": 0.9232876712328767
      },
      "generic": {
        "budgets": {
          "67": {
            "threshold": 0.9977786423753686,
            "tp": 37,
            "fp": 65,
            "fn": 328,
            "precision": 0.3627450980392157,
            "recall": 0.10136986301369863,
            "mean_matched_iou": 0.771910247614903
          },
          "129": {
            "threshold": 0.9933531319405721,
            "tp": 162,
            "fp": 129,
            "fn": 203,
            "precision": 0.5567010309278351,
            "recall": 0.4438356164383562,
            "mean_matched_iou": 0.7222829861216508
          },
          "134": {
            "threshold": 0.9926390950650207,
            "tp": 167,
            "fp": 134,
            "fn": 198,
            "precision": 0.5548172757475083,
            "recall": 0.4575342465753425,
            "mean_matched_iou": 0.7217778319332726
          },
          "337": {
            "threshold": 0.9032283990945227,
            "tp": 229,
            "fp": 325,
            "fn": 136,
            "precision": 0.41335740072202165,
            "recall": 0.6273972602739726,
            "mean_matched_iou": 0.7141966904856496
          }
        },
        "maximum_pool_greedy_recall": 0.9232876712328767
      },
      "acoustic": {
        "budgets": {
          "67": {
            "threshold": 0.997573201980636,
            "tp": 43,
            "fp": 67,
            "fn": 322,
            "precision": 0.39090909090909093,
            "recall": 0.1178082191780822,
            "mean_matched_iou": 0.7759994770171039
          },
          "129": {
            "threshold": 0.9937299806515246,
            "tp": 157,
            "fp": 129,
            "fn": 208,
            "precision": 0.548951048951049,
            "recall": 0.4301369863013699,
            "mean_matched_iou": 0.7326746637533186
          },
          "134": {
            "threshold": 0.9933234841565486,
            "tp": 166,
            "fp": 133,
            "fn": 199,
            "precision": 0.5551839464882943,
            "recall": 0.4547945205479452,
            "mean_matched_iou": 0.7309571319784846
          },
          "337": {
            "threshold": 0.9179097482620763,
            "tp": 233,
            "fp": 331,
            "fn": 132,
            "precision": 0.41312056737588654,
            "recall": 0.6383561643835617,
            "mean_matched_iou": 0.7135085157710415
          }
        },
        "maximum_pool_greedy_recall": 0.9232876712328767
      }
    },
    "physics_minus_generic_TP_at129": -5
  }
}

{
  "comparisons": {
    "raw": {
      "point": {
        "threshold": 0.6818633675575256,
        "tp": 179,
        "fp": 129,
        "fn": 186,
        "precision": 0.5811688311688312,
        "recall": 0.4904109589041096,
        "f1": 0.5319465081723626,
        "false_alerts_per_original_frame": 0.1913946587537092
      },
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 179,
        "fp": 129,
        "fn": 186,
        "precision": 0.5811688311688312,
        "recall": 0.4904109589041096,
        "f1": 0.5319465081723626,
        "mAP50": 0.5113593223695664,
        "mAP50_95": 0.17833362867731298,
        "AP_by_IoU": [
          0.5113593223695664,
          0.4393697230245116,
          0.3278145725351578,
          0.23297602789241992,
          0.1423935939321948,
          0.0736590946957828,
          0.0358784132158496,
          0.013728879526350752,
          0.006069426188353476,
          8.723339294281853e-05
        ],
        "false_positives_per_image": 0.1913946587537092,
        "operational_threshold": 0.6818633675575256,
        "matching_IoU": 0.5,
        "mean_matched_iou": 0.7258355911389629
      },
      "budgets": {
        "67": {
          "threshold": 0.75,
          "tp": 135,
          "fp": 61,
          "fn": 230,
          "precision": 0.6887755102040817,
          "recall": 0.3698630136986301,
          "f1": 0.48128342245989303,
          "false_alerts_per_original_frame": 0.09050445103857567
        },
        "129": {
          "threshold": 0.6818633675575256,
          "tp": 179,
          "fp": 129,
          "fn": 186,
          "precision": 0.5811688311688312,
          "recall": 0.4904109589041096,
          "f1": 0.5319465081723626,
          "false_alerts_per_original_frame": 0.1913946587537092
        },
        "134": {
          "threshold": 0.6818633675575256,
          "tp": 179,
          "fp": 129,
          "fn": 186,
          "precision": 0.5811688311688312,
          "recall": 0.4904109589041096,
          "f1": 0.5319465081723626,
          "false_alerts_per_original_frame": 0.1913946587537092
        },
        "337": {
          "threshold": 0.45,
          "tp": 223,
          "fp": 322,
          "fn": 142,
          "precision": 0.4091743119266055,
          "recall": 0.6109589041095891,
          "f1": 0.4901098901098901,
          "false_alerts_per_original_frame": 0.47774480712166173
        }
      },
      "false_alerts_at_baseline_recall": {
        "threshold": 0.6818633675575256,
        "tp": 179,
        "fp": 129,
        "fn": 186,
        "precision": 0.5811688311688312,
        "recall": 0.4904109589041096,
        "f1": 0.5319465081723626,
        "false_alerts_per_original_frame": 0.1913946587537092
      },
      "review_yield": {
        "25": 23,
        "50": 44,
        "100": 86
      },
      "candidate_pool_recall": 0.9232876712328767,
      "seconds": 2.2875040052458644,
      "lateral_context_fallback_candidates": 0,
      "uncertainty_interval": null,
      "dependency_limit": "single survey; no independent acquisition bootstrap"
    },
    "generic": {
      "point": {
        "threshold": 1.0,
        "tp": 0,
        "fp": 0,
        "fn": 365,
        "precision": 0.0,
        "recall": 0.0
      },
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 0,
        "fp": 0,
        "fn": 365,
        "precision": null,
        "recall": 0.0,
        "f1": 0.0,
        "mAP50": 0.3908922137286406,
        "mAP50_95": 0.145060329899601,
        "AP_by_IoU": [
          0.3908922137286406,
          0.34331048394048425,
          0.27806995405328955,
          0.2005959335857895,
          0.12302601034981045,
          0.06447919297308219,
          0.03090215768384293,
          0.01350914389188425,
          0.0057187013510048785,
          9.950743818100404e-05
        ],
        "false_positives_per_image": 0.0,
        "operational_threshold": 1.0,
        "matching_IoU": 0.5,
        "mean_matched_iou": null
      },
      "budgets": {
        "67": {
          "threshold": 1.0,
          "tp": 0,
          "fp": 0,
          "fn": 365,
          "precision": 0.0,
          "recall": 0.0
        },
        "129": {
          "threshold": 1.0,
          "tp": 0,
          "fp": 0,
          "fn": 365,
          "precision": 0.0,
          "recall": 0.0
        },
        "134": {
          "threshold": 1.0,
          "tp": 0,
          "fp": 0,
          "fn": 365,
          "precision": 0.0,
          "recall": 0.0
        },
        "337": {
          "threshold": 0.9,
          "tp": 229,
          "fp": 329,
          "fn": 136,
          "precision": 0.4103942652329749,
          "recall": 0.6273972602739726,
          "f1": 0.4962080173347779,
          "false_alerts_per_original_frame": 0.48813056379821956
        }
      },
      "false_alerts_at_baseline_recall": {
        "threshold": 0.97,
        "tp": 210,
        "fp": 211,
        "fn": 155,
        "precision": 0.498812351543943,
        "recall": 0.5753424657534246,
        "f1": 0.5343511450381679,
        "false_alerts_per_original_frame": 0.31305637982195844
      },
      "review_yield": {
        "25": 1,
        "50": 9,
        "100": 35
      },
      "candidate_pool_recall": 0.9232876712328767,
      "seconds": 44.4020630097948,
      "lateral_context_fallback_candidates": 0,
      "uncertainty_interval": null,
      "dependency_limit": "single survey; no independent acquisition bootstrap"
    },
    "acoustic": {
      "point": {
        "threshold": 1.0,
        "tp": 0,
        "fp": 0,
        "fn": 365,
        "precision": 0.0,
        "recall": 0.0
      },
      "metrics": {
        "class_id": 0,
        "class_name": "Pipeline",
        "labelled_boxes": 365,
        "images": 674,
        "positive_images": 365,
        "tp": 0,
        "fp": 0,
        "fn": 365,
        "precision": null,
        "recall": 0.0,
        "f1": 0.0,
        "mAP50": 0.39251853521814145,
        "mAP50_95": 0.1463745791732751,
        "AP_by_IoU": [
          0.39251853521814145,
          0.34089824857166723,
          0.2758538796207492,
          0.2000721786368042,
          0.1260203224390999,
          0.06969186540672552,
          0.03577441694728529,
          0.015598739557920972,
          0.007198316297019982,
          0.00011928903733746869
        ],
        "false_positives_per_image": 0.0,
        "operational_threshold": 1.0,
        "matching_IoU": 0.5,
        "mean_matched_iou": null
      },
      "budgets": {
        "67": {
          "threshold": 1.0,
          "tp": 0,
          "fp": 0,
          "fn": 365,
          "precision": 0.0,
          "recall": 0.0
        },
        "129": {
          "threshold": 1.0,
          "tp": 0,
          "fp": 0,
          "fn": 365,
          "precision": 0.0,
          "recall": 0.0
        },
        "134": {
          "threshold": 1.0,
          "tp": 0,
          "fp": 0,
          "fn": 365,
          "precision": 0.0,
          "recall": 0.0
        },
        "337": {
          "threshold": 0.92,
          "tp": 232,
          "fp": 327,
          "fn": 133,
          "precision": 0.4150268336314848,
          "recall": 0.6356164383561644,
          "f1": 0.5021645021645021,
          "false_alerts_per_original_frame": 0.48516320474777447
        }
      },
      "false_alerts_at_baseline_recall": {
        "threshold": 0.97,
        "tp": 217,
        "fp": 211,
        "fn": 148,
        "precision": 0.5070093457943925,
        "recall": 0.5945205479452055,
        "f1": 0.5472887767969735,
        "false_alerts_per_original_frame": 0.31305637982195844
      },
      "review_yield": {
        "25": 0,
        "50": 9,
        "100": 37
      },
      "candidate_pool_recall": 0.9232876712328767,
      "seconds": 44.383176610805094,
      "lateral_context_fallback_candidates": 3647,
      "uncertainty_interval": null,
      "dependency_limit": "single survey; no independent acquisition bootstrap"
    }
  },
  "fit_seconds": 131.3233354901895,
  "feature_schema": [
    "raw_score",
    "score_logit",
    "width_fraction",
    "height_fraction",
    "log_aspect",
    "area_fraction",
    "boundary_truncation",
    "return_mean",
    "return_std",
    "return_q25",
    "return_q75",
    "context_contrast",
    "range_adjacent_dark_contrast",
    "range_dark_asymmetry",
    "range_dark_extent",
    "range_bright_dark_pair",
    "range_vs_alongtrack_gradient",
    "range_vs_alongtrack_profile_variation"
  ],
  "fit_is_exploratory": true,
  "physical_residual_trained": false,
  "actual_acoustic_features": "unsigned bright-return/dark-adjacency and anisotropy along documented raster range axis; not measured shadows, altitude or a PINN",
  "frozen_grid_physics_vs_generic_at_129_FP": 0,
  "descriptive_exact_score_physics_minus_generic_TP_at_129_FP": -5,
  "grid_limitation": "Frozen grid under-resolves scores above 0.99; use separately labeled exact_budget_diagnostics.json for descriptive matched-budget results, not promotion."
}

No independent uncertainty intervals: one acquisition group. The 674 validation frames are repeatedly used development observations. Training candidates were sampled from frozen training sources; the detector had seen those sources. Source groups were not randomly divided. Ambiguous overlaps were excluded from negative labels. Generic and acoustic models use the same L2 logistic family and fit rows. Actual acoustic features are unsigned range-axis bright/dark adjacency and directional structure. Heading, range calibration, side, true shadow geometry, altitude and correspondence are unavailable. Missing features fall back to generic scores. No detector threshold trade-off is called neural-network improvement.

SubPipe: CC BY 4.0, OceanScan-MST / REMARO, Zenodo12666132. Verifier coefficients and code are small distributable derived artifacts; detector weights remain in the authorized local registry.
