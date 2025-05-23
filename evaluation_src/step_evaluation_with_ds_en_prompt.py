import json
import re
import os
from typing import Dict, Any
from tqdm import tqdm
from openai import OpenAI
import time

def parse_deepseek_content(content: str, expected_sub_questions: list) -> Dict[str, Dict[str, Any]]:
    """Parse deepseek.txt content into hierarchical structure"""
    sub_q_pattern = re.compile(
        r'(sub_question_\d+)\s*:\s*(.*?)(?=(?:(?:\n|^)sub_question_\d+\s*:|$))',
        re.DOTALL
    )

    sub_questions = {}
    matches = re.findall(sub_q_pattern, content)

    # Create mapping of parsed sub-questions
    parsed_sub_qs = {sub_q_label: sub_q_block for sub_q_label, sub_q_block in matches}

    # Process all expected sub-questions
    for sub_q_label in expected_sub_questions:
        if sub_q_label in parsed_sub_qs:
            # Process existing sub-questions
            sub_q_block = parsed_sub_qs[sub_q_label]
            step_pattern = re.compile(
                r'(step_\d+)\s*:\s*(.*?)(?=(?:(?:\n|^)step_\d+\s*:|'
                + sub_q_label + r'_answer\s*:|$))',
                re.DOTALL
            )
            
            steps = {}
            for step_label, step_text in re.findall(step_pattern, sub_q_block):
                steps[step_label] = {
                    "content": step_text.strip()
                }

            answer_pattern = re.compile(
                rf'{sub_q_label}_answer\s*:\s*(.*?)(?=(?:(?:\n|^)sub_question_\d+\s*:|$))',
                re.DOTALL
            )
            answer_match = re.search(answer_pattern, sub_q_block)
            answer = answer_match.group(1).strip() if answer_match else ""

            sub_questions[sub_q_label] = {
                "steps": steps,
                "answer": answer,
                "is_complete": True
            }
        else:
            # Add missing sub-questions
            sub_questions[sub_q_label] = {
                "steps": {},
                "answer": "",
                "is_complete": False
            }

    return sub_questions


def evaluate_step_content(client, step_content, step_analysis, context, question, standard_step_content, pbar_eval):
    """Evaluate individual step content, analyzing all physical quantities point by point"""
    results = {
        'equation_correct': False,
        'value_correct': False,
        "miss_item": [],
        'error_kind': '',
        'error_analysis': ''
    }
    
    # Combine all physical quantity names into extraction prompt
    quantity_names = [q['name'] for q in step_analysis['result_quantity']]
    names_prompt = '\n'.join(f"- {name}" for name in quantity_names)

    try:
        # Extract relevant content
        extract_result_prompt = f"""Based on the following solution step content, please extract content related to the following physical quantities:
Problem context: {context}
Specific question: {question}
Physical quantities to extract:
{names_prompt}
Solution step content: {step_content}
Please only return the relevant result content, not related formulas, and do not add any explanations."""
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional physics problem analysis assistant."},
                {"role": "user", "content": extract_result_prompt},
            ],
            stream=False
        )
        
        extracted_result_content = response.choices[0].message.content.strip()
        # print(f"Extracted_result_content: {extracted_result_content}")
        pbar_eval.update(1)

        # Evaluate numerical result correctness
        # Extract values of all physical quantities
        values = [q['value'] for q in step_analysis['result_quantity']]
        # Check if all values are 'N/A'
        if all(value == 'N/A' for value in values):
            # print("All physical quantity values are 'N/A', skipping subsequent processing.")
            results['miss_item'].append("value_correct")
            # results['value_correct'] = None
        else:
            # Generate physical quantity description string
            values_str = '\n'.join([
                f"Physical quantity {i+1}: {q['name']}\nExpected result: {q['value']}"
                for i, q in enumerate(step_analysis['result_quantity'])
                if q['value'] != 'N/A'  # Only process physical quantities with values not 'N/A'
            ])
            # If values_str is not empty, proceed with subsequent processing
            if values_str:
                value_prompt = f"""Please judge whether the following results are equivalent:
Expected results:
{values_str}
Actual content:
{extracted_result_content}
Please judge all results individually. If any one is wrong, it's considered wrong. Only answer "true" or "false". If correct, no explanation needed. If incorrect, briefly explain in one or two sentences."""
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional physics calculation result evaluation assistant."},
                        {"role": "user", "content": value_prompt},
                    ],
                    stream=False
                )
                
                value_result = response.choices[0].message.content.strip()
                # print(f"Value result: {value_result}")
                # Check if result contains "correct"
                results['value_correct'] = 'true' in value_result.lower()
            pbar_eval.update(1)


        if results['value_correct'] == True:
            results['equation_correct'] = True
        else:
            extract_equation_prompt = f"""Based on the following solution step content, please extract content related to the following physical quantities:
Problem context: {context}
Specific question: {question}
Physical quantities to extract:
{names_prompt}
Solution step content: {step_content}
Return the relevant formulas for obtaining the required physical quantities
Please only return the relevant content, do not add any explanations."""
            # Extract relevant content
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a professional physics problem analysis assistant."},
                    {"role": "user", "content": extract_equation_prompt},
                ],
                stream=False
            )
            
            extract_equation_content = response.choices[0].message.content.strip()
            # print(f"Extract_equation_content: {extract_equation_content}")

            pbar_eval.update(1)
            equations = [q['equation'] for q in step_analysis['result_quantity']]
            # Check if all values are 'N/A'
            if all(equation == 'N/A' for equation in equations):
                # print("All physical quantity values are 'N/A', skipping subsequent processing.")
                results['miss_item'].append("equation_correct")
            else:
                # Evaluate formula correctness
                equations_str = '\n'.join([
                    f"Physical quantity {i+1}: {q['name']}\nExpected formula: {q['equation']}"
                    for i, q in enumerate(step_analysis['result_quantity'])
                    if q['equation'] != 'N/A'  # Only process physical quantities with values not 'N/A'
                ])
                if "N/A" not in equations_str:
                    equation_prompt = f"""Please judge whether the following physics formulas are equivalent, ignoring units:
Expected formulas:
{equations_str}
Actual content:
{extract_equation_content}
Please judge all formulas, only answer "true" or "false". If correct, no explanation needed. If incorrect, briefly explain in one or two sentences."""
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "You are a professional physics formula evaluation assistant."},
                            {"role": "user", "content": equation_prompt},
                        ],
                        stream=False
                    )
                    
                    equation_result = response.choices[0].message.content.strip()
                    # print(f"Equation result: {equation_result}")
                    results['equation_correct'] = 'true' in equation_result.lower()
            pbar_eval.update(1)

            # If there are errors, analyze error causes
            if not (results['equation_correct'] and results['value_correct']):

                error_analysis_prompt = f"""Please analyze the errors in the following solution steps:
Standard answer content:
{standard_step_content}
Actual content:
{extract_equation_content}
Please briefly explain the error cause in one or two sentences, answer in English
"""
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional physics problem error analysis assistant."},
                        {"role": "user", "content": error_analysis_prompt},
                    ],
                    stream=False
                )
                
                results['error_analysis'] = response.choices[0].message.content.strip()

                error_prompt = f"""Please analyze the errors in the following solution steps:
Standard answer content: {standard_step_content}
Actual content:
{extract_equation_content}
Error analysis: {results['error_analysis']}
Choose one error cause from the following:
Graphical Analysis Errors: 
Errors in understanding, drawing, analyzing, or extracting data from graphics. For example, misreading coordinate axes, misjudging curve trends, or missing key data points.

Physical Law Application Errors: 
Confusing physical law concepts or using them in inappropriate scenarios. For example, misusing the law of conservation of momentum or the law of conservation of energy.

Physical Condition Analysis Errors: 
Misjudgment of system boundaries, internal and external forces, or components. For example, ignoring friction or misjudging the isolation of the system.

Physical Process Understanding Errors: 
Deviations in the understanding of the development of phenomena, state changes, or causal relationships. For example, incorrect analysis of the motion process of an object or the mechanism of energy conversion.

Variable Relationship Errors: 
Misunderstanding of the dependency or functional relationship between physical quantities. For example, misunderstanding that acceleration is proportional to velocity.

Calculation Process Errors: 
Errors in mathematical operations, formula derivation, or substitution calculations. For example, algebraic operation errors or unit conversion errors.

Boundary Condition Analysis Errors: 
Ignoring or incorrectly handling special cases, limiting conditions, or ranges of applicability. For example, not considering system behavior at extreme temperatures or pressures.
Only return the error category, for example: Conceptual Errors
"""

                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional physics problem error analysis assistant."},
                        {"role": "user", "content": error_prompt},
                    ],
                    stream=False
                )
                
                results['error_kind'] = response.choices[0].message.content.strip()
                pbar_eval.update(1)

    except Exception as e:
        print(f"Evaluation error: {str(e)}")
        time.sleep(1)

    return results


def evaluate_with_deepseek(actual_answer, expected_answer, context, question_content, pbar_eval):
    """Evaluate whether the answer is correct"""
    client = OpenAI(api_key="your_api_key", base_url="https://api.deepseek.com")
    
    prompt = f"""Please judge whether the two answers are semantically equivalent based on the following information, ignoring units:
Specific question:
{question_content}
Actual answer:
{actual_answer}
Expected answer:
{expected_answer}
Please only answer "true" or "false" to indicate whether these two answers express the same meaning. When judging, please mainly consider whether details like mathematical expressions are equivalent, no need to consider units."""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional mathematics problem answer evaluation assistant."},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        
        result = response.choices[0].message.content.strip()
        pbar_eval.update(1)
        return 'true' in result.lower()
    except Exception as e:
        print(f"Evaluation error: {str(e)}")
        time.sleep(1)  # Add delay for retry
        return False


def evaluate_folder(folder_path: str):
    """Evaluate all problems in the folder"""
    results = {}
    client = OpenAI(api_key="your_api_key", base_url="https://api.deepseek.com")
    
    # Traverse all subfolders
    for subfolder in tqdm(os.listdir(folder_path), desc="Processing subfolders"):
        subfolder_path = os.path.join(folder_path, subfolder)
        if not os.path.isdir(subfolder_path):
            continue
        print("subfolder_path is", subfolder_path)
        
        # Read v8 problem file
        problem_path_v8 = os.path.join(subfolder_path, "problem.json")
        if not os.path.exists(problem_path_v8):
            continue

        evaluation_path = os.path.join(subfolder_path, "evaluation")
        os.makedirs(evaluation_path, exist_ok=True)
        deepseek_result_path = os.path.join(evaluation_path, "deepseek_ds.json")
        if os.path.exists(deepseek_result_path):
            print(f"{deepseek_result_path} already exists, skipping evaluation.")
            continue

        with open(problem_path_v8, 'r', encoding='utf-8') as f:
            problem_data_v8 = json.load(f)

        # Read evaluation files in txt folder
        txt_folder = os.path.join(subfolder_path, "txt")
        if not os.path.exists(txt_folder):
            continue

        # Find deepseek.txt file
        deepseek_path = os.path.join(txt_folder, "deepseek_ds.txt")
        if not os.path.exists(deepseek_path):
            continue
        # print("deepseek_path is", deepseek_path)
        
        
        with open(deepseek_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get expected sub-question list
        expected_sub_questions = [f"sub_question_{i+1}" for i in range(len(problem_data_v8['answer']))]

        # Parse deepseek.txt content
        parsed_content = parse_deepseek_content(content, expected_sub_questions)
        
        # Evaluation results
        txt_results = {}
        
        # Establish step mapping for each sub-question
        sub_q_step_mapping = {}
        current_step = 1

        # Traverse each sub-question in explanation_steps
        for sub_q_key in problem_data_v8['explanation_steps'].keys():
            # Get number of steps in current sub-question
            steps_in_sub_q = len(problem_data_v8['explanation_steps'][sub_q_key])
            
            # Update sub_q_step_mapping
            sub_q_step_mapping[sub_q_key] = {
                'start_step': current_step,
                'end_step': current_step + steps_in_sub_q - 1
            }
            
            # Update current_step to the starting step of next sub-question
            current_step += steps_in_sub_q

        
        with tqdm(total=len(problem_data_v8['answer']), desc=f"Evaluating deepseek_r1.txt") as pbar_eval:
            for i, (sub_q_key, sub_q_data) in enumerate(parsed_content.items()):
                expected_answer = problem_data_v8['answer'][i]
                actual_answer = sub_q_data['answer']
                
                # First evaluate overall answer
                is_correct = evaluate_with_deepseek(
                    actual_answer,
                    expected_answer,
                    problem_data_v8['question_structure']['context'],
                    problem_data_v8['question_structure'][sub_q_key],
                    pbar_eval
                )
                print(f"{sub_q_key} answer is_correct: {is_correct}")
                
                if is_correct:
                    # If answer is correct, give full score directly
                    txt_results[sub_q_key] = {
                        'score': 1.0,
                        'steps': {}
                    }
                else:
                    # If answer is incorrect, start evaluating from the first step of this sub-question
                    step_scores = {}
                    steps_analysis = problem_data_v8['steps_analysis']
                    
                    # Get step range for this sub-question
                    start_step = sub_q_step_mapping[sub_q_key]['start_step']
                    end_step = sub_q_step_mapping[sub_q_key]['end_step']
                    
                    # Merge all step content for this sub-question in deepseek.txt
                    deepseek_steps_content = "\n".join([
                        step_data['content'] 
                        for step_data in sub_q_data['steps'].values()
                    ])

                    # Traverse steps corresponding to this sub-question
                    for step_num in range(start_step, end_step + 1):
                        step_key = f"step_{step_num}"
                        if step_key in steps_analysis:
                            step_analysis = steps_analysis[step_key]
                            
                            # Find matches in merged content
                            step_results = evaluate_step_content(
                                client,
                                deepseek_steps_content,  # Use merged content
                                step_analysis,
                                problem_data_v8['question_structure']['context'],
                                problem_data_v8['question_structure'][sub_q_key],
                                problem_data_v8['explanation_steps'][sub_q_key][step_key],
                                pbar_eval
                            )
                            
                            # Calculate step score
                            step_score = 0.0
                            if step_results['equation_correct']:
                                step_score += 0.5
                            if step_results['value_correct']:
                                step_score += 0.5
                                
                            step_scores[step_key] = {
                                'score': step_score,
                                'analysis': step_results
                            }

                    # Calculate total score (use average score of steps in this sub-question)
                    total_steps = end_step - start_step + 1
                    total_score = sum(s['score'] for s in step_scores.values()) / total_steps if total_steps > 0 else 0.0
                    
                    txt_results[sub_q_key] = {
                        'score': total_score,
                        'steps': step_scores
                    }

        # Save evaluation results
        with open(deepseek_result_path, 'w', encoding='utf-8') as f:
            json.dump(txt_results, f, indent=4)
        print(f"Evaluation results saved to: {deepseek_result_path}")
        results[subfolder] = txt_results
        # break
    
    return results

# Usage example
folder_path = r"C:\Users\13938\Desktop\ACL-2025\src\final_benchmark"
results = evaluate_folder(folder_path)