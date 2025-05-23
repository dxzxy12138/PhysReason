import os
import json
import re
import time
from openai import OpenAI
from collections import defaultdict
from tqdm import tqdm
import sys

MODEL_FILES = {
    'deepseek_r1.txt': ('evaluation_deepseek_r1_ds.json', 'deepseek_r1')
}

def create_client():
    client = OpenAI(
        base_url="https://api.deepseek.com",
        api_key="your_api_key",
    )
    return client

def find_files_to_process(base_path):
    """返回需要处理的文件列表，格式为: [(problem_dir, input_file_path, output_file_path, model_name)]"""
    files_to_process = []
    total_files = 0
    skipped_files = 0
    
    for problem_dir in os.listdir(base_path):
        problem_path = os.path.join(base_path, problem_dir)
        if not os.path.isdir(problem_path):
            continue
            
        result_dir = os.path.join(problem_path, 'result')
        score_dir = os.path.join(problem_path, 'score')
        
        if not os.path.exists(result_dir):
            continue
            
        if not os.path.exists(score_dir):
            os.makedirs(score_dir)
            
        if not os.path.exists(os.path.join(problem_path, 'problem.json')):
            continue
            
        for input_file, (output_file, model_name) in MODEL_FILES.items():
            input_path = os.path.join(result_dir, input_file)
            output_path = os.path.join(score_dir, output_file)
            
            if os.path.exists(input_path):
                total_files += 1
                if os.path.exists(output_path):
                    skipped_files += 1
                    continue
                files_to_process.append((problem_path, input_path, output_path, model_name))
                
    return files_to_process, total_files, skipped_files

def extract_answer_with_retry(content, question_content, sub_q_num, max_retries=3):
    """Extract answer with retry mechanism"""
    for attempt in range(max_retries):
        try:
            client = create_client()
            prompt = f"""请从以下输出文本中提取针对特定问题的答案。
具体问题：
{question_content}

输出文本：
{content}

请直接返回答案，不需要任何解释或额外文字。答案通常在'sub_question_{sub_q_num}_answer:'后面。"""

            response = client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的答案提取助手，请只返回提取到的答案，不要添加任何额外的解释。"},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )
            
            extracted_answer = response.choices[0].message.content.strip()
            return re.sub(r'sub_question_\d+_answer:', '', extracted_answer).strip()
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to extract answer after {max_retries} attempts: {str(e)}")
                return ""
            time.sleep(1)  # Wait before retry

def evaluate_with_deepseek(actual_answer, expected_answer, question_content):
    client = create_client()
    
    prompt = f"""请基于以下信息，判断两个答案是否在含义上等价：
具体问题：
{question_content}
实际回答：
{actual_answer}
预期回答：
{expected_answer}
请只回答"正确"或"错误"来表示这两个答案是否表达相同的含义。评判时请考虑数学表达式、单位等细节是否等价。"""

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个专业的数学问题答案评估助手"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    
    return response.choices[0].message.content.strip() == '正确'

def process_files(files_to_process):
    stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    with tqdm(total=len(files_to_process), desc="处理文件") as pbar:
        for problem_path, input_path, output_path, model_name in files_to_process:
            try:
                # 读取问题数据
                with open(os.path.join(problem_path, 'problem.json'), 'r', encoding='utf-8') as f:
                    problem_data = json.load(f)
                
                # 读取答案文件
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                sub_questions_count = len(problem_data["answer"])
                evaluation_results = {model_name: {}}
                
                difficulty = problem_data["difficulty"]
                context = problem_data["question_structure"]["context"]
                
                # 处理每个子问题
                for sub_q_num in range(1, sub_questions_count + 1):
                    sub_q_key = f"sub_question_{sub_q_num}"
                    expected_answer = problem_data["answer"][sub_q_num - 1]
                    question_content = problem_data["question_structure"][sub_q_key]
                    
                    # 使用新的答案提取方法
                    actual_answer = extract_answer_with_retry(content, question_content, sub_q_num)
                    
                    is_correct = evaluate_with_deepseek(
                        actual_answer, 
                        expected_answer,
                        question_content
                    ) if actual_answer else False
                    
                    stats[difficulty]['total'] += 1
                    if is_correct:
                        stats[difficulty]['correct'] += 1
                    
                    evaluation_results[model_name][sub_q_key] = {
                        "correct": is_correct,
                        "actual_answer": actual_answer,
                        "expected_answer": expected_answer,
                        "context": context,
                        "question_content": question_content,
                        "difficulty": difficulty
                    }
                
                # 保存评估结果
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(evaluation_results, f, indent=4, ensure_ascii=False)
                [print(f"Saved evaluation results to {output_path}")]
                
            except Exception as e:
                print(f"\nError processing {input_path}: {str(e)}")
                continue
            
            finally:
                pbar.update(1)
    
    return stats

def main():
    base_path = r"C:\Users\13938\Desktop\ACL-2025\src\final_benchmark"
    print(f"Starting processing in {base_path}...")
    
    try:
        # 找出需要处理的文件
        files_to_process, total_files, skipped_files = find_files_to_process(base_path)
        print(f"总共发现 {total_files} 个文件")
        print(f"其中 {skipped_files} 个文件已处理（跳过）")
        print(f"需要处理 {len(files_to_process)} 个文件")
        
        if not files_to_process:
            print("没有需要处理的文件")
            return
        
        # 处理文件并收集统计信息
        stats = process_files(files_to_process)
        
        # 打印统计信息
        print("\nFinal Statistics:")
        for difficulty, results in stats.items():
            accuracy = (results['correct'] / results['total'] * 100) if results['total'] > 0 else 0
            print(f"{difficulty.capitalize()}: {results['correct']}/{results['total']} correct ({accuracy:.1f}%)")
            
    except Exception as e:
        print(f"\nError occurred: {str(e)}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()