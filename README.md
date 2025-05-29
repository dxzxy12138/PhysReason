# PhysReason: A Comprehensive Benchmark towards Physics-Based Reasoning

[![arXiv](https://img.shields.io/badge/arXiv-2502.12054-b31b1b.svg)](https://arxiv.org/abs/2502.12054)
[![Dataset](https://img.shields.io/badge/🤗%20Hugging%20Face-Dataset-yellow)](https://huggingface.co/datasets/zhibei1204/PhysReason)
[![Project Page](https://img.shields.io/badge/🌐%20Project-Page-blue)](https://dxzxy12138.github.io/PhysReason/)

> **PhysReason is accepted by ACL-2025-main**

## 📋 Overview

PhysReason is a comprehensive physics-based reasoning benchmark consisting of **1,200 physics problems** spanning multiple domains, with a focus on both knowledge-based (25%) and reasoning-based (75%) questions. This benchmark addresses the critical gap in evaluating large language models' capabilities in physics-based reasoning, which requires applying physics theorems and constraints in complex problem-solving scenarios.

## ✨ Key Features

- **📊 Dataset Size**: 1,200 carefully curated physics problems
- **🎯 Problem Types**: Strategic mix of knowledge-based (25%) and reasoning-based (75%) questions
- **📚 Theorem Coverage**: Comprehensive coverage of 147 physics theorems
- **🎨 Visual Content**: 81% of problems include diagrams and visual elements
- **📈 Difficulty Levels**: Four distinct levels - Knowledge, Easy, Medium, Hard
- **🔄 Step-by-step Solutions**: Average of 8.1 solution steps per problem (15.6 for hard problems)
- **🌍 Multi-modal**: Supports both text and image inputs

## 🔧 Data Collection

Our rigorous data collection process ensures high-quality, challenging problems:

- **📖 Sources**: Global college entrance exams and international physics competitions
- **⚙️ Process**: Standardized using MinerU framework for consistent formatting
- **✅ Quality Control**: Two-phase translation process with expert verification
- **🔍 Filtering**: Systematically excluded easily searchable problems to prevent data leakage
- **📊 Classification**: Difficulty levels based on solving time and theorem complexity analysis

## 📊 Benchmark Comparison

| Benchmark      | Multi-modal | Size | Knowledge | Question Type | Avg. T | Step-by-step | Avg. T | Avg. S |
|----------------|-------------|------|-----------|---------------|--------|--------------|--------|--------|
| JEEBench       | ❌          | 123  | CEE       | OE,MC         | 169.7  | -            | -      | -      |
| MMLU-Pro       | ❌          | 1299 | COL       | MC            | 52.1   | -            | -      | -      |
| GPQA           | ❌          | 227  | PH.D.     | OE            | 111.4  | ❌           | 197.2  | 3.6    |
| SciEval        | ❌          | 1657 | -         | OE,MC         | 154.5  | -            | -      | -      |
| SciBench       | ✅          | 295  | COL       | OE            | 80.5   | ❌           | 315.9  | 2.8    |
| MMMU           | ✅          | 443  | COL       | OE,MC         | 53.8   | -            | -      | -      |
| ScienceQA      | ✅          | 617  | K1-K12    | MC            | 13.3   | ❌           | 63.0   | 2.4    |
| OlympiadBench  | ✅          | 2334 | COMP      | OE            | 222.0  | ❌           | 199.8  | 3.7    |
| EMMA           | ✅          | 156  | -         | MC            | 109.5  | -            | -      | -      |
| **Ours-Knowledge** | ✅      | 300  | CEE+COMP  | OE            | 163.7  | ✅           | 196.5  | 3.3    |
| **Ours-Easy**      | ✅      | 300  | CEE+COMP  | OE            | 171.2  | ✅           | 241.5  | 5.0    |
| **Ours-Medium**    | ✅      | 300  | CEE+COMP  | OE            | 229.2  | ✅           | 391.3  | 8.4    |
| **Ours-Hard**      | ✅      | 300  | CEE+COMP  | OE            | 340.9  | ✅           | 936.1  | 15.6   |
| **Ours-Full**      | ✅      | 1200 | CEE+COMP  | OE            | 226.3  | ✅           | 441.3  | 8.1    |

## 🔍 Evaluation Framework

We introduce the **Physics Solution Auto Scoring (PSAS)** framework with two complementary evaluation approaches:

### PSAS-A (Answer Level Evaluation)
- **Sub-question Assessment**: Evaluates answers for each sub-question independently
- **LLM-based Extraction**: Uses advanced language models for answer extraction
- **Semantic Verification**: Ensures semantic consistency between extracted and ground truth answers
- **Weighted Scoring**: Considers solution step lengths as weights for different sub-questions

### PSAS-S (Step Level Evaluation)
Provides detailed step-by-step assessment through four phases:
1. **Data Extraction**: Parses model responses and reference solutions
2. **Scoring**: Evaluates correctness of each reasoning step
3. **First Error Detection**: Identifies where models first deviate from correct reasoning
4. **Error Analysis**: Classifies error types into four key bottlenecks:
   - Physics Theorem Application
   - Physics Process Understanding  
   - Calculation
   - Physics Condition Analysis

## 🚀 Usage

### Core Evaluation Files
- `answer_evaluation_with_ds_ch_prompt.py`: Answer-level evaluation using Chinese prompts
- `answer_evaluation_with_ds_en_prompt.py`: Answer-level evaluation using English prompts  
- `format_result_ds.py`: Optimizes unstable outputs into stable, consistent formats
- `step_evaluation_with_ds_ch_prompt.py`: Step-level evaluation using Chinese prompts
- `step_evaluation_with_ds_en_prompt.py`: Step-level evaluation using English prompts

## 📈 Experimental Results

### Non-O-like Models Performance

| Model             | Input | Knowledge   | Easy        | Medium      | Hard        | Avg.        |
|-------------------|-------|-------------|-------------|-------------|-------------|-------------|
| Qwen2VL-72B       | Q, I  | 41.92/62.47 | 24.04/45.26 | 15.97/36.13 | 4.83/24.23  | 16.96/42.88 |
| InternVL2.5-78B   | Q, I  | 28.34/64.71 | 24.16/50.69 | 17.72/38.56 | 9.71/25.95  | 19.98/45.89 |
| GPT-4o            | Q, I  | 50.71/65.82 | 33.87/51.98 | 22.73/42.36 | 11.03/24.71 | 29.58/47.23 |
| Deepseek-V3-671B  | Q, IC | 55.86/66.14 | 40.06/52.77 | 26.63/44.02 | 13.73/26.87 | 34.07/48.42 |
| Claude-3.5-Sonnet | Q, I  | 54.14/66.45 | 41.35/55.85 | 28.14/44.86 | 15.11/28.51 | 34.69/49.88 |
| Gemini-2.0-Flash  | Q, I  | 65.08/75.04 | 54.84/68.60 | 39.79/55.67 | 21.99/38.39 | 45.20/60.40 |
| Gemini-2.0-Pro    | Q, I  | 67.99/79.01 | 55.43/71.47 | 44.29/57.74 | 23.81/42.66 | 47.88/62.74 |

### O-like Models Performance

| Model                              | Input | Knowledge   | Easy        | Medium      | Hard        | Avg.        |
|------------------------------------|-------|-------------|-------------|-------------|-------------|-------------|
| o1-mini                           | Q, IC | 53.90/65.74 | 35.21/52.26 | 22.24/40.19 | 10.61/26.80 | 30.49/47.18 |
| QvQ-72B                           | Q, I  | 62.44/70.92 | 53.74/64.65 | 28.18/54.88 | 14.30/36.47 | 32.67/57.66 |
| Gemini-2.0-Flash-Thinking-1206   | Q, I  | 65.35/77.20 | 51.89/67.49 | 44.43/58.95 | 27.14/45.48 | 47.20/63.07 |
| QwQ-32B                           | Q, IC | 62.03/76.28 | 54.92/71.08 | 43.64/62.14 | 22.99/42.19 | 45.89/63.87 |
| GLM-Zero                          | Q, IC | 64.95/80.36 | 54.11/71.54 | 41.32/63.67 | 23.04/47.46 | 46.52/65.76 |
| o3-mini-high                      | Q, IC | 70.67/83.61 | 67.20/81.95 | 45.31/64.57 | 30.12/47.23 | 53.32/69.34 |
| Gemini-2.0-Flash-Thinking-0121   | Q, I  | 73.44/84.15 | 63.17/75.94 | 50.41/66.60 | 31.90/48.47 | 54.73/69.73 |
| **Deepseek-R1**                  | Q, IC | **75.11/85.91** | **65.08/79.81** | **54.84/72.02** | **31.95/51.50** | **56.75/73.26** |

### PhysReason-mini Results

| Model                              | K.    | E.    | M.    | H.    | Avg.  |
|------------------------------------|-------|-------|-------|-------|-------|
| o1-mini                           | 54.80 | 30.33 | 15.41 | 7.92  | 27.11 |
| QvQ-72B                           | 51.17 | 37.10 | 29.83 | 22.13 | 35.06 |
| QwQ-32B                           | 64.40 | 50.07 | 38.88 | 27.45 | 45.20 |
| Gemini-2.0-Flash-Thinking-1206   | 71.47 | 49.97 | 36.83 | 22.97 | 45.42 |
| GLM-Zero                          | 72.70 | 50.17 | 43.42 | 24.70 | 47.75 |
| o1                                | 72.47 | 53.37 | 49.31 | 25.32 | 50.12 |
| o3-mini-high                      | 71.10 | 63.20 | 47.02 | 31.93 | 53.31 |
| Gemini-2.0-Flash-Thinking-0121   | 76.33 | 56.87 | 51.85 | 32.61 | 54.42 |
| **Deepseek-R1**                  | **85.17** | **60.77** | **47.24** | **33.23** | **56.60** |

## 🔑 Key Findings

- **Performance Gap**: Even top-performing models achieve less than 60% on answer-level evaluation
- **Difficulty Scaling**: Performance drops significantly from knowledge questions (75.11%) to hard problems (31.95%)
- **O-like Model Advantage**: Models with enhanced reasoning capabilities show superior performance
- **Multi-modal Benefits**: Visual content significantly enhances model understanding and performance
- **Four Critical Bottlenecks** identified through step-level evaluation:
  1. **Physics Theorem Application**
  2. **Physics Process Understanding**
  3. **Calculation Accuracy**
  4. **Physics Condition Analysis**

## 📝 Citation

If you find PhysReason useful in your research, please cite our paper:

```bibtex
@article{zhang2025physreason,
  title={Physreason: A comprehensive benchmark towards physics-based reasoning},
  author={Zhang, Xinyu and Dong, Yuxuan and Wu, Yanrui and Huang, Jiaxing and Jia, Chengyou and Fernando, Basura and Shou, Mike Zheng and Zhang, Lingling and Liu, Jun},
  journal={arXiv preprint arXiv:2502.12054},
  year={2025}
}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

We welcome contributions to PhysReason! Please contact us for more details.

---

**🔗 Quick Links:**
- [📄 Paper](https://arxiv.org/abs/2502.12054)
- [🤗 Dataset](https://huggingface.co/datasets/zhibei1204/PhysReason)
- [🌐 Project Page](https://dxzxy12138.github.io/PhysReason/)
- [💻 GitHub Repository](https://github.com/dxzxy12138/PhysReason)
