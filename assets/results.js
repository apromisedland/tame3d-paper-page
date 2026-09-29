window.TAME3D_RESULTS = {
  "schema_version": 1,
  "source": "Accompanying Tame3D manuscript and its per-seed aggregate counts",
  "seeds": [
    17,
    29,
    43,
    71,
    101
  ],
  "split_sizes_per_seed": {
    "development": 400,
    "calibration": 600,
    "test": 1000,
    "shift": 1000
  },
  "questions_per_scene": 1,
  "aggregation": "Calculate each seed's metric, then arithmetic mean and sample standard deviation (ddof=1).",
  "aggregation_formulas": {
    "mean": "sum(per_seed_values) / number_of_seeds",
    "std": "sqrt(sum((value - mean) ** 2) / (number_of_seeds - 1))",
    "std_ddof": 1,
    "uncertainty": "Sample standard deviation across seeds, not a confidence interval.",
    "seed_index": "Array index in seeds; no pooling across seeds before calculating a metric."
  },
  "evaluation_protocol": {
    "point_baselines": "Initial-observation ordinary singleton predictions. Coverage and selective accuracy equal forced accuracy; answer rate is 100%, set size is 1, and additional acquisitions are 0.",
    "fixed": "Evaluate at the declared round; Fixed (2) always uses two additional observations per expert.",
    "adaptive": "Evaluate at the first accepted round, or at round 2 after abstention.",
    "risk_allocation": "Total alpha = 0.10. Each fixed rule uses alpha at one round; Adaptive uses alpha / 3 at each of rounds 0, 1, 2.",
    "shift": "Retention probabilities decrease by 0.20; position-noise SDs multiply by 1.7; yaw-noise SDs multiply by 2.5. Predictive draws use shifted noise scales, while clean-data temperatures and thresholds remain fixed."
  },
  "metrics": {
    "accuracy": {
      "label": "Forced accuracy",
      "unit": "%",
      "definition": "Correct highest-scoring ordinary candidates / all questions, including questions on which the controller abstains.",
      "numerator": "forced_correct",
      "denominator": "examples_per_summary",
      "formula": "100 * forced_correct[seed_index] / examples_per_summary"
    },
    "coverage": {
      "label": "Mapped-label coverage",
      "unit": "%",
      "definition": "Mapped true labels retained in the prediction set / all questions. A missing true answer maps to Other; covering Other does not recover that answer string.",
      "numerator": "covered",
      "denominator": "examples_per_summary",
      "formula": "100 * covered[seed_index] / examples_per_summary"
    },
    "size": {
      "label": "Mean set size",
      "unit": "labels",
      "definition": "Total retained labels, including Other when present, / all questions.",
      "numerator": "set_size_total",
      "denominator": "examples_per_summary",
      "formula": "set_size_total[seed_index] / examples_per_summary"
    },
    "answer": {
      "label": "Answer rate",
      "unit": "%",
      "definition": "Accepted ordinary singleton answers / all questions. Point baselines always output an ordinary singleton.",
      "numerator": "answered",
      "denominator": "examples_per_summary",
      "formula": "100 * answered[seed_index] / examples_per_summary"
    },
    "selective": {
      "label": "Selective accuracy",
      "unit": "%",
      "definition": "Correct accepted answers / accepted answers; this conditional empirical rate is not the conformal coverage guarantee.",
      "numerator": "accepted_correct",
      "denominator": "answered",
      "formula": "100 * accepted_correct[seed_index] / answered[seed_index]"
    },
    "joint_error": {
      "label": "Joint error",
      "unit": "%",
      "definition": "Wrong accepted answers / all questions. Abstentions remain in the denominator. Computed from counts within each seed before averaging.",
      "numerator": "answered - accepted_correct",
      "denominator": "examples_per_summary",
      "formula": "100 * (answered[seed_index] - accepted_correct[seed_index]) / examples_per_summary"
    },
    "views": {
      "label": "Additional acquisitions",
      "unit": "observations per question",
      "definition": "Additional acquisition rounds / all questions. Each acquisition supplies one observation to each of the two experts; the initial observation is excluded. This is not the sum of separate expert calls, latency, or token cost.",
      "numerator": "acquisition_total",
      "denominator": "examples_per_summary",
      "formula": "acquisition_total[seed_index] / examples_per_summary"
    },
    "candidate_recall": {
      "label": "Candidate recall",
      "unit": "%",
      "definition": "Questions whose ordinary candidate list contains the true answer / all questions. The candidate mask is shared by methods and fixed across rounds.",
      "numerator": "candidate_present",
      "denominator": "examples_per_summary",
      "formula": "100 * candidate_present[seed_index] / examples_per_summary"
    },
    "simultaneous": {
      "label": "All-round mapped coverage",
      "unit": "%",
      "definition": "Questions whose mapped label is covered at every potential round / all questions; distinct from coverage at the selected adaptive round.",
      "numerator": "simultaneous_covered",
      "denominator": "examples_per_summary",
      "formula": "100 * simultaneous_covered[seed_index] / examples_per_summary"
    },
    "count": {
      "label": "Count-query forced accuracy",
      "unit": "%",
      "definition": "Correct forced answers to count queries / count queries, calculated per seed before averaging.",
      "numerator": "type_correct[seed_index][0]",
      "denominator": "question_counts[seed_index][0]",
      "formula": "100 * type_correct[seed_index][0] / question_counts[seed_index][0]"
    },
    "direction": {
      "label": "Direction-query forced accuracy",
      "unit": "%",
      "definition": "Correct forced answers to relative-direction queries / relative-direction queries, calculated per seed before averaging.",
      "numerator": "type_correct[seed_index][1]",
      "denominator": "question_counts[seed_index][1]",
      "formula": "100 * type_correct[seed_index][1] / question_counts[seed_index][1]"
    },
    "nearest": {
      "label": "Nearest-category forced accuracy",
      "unit": "%",
      "definition": "Correct forced answers to nearest-category queries / nearest-category queries, calculated per seed before averaging.",
      "numerator": "type_correct[seed_index][2]",
      "denominator": "question_counts[seed_index][2]",
      "formula": "100 * type_correct[seed_index][2] / question_counts[seed_index][2]"
    }
  },
  "conditions": {
    "test": {
      "Embodied": {
        "display_name": "Egocentric",
        "metrics": {
          "accuracy": {
            "mean": 68.8,
            "std": 0.997496867162999
          },
          "coverage": {
            "mean": 68.8,
            "std": 0.997496867162999
          },
          "size": {
            "mean": 1.0,
            "std": 0.0
          },
          "answer": {
            "mean": 100.0,
            "std": 0.0
          },
          "selective": {
            "mean": 68.8,
            "std": 0.997496867162999
          },
          "joint_error": {
            "mean": 31.2,
            "std": 0.9974968671630005
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          }
        }
      },
      "Global": {
        "display_name": "Global",
        "metrics": {
          "accuracy": {
            "mean": 72.3,
            "std": 0.8631338250816046
          },
          "coverage": {
            "mean": 72.3,
            "std": 0.8631338250816046
          },
          "size": {
            "mean": 1.0,
            "std": 0.0
          },
          "answer": {
            "mean": 100.0,
            "std": 0.0
          },
          "selective": {
            "mean": 72.3,
            "std": 0.8631338250816046
          },
          "joint_error": {
            "mean": 27.7,
            "std": 0.8631338250816032
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          }
        }
      },
      "Unscaled fusion": {
        "display_name": "Unscaled fusion",
        "metrics": {
          "accuracy": {
            "mean": 72.8,
            "std": 0.9273618495495698
          },
          "coverage": {
            "mean": 72.8,
            "std": 0.9273618495495698
          },
          "size": {
            "mean": 1.0,
            "std": 0.0
          },
          "answer": {
            "mean": 100.0,
            "std": 0.0
          },
          "selective": {
            "mean": 72.8,
            "std": 0.9273618495495698
          },
          "joint_error": {
            "mean": 27.2,
            "std": 0.9273618495495706
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          }
        }
      },
      "Aligned fusion": {
        "display_name": "Aligned fusion",
        "metrics": {
          "accuracy": {
            "mean": 74.8,
            "std": 0.9137833441248538
          },
          "coverage": {
            "mean": 74.8,
            "std": 0.9137833441248538
          },
          "size": {
            "mean": 1.0,
            "std": 0.0
          },
          "answer": {
            "mean": 100.0,
            "std": 0.0
          },
          "selective": {
            "mean": 74.8,
            "std": 0.9137833441248538
          },
          "joint_error": {
            "mean": 25.2,
            "std": 0.9137833441248532
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          }
        }
      },
      "Conformal fixed (0)": {
        "display_name": "Fixed (0)",
        "metrics": {
          "accuracy": {
            "mean": 74.8,
            "std": 0.9137833441248538
          },
          "coverage": {
            "mean": 90.8,
            "std": 0.561248608016091
          },
          "size": {
            "mean": 1.5,
            "std": 0.02915475947422653
          },
          "answer": {
            "mean": 59.6,
            "std": 1.6431676725154976
          },
          "selective": {
            "mean": 93.47749379809144,
            "std": 0.566809652259871
          },
          "joint_error": {
            "mean": 3.88,
            "std": 0.22803508501982767
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          }
        }
      },
      "Conformal fixed (2)": {
        "display_name": "Fixed (2)",
        "metrics": {
          "accuracy": {
            "mean": 89.6,
            "std": 0.8154753215150057
          },
          "coverage": {
            "mean": 92.5,
            "std": 0.6324555320336787
          },
          "size": {
            "mean": 1.108,
            "std": 0.027748873851023155
          },
          "answer": {
            "mean": 92.0,
            "std": 1.048808848170153
          },
          "selective": {
            "mean": 95.27869881249946,
            "std": 0.44999235514476316
          },
          "joint_error": {
            "mean": 4.34,
            "std": 0.36469165057620956
          },
          "views": {
            "mean": 2.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          }
        }
      },
      "Adaptive aligned": {
        "display_name": "Adaptive",
        "metrics": {
          "accuracy": {
            "mean": 87.1,
            "std": 1.0049875621120934
          },
          "coverage": {
            "mean": 96.7,
            "std": 0.5099019513592766
          },
          "size": {
            "mean": 1.222,
            "std": 0.03271085446759228
          },
          "answer": {
            "mean": 83.6,
            "std": 1.6911534525287768
          },
          "selective": {
            "mean": 97.38514378463168,
            "std": 0.45401809690382594
          },
          "joint_error": {
            "mean": 2.18,
            "std": 0.3346640106136302
          },
          "views": {
            "mean": 1.064,
            "std": 0.040373258476372735
          },
          "candidate_recall": {
            "mean": 95.6,
            "std": 0.27386127875258304
          },
          "simultaneous": {
            "mean": 93.8,
            "std": 0.6595452979136408
          },
          "count": {
            "mean": 85.49705933516293,
            "std": 1.2436843544488736
          },
          "direction": {
            "mean": 92.24077656892865,
            "std": 0.8609610496113755
          },
          "nearest": {
            "mean": 83.51268830671816,
            "std": 1.0755189242296552
          }
        }
      }
    },
    "shift": {
      "Aligned fusion": {
        "display_name": "Aligned fusion",
        "metrics": {
          "accuracy": {
            "mean": 60.6,
            "std": 1.2020815280171324
          },
          "coverage": {
            "mean": 60.6,
            "std": 1.2020815280171324
          },
          "size": {
            "mean": 1.0,
            "std": 0.0
          },
          "answer": {
            "mean": 100.0,
            "std": 0.0
          },
          "selective": {
            "mean": 60.6,
            "std": 1.2020815280171324
          },
          "joint_error": {
            "mean": 39.4,
            "std": 1.2020815280171324
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.4,
            "std": 0.29154759474226427
          }
        }
      },
      "Conformal fixed (0)": {
        "display_name": "Fixed (0)",
        "metrics": {
          "accuracy": {
            "mean": 60.6,
            "std": 1.2020815280171324
          },
          "coverage": {
            "mean": 84.24,
            "std": 0.7765307463326847
          },
          "size": {
            "mean": 1.79,
            "std": 0.036055512754639925
          },
          "answer": {
            "mean": 41.6,
            "std": 1.7846568297574736
          },
          "selective": {
            "mean": 79.44379288310537,
            "std": 0.8041374831313082
          },
          "joint_error": {
            "mean": 8.54,
            "std": 0.05477225575051642
          },
          "views": {
            "mean": 0.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.4,
            "std": 0.29154759474226427
          }
        }
      },
      "Conformal fixed (2)": {
        "display_name": "Fixed (2)",
        "metrics": {
          "accuracy": {
            "mean": 80.0,
            "std": 0.9617692030835702
          },
          "coverage": {
            "mean": 82.8,
            "std": 1.055935604097146
          },
          "size": {
            "mean": 1.01,
            "std": 0.01581138830084191
          },
          "answer": {
            "mean": 89.8,
            "std": 1.4212670403551912
          },
          "selective": {
            "mean": 83.10671087591801,
            "std": 0.9044711344097208
          },
          "joint_error": {
            "mean": 15.16,
            "std": 0.5727128425310544
          },
          "views": {
            "mean": 2.0,
            "std": 0.0
          },
          "candidate_recall": {
            "mean": 95.4,
            "std": 0.29154759474226427
          }
        }
      },
      "Adaptive aligned": {
        "display_name": "Adaptive",
        "metrics": {
          "accuracy": {
            "mean": 76.58,
            "std": 1.0568822072492285
          },
          "coverage": {
            "mean": 88.16,
            "std": 0.7536577472566713
          },
          "size": {
            "mean": 1.342,
            "std": 0.0327108544675922
          },
          "answer": {
            "mean": 78.0,
            "std": 1.5033296378372938
          },
          "selective": {
            "mean": 85.88597696438153,
            "std": 0.7464117668251401
          },
          "joint_error": {
            "mean": 11.0,
            "std": 0.36742346141747684
          },
          "views": {
            "mean": 1.39,
            "std": 0.03999999999999994
          },
          "candidate_recall": {
            "mean": 95.4,
            "std": 0.29154759474226427
          },
          "simultaneous": {
            "mean": 83.4,
            "std": 0.8455767262643896
          },
          "count": {
            "mean": 66.97381470306614,
            "std": 3.0230947018881573
          },
          "direction": {
            "mean": 85.88232432529108,
            "std": 3.725933769544267
          },
          "nearest": {
            "mean": 77.06060606060606,
            "std": 1.712858516492433
          }
        }
      }
    }
  },
  "derived": {
    "alignment_gain_pp": 2.0,
    "acquisition_saving_percent": 46.8,
    "coverage_drop_pp": 8.540000000000006
  }
};
