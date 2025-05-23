# PhysReason: A Comprehensive Benchmark towards Physics-Based Reasoning
## Overview

PhysReason is a comprehensive physics-based reasoning benchmark consisting of 1,200 physics problems spanning multiple domains, with a focus on both knowledge-based (25%) and reasoning-based (75%) questions.

## Key Features

- **Dataset Size**: 1,200 problems
- **Problem Types**: Mix of knowledge (25%) and reasoning (75%) questions
- **Theorem Coverage**: 147 physics theorems
- **Visual Content**: 81% problems include diagrams
- **Difficulty Levels**: Knowledge, Easy, Medium, Hard

## Data Collection

- Sources: Global college entrance exams and competitions

- Process: Standardized using MinerU framework

- Quality Control: Two-phase translation with expert verification

- Filtering: Excluded easily searchable problems

- Classification: Based on solving time and theorem complexity

- ## Benchmark Comparison

  | Benchmark      | Multi-modal | Size | Knowledge | Question Type | Avg. T | Step-by-step | Avg. T | Avg. S |
  | -------------- | ----------- | ---- | --------- | ------------- | ------ | ------------ | ------ | ------ |
  | JEEBench       | ❌           | 123  | CEE       | OE,MC         | 169.7  | -            | -      | -      |
  | MMLU-Pro       | ❌           | 1299 | COL       | MC            | 52.1   | -            | -      | -      |
  | GPQA           | ❌           | 227  | PH.D.     | OE            | 111.4  | ❌            | 197.2  | 3.6    |
  | SciEval        | ❌           | 1657 | -         | OE,MC         | 154.5  | -            | -      | -      |
  | SciBench       | ✅           | 295  | COL       | OE            | 80.5   | ❌            | 315.9  | 2.8    |
  | MMMU           | ✅           | 443  | COL       | OE,MC         | 53.8   | -            | -      | -      |
  | ScienceQA      | ✅           | 617  | K1-K12    | MC            | 13.3   | ❌            | 63.0   | 2.4    |
  | OlympiadBench  | ✅           | 2334 | COMP      | OE            | 222.0  | ❌            | 199.8  | 3.7    |
  | EMMA           | ✅           | 156  | -         | MC            | 109.5  | -            | -      | -      |
  | Ours-Knowledge | ✅           | 300  | CEE+COMP  | OE            | 163.7  | ✅            | 196.5  | 3.3    |
  | Ours-Easy      | ✅           | 300  | CEE+COMP  | OE            | 171.2  | ✅            | 241.5  | 5.0    |
  | Ours-Medium    | ✅           | 300  | CEE+COMP  | OE            | 229.2  | ✅            | 391.3  | 8.4    |
  | Ours-Hard      | ✅           | 300  | CEE+COMP  | OE            | 340.9  | ✅            | 936.1  | 15.6   |
  | Ours-Full      | ✅           | 1200 | CEE+COMP  | OE            | 226.3  | ✅            | 441.3  | 8.1    |

  ## Evaluation Framework

  ### PSAS-A (Answer Level)

  - Evaluates sub-question answers
  - Uses LLM for answer extraction
  - Verifies semantic consistency
  - Weighted scoring based on solution steps

  ### PSAS-S (Step Level)

  - Four-phase assessment:
    1. Data extraction
    2. Scoring
    3. First error step detection
    4. Error analysis
   
### Core Evaluation Files
  - answer_evaluation_with_ds_ch_prompt.py: Answer-level evaluation using Chinese prompts for Deepseek models
  - answer_evaluation_with_ds_en_prompt.py: Answer-level evaluation using English prompts for Deepseek models
  - format_result_ds.py: Optimizes unstable outputs into stable, consistent formats
  - step_evaluation_with_ds_ch_prompt.py: Step-level evaluation using Chinese prompts for Deepseek models
  - step_evaluation_with_ds_en_prompt.py: Step-level evaluation using English prompts for Deepseek models

  ## Experimental Results

  ### Non-O-like Models Performance

  | Model             | Input | Knowledge   | Easy        | Medium      | Hard        | Avg.        |
  | ----------------- | ----- | ----------- | ----------- | ----------- | ----------- | ----------- |
  | Qwen2VL-72B       | Q, I  | 41.92/62.47 | 24.04/45.26 | 15.97/36.13 | 4.83/24.23  | 16.96/42.88 |
  | InternVL2.5-78B   | Q, I  | 28.34/64.71 | 24.16/50.69 | 17.72/38.56 | 9.71/25.95  | 19.98/45.89 |
  | GPT-4o            | Q, I  | 50.71/65.82 | 33.87/51.98 | 22.73/42.36 | 11.03/24.71 | 29.58/47.23 |
  | Deepseek-V3-671B  | Q, IC | 55.86/66.14 | 40.06/52.77 | 26.63/44.02 | 13.73/26.87 | 34.07/48.42 |
  | Claude-3.5-Sonnet | Q, I  | 54.14/66.45 | 41.35/55.85 | 28.14/44.86 | 15.11/28.51 | 34.69/49.88 |
  | Gemini-2.0-Flash  | Q, I  | 65.08/75.04 | 54.84/68.60 | 39.79/55.67 | 21.99/38.39 | 45.20/60.40 |
  | Gemini-2.0-Pro    | Q, I  | 67.99/79.01 | 55.43/71.47 | 44.29/57.74 | 23.81/42.66 | 47.88/62.74 |

  ### O-like Models Performance

  | Model         | Input | Knowledge   | Easy        | Medium      | Hard        | Avg.        |
  | ------------- | ----- | ----------- | ----------- | ----------- | ----------- | ----------- |
  | o1-mini       | Q, IC | 53.90/65.74 | 35.21/52.26 | 22.24/40.19 | 10.61/26.80 | 30.49/47.18 |
  | QvQ-72B       | Q, I  | 62.44/70.92 | 53.74/64.65 | 28.18/54.88 | 14.30/36.47 | 32.67/57.66 |
  | Gemini-2.0-T† | Q, I  | 65.35/77.20 | 51.89/67.49 | 44.43/58.95 | 27.14/45.48 | 47.20/63.07 |
  | QwQ-32B       | Q, IC | 62.03/76.28 | 54.92/71.08 | 43.64/62.14 | 22.99/42.19 | 45.89/63.87 |
  | GLM-Zero      | Q, IC | 64.95/80.36 | 54.11/71.54 | 41.32/63.67 | 23.04/47.46 | 46.52/65.76 |
  | o3-mini-high  | Q, IC | 70.67/83.61 | 67.20/81.95 | 45.31/64.57 | 30.12/47.23 | 53.32/69.34 |
  | Gemini-2.0-T* | Q, I  | 73.44/84.15 | 63.17/75.94 | 50.41/66.60 | 31.90/48.47 | 54.73/69.73 |
  | Deepseek-R1   | Q, IC | 75.11/85.91 | 65.08/79.81 | 54.84/72.02 | 31.95/51.50 | 56.75/73.26 |

  ### PhysReason-mini Results

  | Model         | K.    | E.    | M.    | H.    | Avg.  |
  | ------------- | ----- | ----- | ----- | ----- | ----- |
  | o1-mini       | 54.80 | 30.33 | 15.41 | 7.92  | 27.11 |
  | QvQ-72B       | 51.17 | 37.10 | 29.83 | 22.13 | 35.06 |
  | QwQ-32B       | 64.40 | 50.07 | 38.88 | 27.45 | 45.20 |
  | Gemini-2.0-T† | 71.47 | 49.97 | 36.83 | 22.97 | 45.42 |
  | GLM-Zero      | 72.70 | 50.17 | 43.42 | 24.70 | 47.75 |
  | o1            | 72.47 | 53.37 | 49.31 | 25.32 | 50.12 |
  | o3-mini-high  | 71.10 | 63.20 | 47.02 | 31.93 | 53.31 |
  | Gemini-2.0-T* | 76.33 | 56.87 | 51.85 | 32.61 | 54.42 |
  | Deepseek-R1   | 85.17 | 60.77 | 47.24 | 33.23 | 56.60 |

  ## Key Findings

  - Strong performance from O-like models
  - Gemini and Deepseek models show competitive results
  - Detailed error analysis through PSAS-S framework
  - Multi-modal capabilities enhance performance
  - Step-by-step evaluation provides deeper insights
