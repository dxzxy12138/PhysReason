import os
from openai import OpenAI
import json
from tqdm import tqdm
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import random

TARGET_FILES = {
    'deepseek_r1.txt', 
}

API_KEYS = [
    "you_api_keys_list"
]

thread_local = threading.local()
api_key_lock = threading.Lock()
current_api_key_index = 0
processed_count = 0
total_count = 0
count_lock = threading.Lock()

def get_next_api_key():
    global current_api_key_index
    with api_key_lock:
        api_key = API_KEYS[current_api_key_index]
        current_api_key_index = (current_api_key_index + 1) % len(API_KEYS)
        return api_key

def get_client():
    if not hasattr(thread_local, 'client'):
        api_key = get_next_api_key()
        thread_local.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
    return thread_local.client

def retry_with_new_key(func):
    def wrapper(*args, **kwargs):
        max_retries = len(API_KEYS)
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt < max_retries - 1:
                    tqdm.write(f"\nRetrying with new API key. Error: {str(e)}")
                    api_key = get_next_api_key()
                    thread_local.client = OpenAI(
                        api_key=api_key,
                        base_url="https://api.deepseek.com"
                    )
                    time.sleep(1)
                else:
                    raise e
    return wrapper

def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

@retry_with_new_key
def process_with_deepseek(content, problem_structure):
    client = get_client()
    
    prompt = f"""
Given the following problem structure:
{json.dumps(problem_structure, indent=2)}

Please restructure the following content into this format:
sub_question_1:
step_1: [reasoning step]
step_2: [reasoning step]
...
sub_question_1_answer: [final answer]
sub_question_2:
step_3: [reasoning step]
step_4: [reasoning step]
...
sub_question_2_answer: [final answer]

sub_question_3:
step_5: [reasoning step]
...
sub_question_3_answer: [final answer]
The step sequences of different sub_questions should be continuous.
Do not return other content.
Content to restructure:
{content}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    
    return response.choices[0].message.content

def process_single_file(args):
    global processed_count
    problem_path, file, problem_structure, main_pbar = args
    
    try:
        input_path = os.path.join(problem_path, 'result', file)
        txt_folder = os.path.join(problem_path, 'txt')
        if not os.path.exists(txt_folder):
            os.makedirs(txt_folder)
            
        filename_without_ext = os.path.splitext(file)[0]
        new_filename = f"{filename_without_ext}_ds.txt"
        output_path = os.path.join(txt_folder, new_filename)
        
        if os.path.exists(output_path):
            with count_lock:
                processed_count += 1
                print(f"\rProcessed: {processed_count}/{total_count} files ({(processed_count/total_count)*100:.2f}%)", end="")
            main_pbar.update(1)
            return True
            
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        processed_content = process_with_deepseek(content, problem_structure)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed_content)
        
        with count_lock:
            processed_count += 1
            print(f"\rProcessed: {processed_count}/{total_count} files ({(processed_count/total_count)*100:.2f}%)", end="")
            
        main_pbar.update(1)
        return True
        
    except Exception as e:
        tqdm.write(f"\nError processing {input_path}: {str(e)}")
        main_pbar.update(1)
        return False

def count_total_files(base_path):
    with tqdm(os.listdir(base_path), desc="Counting files", unit="dir") as pbar:
        total = 0
        for problem_dir in pbar:
            if problem_dir.startswith('cal_problem_'):
                problem_path = os.path.join(base_path, problem_dir)
                if os.path.isdir(problem_path):
                    total += len([f for f in os.listdir(os.path.join(problem_path, 'result')) if f in TARGET_FILES])
        return total

def process_files(base_path):
    global total_count
    print("Counting total files to process...")
    total_count = count_total_files(base_path)
    tasks = []
    
    with tqdm(total=total_count, desc="Overall progress", unit="file", position=0) as main_pbar:
        for problem_dir in tqdm(os.listdir(base_path), desc="Collecting tasks", unit="dir", position=1, leave=False):
            if not problem_dir.startswith('cal_problem_'):
                continue
                
            problem_path = os.path.join(base_path, problem_dir)
            if not os.path.isdir(problem_path):
                continue
            
            json_path = os.path.join(problem_path, 'problem.json')
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    problem_data = json.load(f)
                    problem_structure = problem_data["question_structure"]
            except Exception as e:
                tqdm.write(f"\nError reading json file {json_path}: {str(e)}")
                continue
            
            for file in os.listdir(os.path.join(problem_path, "result")):
                if file in TARGET_FILES:
                    tasks.append((problem_path, file, problem_structure, main_pbar))
        
        with ThreadPoolExecutor(max_workers=len(API_KEYS)) as executor:
            random.shuffle(tasks)
            list(tqdm(
                executor.map(process_single_file, tasks),
                total=len(tasks),
                desc="Processing files",
                unit="file",
                position=2,
                leave=False
            ))

def main():
    base_path = r"C:\Users\13938\Desktop\ACL-2025\src\final_benchmark"
    
    print("Starting file processing...")
    print(f"Target files to process: {', '.join(TARGET_FILES)}")
    print(f"Using {len(API_KEYS)} API keys with {len(API_KEYS)} concurrent workers")
    
    start_time = time.time()
    process_files(base_path)
    elapsed_time = time.time() - start_time
    
    print(f"\nProcessing completed in {elapsed_time:.2f} seconds")
    print(f"Total files processed: {processed_count}/{total_count}")

if __name__ == "__main__":
    main()