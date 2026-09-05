"""
src/llm.py

个人法律知识库
LLM V3.9

功能：
1. 使用 Ollama 调用本地 LLM
2. 根据 RAG 检索结果生成法律回答
3. 严格限制模型只能依据知识库资料回答
4. 优先使用核心法律依据
5. 禁止编造法律条款
6. 优化 Prompt，减少无意义输出
7. 限制最大生成长度，提高响应速度
8. 保持与 rag.py 的兼容接口：

    generate_answer(question, context)

当前模型：
    qwen3.5:9b

Ollama：
    http://127.0.0.1:11434
"""

import time
import requests


# ============================================================
# Ollama 配置
# ============================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

MODEL_NAME = "qwen3.5:9b"


# ============================================================
# LLM 参数
# ============================================================

TEMPERATURE = 0.1

NUM_PREDICT = 800

REQUEST_TIMEOUT = 300


# ============================================================
# Prompt
# ============================================================

def build_prompt(question, context):
    """
    构建法律 RAG Prompt。
    """

    prompt = f"""
你是一名严谨的中国劳动法律知识库 AI 助手。

你的任务是：
根据【知识库法律资料】回答【用户问题】。

==============================
必须遵守以下规则
==============================

1. 只能根据【知识库法律资料】回答。

2. 不得使用知识库之外的法律条文、司法解释、
   行政法规或你自己的法律知识补充答案。

3. 如果知识库资料中存在直接相关的法律条款，
   必须以直接相关条款作为主要法律依据。

4. 如果存在多个相关条款：
   - 优先引用与用户问题直接对应的条款；
   - 其次引用补充说明该问题的条款；
   - 不要把仅仅包含相同关键词、但与问题无直接关系的条款
     作为主要法律依据。

5. 法律条款必须以知识库提供的内容为准。
   不得自行修改、补充或编造法律条文。

6. 如果知识库资料不足以回答问题，
   必须明确回答：
   “当前知识库中没有找到足够的相关法律规定。”

7. 不要输出思考过程、推理过程或内部分析。

8. 回答应该简洁、准确、直接。

9. 法律问题优先按照以下结构回答：

   【结论】
   直接回答用户问题。

   【法律依据】
   列出最重要的法律名称、条款和相关内容。

   【说明】
   对法律条款进行简短解释。

10. 如果知识库中只有部分相关资料，
    只能回答能够由这些资料支持的部分，
    不要自行推测。

11. 不要虚构法律条款编号。

12. 不要虚构案例、法院判决、司法解释或法律观点。

==============================
用户问题
==============================

{question}

==============================
知识库法律资料
==============================

{context}

==============================
回答要求
==============================

请直接回答用户问题。

优先使用知识库中与问题最直接相关的法律条款。

只输出最终法律回答，
不要输出你的思考过程。
"""

    return prompt


# ============================================================
# 调用 Ollama
# ============================================================

def generate_answer(question, context):
    """
    根据用户问题和 RAG Context 生成法律回答。

    保持与 rag.py 的兼容接口：

        generate_answer(question, context)

    参数：
        question: 用户问题
        context: RAG 检索结果

    返回：
        str
    """

    if not question or not question.strip():
        return "请输入法律问题。"

    if not context or not context.strip():
        return "当前知识库中没有找到相关法律资料。"

    question = question.strip()
    context = context.strip()

    # --------------------------------------------------------
    # 构建 Prompt
    # --------------------------------------------------------

    prompt = build_prompt(
        question=question,
        context=context
    )

    # --------------------------------------------------------
    # 开始计时
    # --------------------------------------------------------

    start_time = time.perf_counter()

    print()
    print("正在调用 Ollama...")
    print(f"LLM 模型：{MODEL_NAME}")

    # --------------------------------------------------------
    # Ollama 请求
    # --------------------------------------------------------

    try:

        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": TEMPERATURE,
                    "num_predict": NUM_PREDICT,
                }
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

    except requests.exceptions.ConnectionError:

        return (
            "无法连接 Ollama。\n\n"
            "请确认 Ollama 已经启动，并检查：\n"
            f"{OLLAMA_URL}"
        )

    except requests.exceptions.Timeout:

        return (
            "LLM 请求超时。\n\n"
            f"当前模型：{MODEL_NAME}\n"
            f"超时时间：{REQUEST_TIMEOUT} 秒"
        )

    except requests.exceptions.RequestException as e:

        return (
            "调用 Ollama 失败。\n\n"
            f"错误信息：{e}"
        )

    # --------------------------------------------------------
    # 解析返回结果
    # --------------------------------------------------------

    try:

        data = response.json()

    except ValueError:

        return "Ollama 返回的数据格式无法解析。"

    answer = data.get("response", "")

    if not answer:

        return "LLM 没有返回有效回答。"

    answer = answer.strip()

    # --------------------------------------------------------
    # 计算耗时
    # --------------------------------------------------------

    elapsed = time.perf_counter() - start_time

    print(f"LLM 生成耗时：{elapsed:.2f} 秒")

    # --------------------------------------------------------
    # 返回最终回答
    # --------------------------------------------------------

    return answer


# ============================================================
# 独立测试
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("个人法律知识库")
    print("LLM V3.9 测试")
    print("=" * 70)

    print()
    print(f"Ollama：{OLLAMA_URL}")
    print(f"模型：{MODEL_NAME}")
    print(f"Temperature：{TEMPERATURE}")
    print(f"最大输出：{NUM_PREDICT}")

    print()
    print("=" * 70)

    question = input("请输入问题：").strip()

    if not question:

        print("未输入问题。")

    else:

        # ----------------------------------------------------
        # 测试 Context
        # ----------------------------------------------------

        test_context = """
【核心法律依据】

《中华人民共和国劳动合同法》第十四条

无固定期限劳动合同，是指用人单位与劳动者约定无确定终止时间的劳动合同。

有下列情形之一，劳动者提出或者同意续订、订立劳动合同的，
除劳动者提出订立固定期限劳动合同外，应当订立无固定期限劳动合同：

（一）劳动者在该用人单位连续工作满十年的；

【辅助法律依据】

《中华人民共和国劳动合同法实施条例》第九条

劳动合同法第十四条第二款规定的连续工作满10年的起始时间，
应当自用人单位用工之日起计算，包括劳动合同法施行前的工作年限。
"""

        print()
        print("=" * 70)
        print("正在生成 AI 法律回答...")
        print("=" * 70)

        answer = generate_answer(
            question=question,
            context=test_context
        )

        print()
        print("=" * 70)
        print("AI 法律回答")
        print("=" * 70)

        print(answer)

        print()
        print("=" * 70)
        print("测试完成")
        print("=" * 70)