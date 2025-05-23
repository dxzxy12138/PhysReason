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
    """Returns a list of files to process, format: [(problem_dir, input_file_path, output_file_path, model_name)]"""
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
            prompt = f"""Please extract the answer for the specific question from the following output text.
Specific question:
{question_content}

Output text:
{content}

Please return the answer directly without any explanation or additional text. The answer is usually after 'sub_question_{sub_q_num}_answer:'."""

            response = client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional answer extraction assistant. Please only return the extracted answer without adding any additional explanations."},
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
    
    prompt = f"""Based on the following information, please determine whether the two answers are semantically equivalent:
Specific question:
{question_content}
Actual answer:
{actual_answer}
Expected answer:
{expected_answer}
Please only answer "true" or "false" to indicate whether these two answers express the same meaning. When evaluating, please consider whether mathematical expressions, units, and other details are equivalent."""

    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a professional mathematical problem answer evaluation assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    
    return response.choices[0].message.content.strip().lower() == 'true'

def process_files(files_to_process):
    stats = defaultdict(lambda: {'correct': 0, 'total': 0})
    
    with tqdm(total=len(files_to_process), desc="Processing files") as pbar:
        for problem_path, input_path, output_path, model_name in files_to_process:
            try:
                # Read problem data
                with open(os.path.join(problem_path, 'problem.json'), 'r', encoding='utf-8') as f:
                    problem_data = json.load(f)
                
                # Read answer file
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                sub_questions_count = len(problem_data["answer"])
                evaluation_results = {model_name: {}}
                
                difficulty = problem_data["difficulty"]
                context = problem_data["question_structure"]["context"]
                
                # Process each sub-question
                for sub_q_num in range(1, sub_questions_count + 1):
                    sub_q_key = f"sub_question_{sub_q_num}"
                    expected_answer = problem_data["answer"][sub_q_num - 1]
                    question_content = problem_data["question_structure"][sub_q_key]
                    
                    # Use new answer extraction method
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
                
                # Save evaluation results
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(evaluation_results, f, indent=4, ensure_ascii=False)
                print(f"Saved evaluation results to {output_path}")
                
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
        # Find files to process
        files_to_process, total_files, skipped_files = find_files_to_process(base_path)
        print(f"Total files found: {total_files}")
        print(f"Files already processed (skipped): {skipped_files}")
        print(f"Files to process: {len(files_to_process)}")
        
        if not files_to_process:
            print("No files need to be processed")
            return
        
        # Process files and collect statistics
        stats = process_files(files_to_process)
        
        # Print statistics
        print("\nFinal Statistics:")
        for difficulty, results in stats.items():
            accuracy = (results['correct'] / results['total'] * 100) if results['total'] > 0 else 0
            print(f"{difficulty.capitalize()}: {results['correct']}/{results['total']} correct ({accuracy:.1f}%)")
            
    except Exception as e:
        print(f"\nError occurred: {str(e)}", file=sys.stderr)
        raise

if __name__ == "__main__":
    main()