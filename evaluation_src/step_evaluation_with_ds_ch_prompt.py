import json
import re
import os
from typing import Dict, Any
from tqdm import tqdm
from openai import OpenAI
import time

def parse_deepseek_content(content: str, expected_sub_questions: list) -> Dict[str, Dict[str, Any]]:
    """解析 deepseek.txt 内容为层级结构"""
    sub_q_pattern = re.compile(
        r'(sub_question_\d+)\s*:\s*(.*?)(?=(?:(?:\n|^)sub_question_\d+\s*:|$))',
        re.DOTALL
    )

    sub_questions = {}
    matches = re.findall(sub_q_pattern, content)

    # 创建已解析子问题的映射
    parsed_sub_qs = {sub_q_label: sub_q_block for sub_q_label, sub_q_block in matches}

    # 处理所有预期的子问题
    for sub_q_label in expected_sub_questions:
        if sub_q_label in parsed_sub_qs:
            # 处理存在的子问题
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
            # 添加缺失的子问题
            sub_questions[sub_q_label] = {
                "steps": {},
                "answer": "",
                "is_complete": False
            }

    return sub_questions


def evaluate_step_content(client, step_content, step_analysis, context, question, standard_step_content, pbar_eval):
    """评估单个步骤的内容，分点分析所有物理量"""
    results = {
        'equation_correct': False,
        'value_correct': False,
        "miss_item": [],
        'error_kind': '',
        'error_analysis': ''
    }
    
    # 将所有物理量的名称合并成提取提示
    quantity_names = [q['name'] for q in step_analysis['result_quantity']]
    names_prompt = '\n'.join(f"- {name}" for name in quantity_names)

    try:
        # 提取相关内容
        extract_result_prompt = f"""基于以下解题步骤内容，请提取与以下物理量相关的内容：
问题背景：{context}
具体问题：{question}
需要提取的物理量：
{names_prompt}
解题步骤内容：{step_content}
请只返回相关的结果内容，不要相关公式，不要添加任何解释。"""
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的物理问题分析助手"},
                {"role": "user", "content": extract_result_prompt},
            ],
            stream=False
        )
        
        extracted_result_content = response.choices[0].message.content.strip()
        # print(f"Extracted_result_content: {extracted_result_content}")
        pbar_eval.update(1)

        # 评估数值结果正确性
        # 提取所有物理量的值
        values = [q['value'] for q in step_analysis['result_quantity']]
        # 检查是否所有值都是 'N/A'
        if all(value == 'N/A' for value in values):
            # print("所有物理量的值都是 'N/A'，跳过后续处理。")
            results['miss_item'].append("value_correct")
            # results['value_correct'] = None
        else:
            # 生成物理量描述字符串
            values_str = '\n'.join([
                f"物理量 {i+1}：{q['name']}\n预期结果：{q['value']}"
                for i, q in enumerate(step_analysis['result_quantity'])
                if q['value'] != 'N/A'  # 只处理值不为 'N/A' 的物理量
            ])
            # 如果 values_str 不为空，则进行后续处理
            if values_str:
                value_prompt = f"""请判断以下结果是否等价：
预期结果：
{values_str}
实际内容：
{extracted_result_content}
请逐个判断所有结果，有一次错误的也是错误，只回答"正确"或"错误"。如果正确不用解释，如果有错误也用一两句话简单说明一下。"""
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的物理计算结果评估助手"},
                        {"role": "user", "content": value_prompt},
                    ],
                    stream=False
                )
                
                value_result = response.choices[0].message.content.strip()
                # print(f"Value result: {value_result}")
                # 判断结果中是否包含“正确”
                results['value_correct'] = '正确' in value_result
            pbar_eval.update(1)


        if results['value_correct'] == True:
            results['equation_correct'] = True
        else:
            extract_equation_prompt = f"""基于以下解题步骤内容，请提取与以下物理量相关的内容：
问题背景：{context}
具体问题：{question}
需要提取的物理量：
{names_prompt}
解题步骤内容：{step_content}
返回得到所要求物理量的相关公式
请只返回相关的内容，不要添加任何解释。"""
            # 提取相关内容
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一个专业的物理问题分析助手"},
                    {"role": "user", "content": extract_equation_prompt},
                ],
                stream=False
            )
            
            extract_equation_content = response.choices[0].message.content.strip()
            # print(f"Extract_equation_content: {extract_equation_content}")

            pbar_eval.update(1)
            equations = [q['equation'] for q in step_analysis['result_quantity']]
            # 检查是否所有值都是 'N/A'
            if all(equation == 'N/A' for equation in equations):
                # print("所有物理量的值都是 'N/A'，跳过后续处理。")
                results['miss_item'].append("equation_correct")
            else:
                # 评估公式正确性
                equations_str = '\n'.join([
                    f"物理量 {i+1}：{q['name']}\n预期公式：{q['equation']}"
                    for i, q in enumerate(step_analysis['result_quantity'])
                    if q['equation'] != 'N/A'  # 只处理值不为 'N/A' 的物理量
                ])
                if "N/A" not in equations_str:
                    equation_prompt = f"""请判断以下物理公式是否等价,不考虑单位：
预期公式：
{equations_str}
实际内容：
{extract_equation_content}
请判断所有公式，只回答"正确"或"错误"，如果正确不用解释，如果有错误也用一两句话简单说明一下。"""
                    response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "你是一个专业的物理公式评估助手"},
                            {"role": "user", "content": equation_prompt},
                        ],
                        stream=False
                    )
                    
                    equation_result = response.choices[0].message.content.strip()
                    # print(f"Equation result: {equation_result}")
                    results['equation_correct'] = '正确' in equation_result
            pbar_eval.update(1)

# 公式评估结果：{equation_result}
# 结果评估结果：{value_result if values_str else '未评估'}

            # 如果有错误，分析错误原因
            if not (results['equation_correct'] and results['value_correct']):

# 预期内容：
# {equations_str}
# {values_str}
# 公式评估结果：{equation_result}
# 结果评估结果：{value_result if values_str else '未评估'}
# 错误原因:{results['error_analysis']}
                error_analysis_prompt = f"""请分析以下解题步骤中的错误：
标准答案内容：
{standard_step_content}
实际内容：
{extract_equation_content}
再请用一两句简洁得说明错误原因,用英文回答问题
"""
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的物理问题错误分析助手"},
                        {"role": "user", "content": error_analysis_prompt},
                    ],
                    stream=False
                )
                
                results['error_analysis'] = response.choices[0].message.content.strip()

                error_prompt = f"""请分析以下解题步骤中的错误：
标准答案内容：{standard_step_content}
实际内容：
{extract_equation_content}
错误分析：{results['error_analysis']}
在以下错误原因中挑选一个，
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
只返回错误原因种类即可，例如Conceptual Errors
"""

                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的物理问题错误分析助手"},
                        {"role": "user", "content": error_prompt},
                    ],
                    stream=False
                )
                
                results['error_kind'] = response.choices[0].message.content.strip()
                pbar_eval.update(1)

    except Exception as e:
        print(f"评估出错: {str(e)}")
        time.sleep(1)

    return results


def evaluate_with_deepseek(actual_answer, expected_answer, context, question_content, pbar_eval):
    """评估答案是否正确"""
    client = OpenAI(api_key="your_api_key", base_url="https://api.deepseek.com")
    
    prompt = f"""请基于以下信息，判断两个答案是否在含义上等价，不考虑单位：
具体问题：
{question_content}
实际回答：
{actual_answer}
预期回答：
{expected_answer}
请只回答"正确"或"错误"来表示这两个答案是否表达相同的含义。评判时请主要考虑数学表达式等细节是否等价，不需要考虑单位。"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个专业的数学问题答案评估助手"},
                {"role": "user", "content": prompt},
            ],
            stream=False
        )
        
        result = response.choices[0].message.content.strip()
        pbar_eval.update(1)
        return result == '正确'
    except Exception as e:
        print(f"评估出错: {str(e)}")
        time.sleep(1)  # 添加延迟重试
        return False


def evaluate_folder(folder_path: str):
    """评估文件夹中的所有问题"""
    results = {}
    client = OpenAI(api_key="your_api_key", base_url="https://api.deepseek.com")
    
    # 遍历所有子文件夹
    for subfolder in tqdm(os.listdir(folder_path), desc="处理子文件夹"):
        subfolder_path = os.path.join(folder_path, subfolder)
        if not os.path.isdir(subfolder_path):
            continue
        print("subfolder_path is", subfolder_path)
        
        # 读取v8问题文件
        problem_path_v8 = os.path.join(subfolder_path, "problem.json")
        if not os.path.exists(problem_path_v8):
            continue

        evaluation_path = os.path.join(subfolder_path, "evaluation")
        os.makedirs(evaluation_path, exist_ok=True)
        deepseek_result_path = os.path.join(evaluation_path, "deepseek_ds.json")
        if os.path.exists(deepseek_result_path):
            print(f"{deepseek_result_path} 已存在，跳过评估。")
            continue

        with open(problem_path_v8, 'r', encoding='utf-8') as f:
            problem_data_v8 = json.load(f)

        # 读取txt文件夹中的评估文件
        txt_folder = os.path.join(subfolder_path, "txt")
        if not os.path.exists(txt_folder):
            continue

        # 寻找deepseek.txt文件
        deepseek_path = os.path.join(txt_folder, "deepseek_ds.txt")
        if not os.path.exists(deepseek_path):
            continue
        # print("deepseek_path is", deepseek_path)
        
        
        with open(deepseek_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 获取预期的子问题列表
        expected_sub_questions = [f"sub_question_{i+1}" for i in range(len(problem_data_v8['answer']))]

        # 解析deepseek.txt内容
        parsed_content = parse_deepseek_content(content, expected_sub_questions)
        
        # 评估结果
        txt_results = {}
        
        # 为每个子问题建立step映射
        sub_q_step_mapping = {}
        current_step = 1

        # 遍历 explanation_steps 中的每个子问题
        for sub_q_key in problem_data_v8['explanation_steps'].keys():
            # 获取当前子问题的步骤数量
            steps_in_sub_q = len(problem_data_v8['explanation_steps'][sub_q_key])
            
            # 更新 sub_q_step_mapping
            sub_q_step_mapping[sub_q_key] = {
                'start_step': current_step,
                'end_step': current_step + steps_in_sub_q - 1
            }
            
            # 更新 current_step 为下一个子问题的起始步骤
            current_step += steps_in_sub_q

        
        with tqdm(total=len(problem_data_v8['answer']), desc=f"评估 deepseek_r1.txt") as pbar_eval:
            for i, (sub_q_key, sub_q_data) in enumerate(parsed_content.items()):
                expected_answer = problem_data_v8['answer'][i]
                actual_answer = sub_q_data['answer']
                
                # 首先评估整体答案
                is_correct = evaluate_with_deepseek(
                    actual_answer,
                    expected_answer,
                    problem_data_v8['question_structure']['context'],
                    problem_data_v8['question_structure'][sub_q_key],
                    pbar_eval
                )
                print(f"{sub_q_key} answer is_correct: {is_correct}")
                
                if is_correct:
                    # 如果答案正确，直接给满分
                    txt_results[sub_q_key] = {
                        'score': 1.0,
                        'steps': {}
                    }
                else:
                    # 如果答案错误，从该子问题的第一个step开始评估
                    step_scores = {}
                    steps_analysis = problem_data_v8['steps_analysis']
                    
                    # 获取该子问题的step范围
                    start_step = sub_q_step_mapping[sub_q_key]['start_step']
                    end_step = sub_q_step_mapping[sub_q_key]['end_step']
                    
                    # 合并该子问题在deepseek.txt中的所有步骤内容
                    deepseek_steps_content = "\n".join([
                        step_data['content'] 
                        for step_data in sub_q_data['steps'].values()
                    ])

                    # 遍历该子问题对应的steps
                    for step_num in range(start_step, end_step + 1):
                        step_key = f"step_{step_num}"
                        if step_key in steps_analysis:
                            step_analysis = steps_analysis[step_key]
                            
                            # 在合并后的内容中查找匹配
                            step_results = evaluate_step_content(
                                client,
                                deepseek_steps_content,  # 使用合并后的内容
                                step_analysis,
                                problem_data_v8['question_structure']['context'],
                                problem_data_v8['question_structure'][sub_q_key],
                                problem_data_v8['explanation_steps'][sub_q_key][step_key],
                                pbar_eval
                            )
                            
                            # 计算步骤得分
                            step_score = 0.0
                            if step_results['equation_correct']:
                                step_score += 0.5
                            if step_results['value_correct']:
                                step_score += 0.5
                                
                            step_scores[step_key] = {
                                'score': step_score,
                                'analysis': step_results
                            }

                    # 计算总分（使用该子问题steps的平均分）
                    total_steps = end_step - start_step + 1
                    total_score = sum(s['score'] for s in step_scores.values()) / total_steps if total_steps > 0 else 0.0
                    
                    txt_results[sub_q_key] = {
                        'score': total_score,
                        'steps': step_scores
                    }

        # 保存评估结果
        with open(deepseek_result_path, 'w', encoding='utf-8') as f:
            json.dump(txt_results, f, indent=4)
        print(f"评估结果已保存到: {deepseek_result_path}")
        results[subfolder] = txt_results
        # break
    
    return results

# 使用示例
folder_path = r"C:\Users\13938\Desktop\ACL-2025\src\final_benchmark"
results = evaluate_folder(folder_path)
