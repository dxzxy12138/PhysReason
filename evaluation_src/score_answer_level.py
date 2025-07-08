import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def calculate_weighted_scores(folder_path):
    eval_files = [
        'deepseek_ds.json',
        'deepseek_r1_ds.json',
        'gemini_output_ds.json',
        'gemini_thinking_output_ds.json',
        'gemini_thinking_output_v2_ds.json',
        'gpt_4o_ds.json',
        'internvl_output_ds.json',
        'o1_mini_ds.json',
        'qvq_output_ds.json',
        'qwq_output_ds.json',
        'qwen2vl_output_ds.json',
        'claude_ds.json',
        'glm_zero_ds.json',
        # 'gemini_pro_output_ds.json'
    ]
    
    model_scores = {
        model_name.replace('_ds', '').replace('.json', ''): {
            'knowledge': [], 'easy': [], 'medium': [], 'difficult': []
        } for model_name in eval_files
    }

    for subdir in os.listdir(folder_path):
        subdir_path = os.path.join(folder_path, subdir)
        if not os.path.isdir(subdir_path):
            continue

        with open(os.path.join(subdir_path, 'problem.json'), 'r', encoding='utf-8') as f:
            problem_data = json.load(f)
            steps = problem_data['explanation_steps']
            difficulty = problem_data['difficulty']

        weights = {}
        total_steps = 0
        sub_questions = []  # 保存子问题的顺序
        for sub_q, step_dict in steps.items():
            step_count = len(step_dict)
            weights[sub_q] = step_count
            total_steps += step_count
            sub_questions.append(sub_q)

        eval_dir = os.path.join(subdir_path, 'evaluation')
        for eval_file in eval_files:
            eval_path = os.path.join(eval_dir, eval_file)
            if not os.path.exists(eval_path):
                continue

            with open(eval_path, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)

            # 计算得分，考虑前序问题的正确性
            total_score = 0
            previous_correct = True  # 跟踪前序问题是否正确
            
            for sub_q in sub_questions:
                if not previous_correct:  # 如果前面有错误，后续题目都计0分
                    break
                    
                if sub_q in eval_data:
                    sub_data = eval_data[sub_q]
                    if isinstance(sub_data, str) and sub_data == "No errors found.":
                        sub_score = weights[sub_q]
                    elif isinstance(sub_data, dict):
                        sub_score = sub_data.get('score', 0) * weights[sub_q]
                        if sub_score == 0:  # 如果当前问题错误
                            previous_correct = False
                    else:
                        previous_correct = False
                        sub_score = 0
                    total_score += sub_score
                else:
                    previous_correct = False

            final_score = (total_score / total_steps) * 100
            model_name = eval_file.replace('_ds.json', '')
            model_scores[model_name][difficulty].append(final_score)

    # 计算并直接打印性能结果
    print("\nModel Performance Summary:")
    print("-" * 80)
    print(f"{'Model':<20} {'Knowledge':>10} {'Easy':>10} {'Medium':>10} {'Difficult':>10} {'Overall':>10}")
    print("-" * 80)
    
    final_scores = {}
    for model in model_scores:
        final_scores[model] = {
            difficulty: np.mean(scores) if scores else 0
            for difficulty, scores in model_scores[model].items()
        }
        
        # 计算总体平均分
        all_scores = []
        for difficulty in ['knowledge', 'easy', 'medium', 'difficult']:
            all_scores.extend(model_scores[model][difficulty])
        overall_score = np.mean(all_scores) if all_scores else 0
        
        # 打印每个模型的性能
        print(f"{model:<20} "
              f"{final_scores[model]['knowledge']:>10.2f} "
              f"{final_scores[model]['easy']:>10.2f} "
              f"{final_scores[model]['medium']:>10.2f} "
              f"{final_scores[model]['difficult']:>10.2f} "
              f"{overall_score:>10.2f}")

    print("-" * 80)
    return model_scores, final_scores

def visualize_and_save_results(model_scores, final_scores, save_path):
    results = []
    for model in model_scores:
        row = {'Model': model}
        overall_scores = []
        
        for difficulty in ['knowledge', 'easy', 'medium', 'difficult']:
            scores = model_scores[model][difficulty]
            avg_score = np.mean(scores) if scores else 0
            row[f'{difficulty}_score'] = round(avg_score, 2)
            row[f'{difficulty}_count'] = len(scores)
            overall_scores.extend(scores)
            
        row['overall_score'] = round(np.mean(overall_scores) if overall_scores else 0, 2)
        row['total_problems'] = len(overall_scores)
        results.append(row)
    
    df = pd.DataFrame(results)
    
    ensure_dir(save_path)
    df.to_excel(os.path.join(save_path, 'model_performance.xlsx'), index=False)
    
    plt.figure(figsize=(15, 8))
    difficulties = ['knowledge', 'easy', 'medium', 'difficult']
    bar_width = 0.15
    index = np.arange(len(results))
    
    for i, diff in enumerate(difficulties):
        scores = [row[f'{diff}_score'] for row in results]
        plt.bar(index + i*bar_width, scores, bar_width, label=diff.capitalize())
    
    overall_scores = [row['overall_score'] for row in results]
    plt.plot(index + bar_width*2, overall_scores, 'k-o', label='Overall')
    
    plt.xlabel('Models')
    plt.ylabel('Score (%)')
    plt.title('Model Performance by Difficulty')
    plt.xticks(index + bar_width*2, [row['Model'] for row in results], rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(save_path, 'performance_plot.png'))
    plt.close()


def main():
    input_folder = r"D:\ACL-2025\src\final_benchmark"
    output_folder = r"D:\ACL-2025\src\benchmark_result_analysis"
    
    model_scores, final_scores = calculate_weighted_scores(input_folder)
    visualize_and_save_results(model_scores, final_scores, output_folder)

if __name__ == "__main__":
    main()
