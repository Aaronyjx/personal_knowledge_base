from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List


VERSION = "V6.16"


@dataclass
class LegalTestCase:
    id: int
    question: str
    expected_law: str
    expected_article: str
    description: str


TEST_CASES = [
    LegalTestCase(
        id=1,
        question="试用期最长可以约定多久？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第19条",
        description="试用期最长期限",
    ),
    LegalTestCase(
        id=2,
        question="劳动合同期限一年，试用期最长多久？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第19条",
        description="一年期劳动合同试用期",
    ),
    LegalTestCase(
        id=3,
        question="三年劳动合同可以约定多长时间试用期？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第19条",
        description="三年劳动合同试用期",
    ),
    LegalTestCase(
        id=4,
        question="同一个用人单位可以约定两次试用期吗？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第19条",
        description="重复约定试用期",
    ),
    LegalTestCase(
        id=5,
        question="非全日制用工可以约定试用期吗？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第70条",
        description="非全日制用工试用期",
    ),
    LegalTestCase(
        id=6,
        question="试用期工资最低是多少？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第20条",
        description="试用期工资",
    ),
    LegalTestCase(
        id=7,
        question="试用期内用人单位可以随意解除劳动合同吗？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第21条",
        description="试用期解除劳动合同",
    ),
    LegalTestCase(
        id=8,
        question="违法约定试用期有什么法律责任？",
        expected_law="中华人民共和国劳动合同法",
        expected_article="第83条",
        description="违法约定试用期责任",
    ),
]


CHINESE_NUMBER_MAPPING = {
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
    "十一": "11",
    "十二": "12",
    "十三": "13",
    "十四": "14",
    "十五": "15",
    "十六": "16",
    "十七": "17",
    "十八": "18",
    "十九": "19",
    "二十": "20",
    "二十一": "21",
    "二十二": "22",
    "二十三": "23",
    "二十四": "24",
    "二十五": "25",
    "二十六": "26",
    "二十七": "27",
    "二十八": "28",
    "二十九": "29",
    "三十": "30",
    "三十一": "31",
    "三十二": "32",
    "三十三": "33",
    "三十四": "34",
    "三十五": "35",
    "三十六": "36",
    "三十七": "37",
    "三十八": "38",
    "三十九": "39",
    "四十": "40",
    "四十一": "41",
    "四十二": "42",
    "四十三": "43",
    "四十四": "44",
    "四十五": "45",
    "四十六": "46",
    "四十七": "47",
    "四十八": "48",
    "四十九": "49",
    "五十": "50",
    "五十一": "51",
    "五十二": "52",
    "五十三": "53",
    "五十四": "54",
    "五十五": "55",
    "五十六": "56",
    "五十七": "57",
    "五十八": "58",
    "五十九": "59",
    "六十": "60",
    "六十一": "61",
    "六十二": "62",
    "六十三": "63",
    "六十四": "64",
    "六十五": "65",
    "六十六": "66",
    "六十七": "67",
    "六十八": "68",
    "六十九": "69",
    "七十": "70",
    "七十一": "71",
    "七十二": "72",
    "七十三": "73",
    "七十四": "74",
    "七十五": "75",
    "七十六": "76",
    "七十七": "77",
    "七十八": "78",
    "七十九": "79",
    "八十": "80",
    "八十一": "81",
    "八十二": "82",
    "八十三": "83",
}


def normalize_article(article: str) -> str:
    if article is None:
        return ""

    article = str(article).strip()

    if not article:
        return ""

    text = (
        article
        .replace("第", "")
        .replace("条", "")
        .strip()
    )

    if text.isdigit():
        return f"第{text}条"

    if text in CHINESE_NUMBER_MAPPING:
        return f"第{CHINESE_NUMBER_MAPPING[text]}条"

    return article


def article_matches(actual: str, expected: str) -> bool:
    return normalize_article(actual) == normalize_article(expected)


def safe_str(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _get_dict_field(
    data: Dict[str, Any],
    keys: tuple,
) -> Any:

    if not isinstance(data, dict):
        return None

    for key in keys:
        if key in data:
            value = data[key]

            if value is not None:
                return value

    payload = data.get("payload")

    if isinstance(payload, dict):
        for key in keys:
            if key in payload:
                value = payload[key]

                if value is not None:
                    return value

    metadata = data.get("metadata")

    if isinstance(metadata, dict):
        for key in keys:
            if key in metadata:
                value = metadata[key]

                if value is not None:
                    return value

    document = data.get("document")

    if isinstance(document, dict):

        for key in keys:
            if key in document:
                value = document[key]

                if value is not None:
                    return value

        document_payload = document.get("payload")

        if isinstance(document_payload, dict):

            for key in keys:
                if key in document_payload:
                    value = document_payload[key]

                    if value is not None:
                        return value

    result = data.get("result")

    if isinstance(result, dict):

        for key in keys:
            if key in result:
                value = result[key]

                if value is not None:
                    return value

        result_payload = result.get("payload")

        if isinstance(result_payload, dict):

            for key in keys:
                if key in result_payload:
                    value = result_payload[key]

                    if value is not None:
                        return value

    return None


def get_field(
    item: Any,
    *keys: str,
    default: Any = "",
) -> Any:

    if item is None:
        return default

    if isinstance(item, dict):

        value = _get_dict_field(
            item,
            keys,
        )

        if value is not None:
            return value

        return default

    for key in keys:

        try:

            if hasattr(item, key):

                value = getattr(item, key)

                if value is not None:
                    return value

        except Exception:
            pass

    try:

        if hasattr(item, "payload"):

            payload = getattr(item, "payload")

            if isinstance(payload, dict):

                value = _get_dict_field(
                    payload,
                    keys,
                )

                if value is not None:
                    return value

            else:

                for key in keys:

                    try:

                        if hasattr(payload, key):

                            value = getattr(
                                payload,
                                key,
                            )

                            if value is not None:
                                return value

                    except Exception:
                        pass

    except Exception:
        pass

    try:

        if hasattr(item, "metadata"):

            metadata = getattr(
                item,
                "metadata",
            )

            if isinstance(metadata, dict):

                value = _get_dict_field(
                    metadata,
                    keys,
                )

                if value is not None:
                    return value

    except Exception:
        pass

    return default


def get_law_name(item: Any) -> str:

    value = get_field(
        item,
        "law_name",
        "law",
        "law_title",
        "document_name",
        "document_title",
        "source_name",
        "source",
        "title",
    )

    return safe_str(value)


def get_article(item: Any) -> str:

    value = get_field(
        item,
        "article",
        "article_number",
        "article_no",
        "article_number_normalized",
        "normalized_article",
        "article_title",
    )

    return safe_str(value)


def get_evidence_role(item: Any) -> str:

    value = get_field(
        item,
        "evidence_role",
        "role",
    )

    return safe_str(value).lower()


def get_text(item: Any) -> str:

    value = get_field(
        item,
        "text",
        "article_text",
        "content",
        "text_content",
        "payload_text",
    )

    return safe_str(value)


def get_score(item: Any) -> Any:

    return get_field(
        item,
        "final_score",
        "score",
        "reranker_score",
        "similarity",
    )


def extract_final_results(result: Any) -> List[Any]:

    if result is None:
        return []

    if isinstance(result, list):
        return result

    if isinstance(result, tuple):
        return list(result)

    if isinstance(result, dict):

        for key in [
            "results",
            "documents",
            "final_results",
            "items",
            "data",
            "matches",
            "retrieved",
            "retrieved_documents",
        ]:

            value = result.get(key)

            if isinstance(value, list):
                return value

            if isinstance(value, tuple):
                return list(value)

    return []


def is_expected_evidence(
    item: Any,
    case: LegalTestCase,
) -> bool:

    law = get_law_name(item)

    article = get_article(item)

    law_ok = (
        case.expected_law in law
        or
        law in case.expected_law
    )

    article_ok = article_matches(
        article,
        case.expected_article,
    )

    return law_ok and article_ok


def find_expected_positions(
    results: List[Any],
    case: LegalTestCase,
) -> List[int]:

    positions = []

    for index, item in enumerate(
        results,
        start=1,
    ):

        if is_expected_evidence(
            item,
            case,
        ):

            positions.append(index)

    return positions


def find_expected_evidence(
    results: List[Any],
    case: LegalTestCase,
) -> List[Any]:

    matches = []

    for item in results:

        if is_expected_evidence(
            item,
            case,
        ):

            matches.append(item)

    return matches


def find_primary(
    results: List[Any],
) -> Any:

    for item in results:

        role = get_evidence_role(item)

        if role == "primary":
            return item

    return None


def find_primary_position(
    results: List[Any],
) -> int:

    for index, item in enumerate(
        results,
        start=1,
    ):

        if get_evidence_role(item) == "primary":
            return index

    return 0


def count_supporting(
    results: List[Any],
) -> int:

    count = 0

    for item in results:

        if get_evidence_role(item) == "supporting":
            count += 1

    return count


def calculate_mrr(
    expected_positions: List[int],
) -> float:

    if not expected_positions:
        return 0.0

    first_position = min(
        expected_positions
    )

    return 1.0 / first_position


def calculate_recall_at_k(
    expected_positions: List[int],
    k: int,
) -> bool:

    for position in expected_positions:

        if position <= k:
            return True

    return False


def get_role_counts(
    results: List[Any],
) -> Dict[str, int]:

    counts = {}

    for item in results:

        role = get_evidence_role(item)

        if not role:
            role = "none"

        counts[role] = (
            counts.get(role, 0)
            + 1
        )

    return counts


def print_result_diagnostic(
    results: List[Any],
) -> None:

    print()
    print("Top Results：")

    for index, item in enumerate(
        results[:10],
        start=1,
    ):

        law = get_law_name(item)
        article = get_article(item)
        role = get_evidence_role(item)
        score = get_score(item)
        text = get_text(item)

        print(
            f"[{index}] "
            f"{law} "
            f"{article} "
            f"role={role or '-'} "
            f"score={score}"
        )

        print(
            f"     text_length={len(text)}"
        )

    print()


def evaluate_case(
    case: LegalTestCase,
) -> Dict[str, Any]:

    print()
    print("=" * 70)
    print(
        f"[{case.id}/{len(TEST_CASES)}] "
        f"{case.question}"
    )
    print("=" * 70)

    print(
        f"说明：{case.description}"
    )

    print("=" * 70)

    start = time.time()

    try:

        from src.reranker import search

    except ImportError as e:

        print()
        print(
            "❌ 无法导入 src.reranker.search"
        )
        print(e)

        return {
            "passed": False,
            "law_ok": False,
            "article_ok": False,
            "primary_ok": False,
            "payload_ok": False,
            "supporting_ok": False,
            "expected_found": False,
            "error": str(e),
            "elapsed": time.time() - start,
        }

    try:

        result = search(
            case.question
        )

        results = extract_final_results(
            result
        )

        print()
        print(
            f"返回结果数量：{len(results)}"
        )

        if not results:

            print(
                "❌ 没有返回法律资料"
            )

            return {
                "passed": False,
                "law_ok": False,
                "article_ok": False,
                "primary_ok": False,
                "payload_ok": False,
                "supporting_ok": False,
                "expected_found": False,
                "expected_positions": [],
                "expected_rank": 0,
                "primary_rank": 0,
                "mrr": 0.0,
                "recall_at_3": False,
                "recall_at_5": False,
                "recall_at_10": False,
                "actual_law": "",
                "actual_article": "",
                "actual_role": "",
                "text_length": 0,
                "elapsed": time.time() - start,
            }

        print_result_diagnostic(
            results
        )

        expected_matches = find_expected_evidence(
            results,
            case,
        )

        expected_positions = find_expected_positions(
            results,
            case,
        )

        expected_found = (
            len(expected_matches) > 0
        )

        expected_rank = (
            min(expected_positions)
            if expected_positions
            else 0
        )

        mrr = calculate_mrr(
            expected_positions
        )

        recall_at_3 = calculate_recall_at_k(
            expected_positions,
            3,
        )

        recall_at_5 = calculate_recall_at_k(
            expected_positions,
            5,
        )

        recall_at_10 = calculate_recall_at_k(
            expected_positions,
            10,
        )

        primary = find_primary(
            results
        )

        primary_rank = find_primary_position(
            results
        )

        primary_ok = False

        primary_law = ""
        primary_article = ""
        primary_text = ""

        if primary is not None:

            primary_law = get_law_name(
                primary
            )

            primary_article = get_article(
                primary
            )

            primary_text = get_text(
                primary
            )

            primary_law_ok = (
                case.expected_law
                in primary_law
                or
                primary_law
                in case.expected_law
            )

            primary_article_ok = (
                article_matches(
                    primary_article,
                    case.expected_article,
                )
            )

            primary_ok = (
                primary_law_ok
                and
                primary_article_ok
            )

        actual_law = ""
        actual_article = ""
        actual_role = ""
        actual_text = ""

        if expected_matches:

            expected_item = (
                expected_matches[0]
            )

            actual_law = get_law_name(
                expected_item
            )

            actual_article = get_article(
                expected_item
            )

            actual_role = get_evidence_role(
                expected_item
            )

            actual_text = get_text(
                expected_item
            )

        law_ok = expected_found
        article_ok = expected_found

        payload_ok = (
            len(actual_text) > 0
        )

        supporting_count = count_supporting(
            results
        )

        supporting_ok = (
            supporting_count > 0
        )

        passed = (
            law_ok
            and
            article_ok
            and
            payload_ok
        )

        elapsed = time.time() - start

        print()
        print("Expected：")

        print(
            f"  Law     : "
            f"{case.expected_law}"
        )

        print(
            f"  Article : "
            f"{case.expected_article}"
        )

        print()
        print("Retrieval：")

        if expected_found:

            print(
                "  ✅ 期望法律条款已检索到"
            )

            print(
                f"  Rank    : "
                f"{expected_rank}"
            )

            print(
                f"  Positions: "
                f"{expected_positions}"
            )

        else:

            print(
                "  ❌ 未检索到期望法律条款"
            )

        print(
            f"  MRR     : "
            f"{mrr:.4f}"
        )

        print(
            f"  Recall@3: "
            f"{'✅' if recall_at_3 else '❌'}"
        )

        print(
            f"  Recall@5: "
            f"{'✅' if recall_at_5 else '❌'}"
        )

        print(
            f"  Recall@10: "
            f"{'✅' if recall_at_10 else '❌'}"
        )

        print()
        print("Actual Expected Evidence：")

        if expected_found:

            print(
                f"  Law     : "
                f"{actual_law}"
            )

            print(
                f"  Article : "
                f"{actual_article}"
            )

            print(
                f"  Role    : "
                f"{actual_role or '-'}"
            )

            print(
                f"  Text    : "
                f"{len(actual_text)}"
            )

        else:

            print(
                "  ❌ 未找到期望法律条款"
            )

        print()
        print("Primary Evidence：")

        if primary is None:

            print(
                "  ❌ 未找到 primary evidence"
            )

        else:

            print(
                f"  Rank    : "
                f"{primary_rank}"
            )

            print(
                f"  Law     : "
                f"{primary_law}"
            )

            print(
                f"  Article : "
                f"{primary_article}"
            )

            print(
                f"  Text    : "
                f"{len(primary_text)}"
            )

            if primary_ok:

                print(
                    "  ✅ Primary 正确"
                )

            else:

                print(
                    "  ⚠️ Primary 存在，"
                    "但不是期望条款"
                )

        print()
        print("Component Check：")

        print(
            f"  Law Match         : "
            f"{'✅' if law_ok else '❌'}"
        )

        print(
            f"  Article Match     : "
            f"{'✅' if article_ok else '❌'}"
        )

        print(
            f"  Primary Evidence : "
            f"{'✅' if primary_ok else '❌'}"
        )

        print(
            f"  Payload Text      : "
            f"{'✅' if payload_ok else '❌'} "
            f"({len(actual_text)})"
        )

        print(
            f"  Supporting Found  : "
            f"{'✅' if supporting_ok else '❌'} "
            f"({supporting_count})"
        )

        role_counts = get_role_counts(
            results
        )

        print()
        print("Role Distribution：")

        for role, count in sorted(
            role_counts.items()
        ):

            print(
                f"  {role:<12}: {count}"
            )

        print()
        print(
            "Regression Result："
        )

        if passed:

            print(
                "  ✅ PASS"
            )

        else:

            print(
                "  ❌ FAIL"
            )

            if not expected_found:

                print(
                    "  ❌ Retrieval 未找到期望条款"
                )

            elif not payload_ok:

                print(
                    "  ❌ Payload Text 缺失"
                )

            elif not primary_ok:

                print(
                    "  ⚠️ 检索正确，但 Primary "
                    "Evidence 分类不正确"
                )

        print(
            f"耗时：{elapsed:.2f} 秒"
        )

        return {
            "passed": passed,
            "law_ok": law_ok,
            "article_ok": article_ok,
            "primary_ok": primary_ok,
            "payload_ok": payload_ok,
            "supporting_ok": supporting_ok,
            "supporting_count": supporting_count,
            "expected_found": expected_found,
            "expected_positions": expected_positions,
            "expected_rank": expected_rank,
            "primary_rank": primary_rank,
            "mrr": mrr,
            "recall_at_3": recall_at_3,
            "recall_at_5": recall_at_5,
            "recall_at_10": recall_at_10,
            "expected_law": case.expected_law,
            "expected_article": case.expected_article,
            "actual_law": actual_law,
            "actual_article": actual_article,
            "actual_role": actual_role,
            "actual_text": actual_text,
            "text_length": len(actual_text),
            "role_counts": role_counts,
            "elapsed": elapsed,
        }

    except Exception as e:

        elapsed = time.time() - start

        print()
        print(
            "❌ 测试异常"
        )

        print(
            type(e).__name__
        )

        print(e)

        return {
            "passed": False,
            "law_ok": False,
            "article_ok": False,
            "primary_ok": False,
            "payload_ok": False,
            "supporting_ok": False,
            "expected_found": False,
            "expected_positions": [],
            "expected_rank": 0,
            "primary_rank": 0,
            "mrr": 0.0,
            "recall_at_3": False,
            "recall_at_5": False,
            "recall_at_10": False,
            "error": str(e),
            "elapsed": elapsed,
        }


def main():

    print()
    print("=" * 70)
    print("个人法律知识库")
    print("=" * 70)
    print(
        f"Legal RAG Regression "
        f"Evaluation {VERSION}"
    )
    print("=" * 70)

    print()
    print(
        f"测试用例：{len(TEST_CASES)}"
    )

    print()
    print("测试目标：")

    print("  ① 法律名称")
    print("  ② 核心条款")
    print("  ③ Retrieval Rank")
    print("  ④ MRR")
    print("  ⑤ Recall@K")
    print("  ⑥ Primary Evidence")
    print("  ⑦ Payload Text Recovery")
    print("  ⑧ Supporting Evidence")
    print("  ⑨ Evidence Role Classification")

    total_start = time.time()

    evaluation_results = []

    for case in TEST_CASES:

        result = evaluate_case(
            case
        )

        evaluation_results.append(
            result
        )

    total = len(
        evaluation_results
    )

    passed = sum(
        1
        for result in evaluation_results
        if result.get("passed")
    )

    failed = total - passed

    law_match = sum(
        1
        for result in evaluation_results
        if result.get("law_ok")
    )

    article_match = sum(
        1
        for result in evaluation_results
        if result.get("article_ok")
    )

    expected_found = sum(
        1
        for result in evaluation_results
        if result.get("expected_found")
    )

    primary_match = sum(
        1
        for result in evaluation_results
        if result.get("primary_ok")
    )

    payload_match = sum(
        1
        for result in evaluation_results
        if result.get("payload_ok")
    )

    supporting_found = sum(
        1
        for result in evaluation_results
        if result.get("supporting_ok")
    )

    recall_at_3 = sum(
        1
        for result in evaluation_results
        if result.get("recall_at_3")
    )

    recall_at_5 = sum(
        1
        for result in evaluation_results
        if result.get("recall_at_5")
    )

    recall_at_10 = sum(
        1
        for result in evaluation_results
        if result.get("recall_at_10")
    )

    total_mrr = sum(
        result.get("mrr", 0.0)
        for result in evaluation_results
    )

    average_mrr = (
        total_mrr / total
        if total > 0
        else 0.0
    )

    accuracy = (
        passed / total * 100
        if total > 0
        else 0.0
    )

    total_elapsed = (
        time.time()
        - total_start
    )

    print()
    print("=" * 70)
    print(
        f"{VERSION} Regression Summary"
    )
    print("=" * 70)

    print()
    print(
        f"总测试数：{total}"
    )

    print(
        f"通过：{passed}"
    )

    print(
        f"失败：{failed}"
    )

    print(
        f"准确率：{accuracy:.1f}%"
    )

    print()
    print("Retrieval Metrics：")

    print(
        f"Expected Found : "
        f"{expected_found}/{total}"
    )

    print(
        f"Recall@3       : "
        f"{recall_at_3}/{total}"
    )

    print(
        f"Recall@5       : "
        f"{recall_at_5}/{total}"
    )

    print(
        f"Recall@10      : "
        f"{recall_at_10}/{total}"
    )

    print(
        f"MRR            : "
        f"{average_mrr:.4f}"
    )

    print()
    print("Component Statistics：")

    print(
        f"Law Match        : "
        f"{law_match}/{total}"
    )

    print(
        f"Article Match    : "
        f"{article_match}/{total}"
    )

    print(
        f"Primary Evidence : "
        f"{primary_match}/{total}"
    )

    print(
        f"Payload Text     : "
        f"{payload_match}/{total}"
    )

    print(
        f"Supporting Found : "
        f"{supporting_found}/{total}"
    )

    print()
    print("Case Summary：")

    for case, result in zip(
        TEST_CASES,
        evaluation_results,
    ):

        status = (
            "PASS"
            if result.get("passed")
            else "FAIL"
        )

        expected_article = (
            case.expected_article
        )

        actual_article = result.get(
            "actual_article",
            "-",
        )

        expected_rank = result.get(
            "expected_rank",
            0,
        )

        primary_rank = result.get(
            "primary_rank",
            0,
        )

        role = result.get(
            "actual_role",
            "",
        )

        text_length = result.get(
            "text_length",
            0,
        )

        if not actual_article:
            actual_article = "-"

        if not role:
            role = "-"

        expected_rank_text = (
            str(expected_rank)
            if expected_rank
            else "-"
        )

        primary_rank_text = (
            str(primary_rank)
            if primary_rank
            else "-"
        )

        print(
            f"[{case.id}] "
            f"{status:<5} "
            f"Expected="
            f"{expected_article:<6} "
            f"Actual="
            f"{actual_article:<6} "
            f"Rank="
            f"{expected_rank_text:<4} "
            f"PrimaryRank="
            f"{primary_rank_text:<4} "
            f"Role="
            f"{role:<11} "
            f"Text="
            f"{text_length}"
        )

    print()
    print(
        "Evidence Role Diagnostic："
    )

    role_counts = {}

    for result in evaluation_results:

        role = result.get(
            "actual_role",
            "",
        )

        if not role:
            role = "none"

        role_counts[role] = (
            role_counts.get(
                role,
                0,
            )
            + 1
        )

    for role, count in sorted(
        role_counts.items()
    ):

        print(
            f"  {role:<12}: {count}"
        )

    if failed > 0:

        print()
        print(
            "Failure Diagnostic："
        )

        for case, result in zip(
            TEST_CASES,
            evaluation_results,
        ):

            if result.get("passed"):
                continue

            print()
            print(
                f"[Case {case.id}] "
                f"{case.question}"
            )

            if result.get(
                "expected_found"
            ):

                rank = result.get(
                    "expected_rank",
                    0,
                )

                role = result.get(
                    "actual_role",
                    "",
                )

                print(
                    f"  ✅ 期望条款已检索到"
                    f"（Rank={rank}）"
                )

                print(
                    f"  当前 Role="
                    f"{role or 'none'}"
                )

            else:

                print(
                    "  ❌ 未检索到期望法律条款"
                )

            if result.get(
                "primary_ok"
            ):

                print(
                    "  ✅ Primary Evidence 正确"
                )

            else:

                print(
                    "  ❌ Primary Evidence "
                    "不正确"
                )

            if result.get(
                "payload_ok"
            ):

                print(
                    "  ✅ Payload Text 正常"
                )

            else:

                print(
                    "  ❌ Payload Text 缺失"
                )

            error = result.get(
                "error"
            )

            if error:

                print(
                    f"  ❌ Error: {error}"
                )

    print()
    print(
        "V6.16 Diagnosis："
    )

    if expected_found == total:

        print(
            "  ✅ 8/8 期望法律条款均已检索到"
        )

        if primary_match < total:

            print(
                "  ⚠️ Retrieval 基础正确"
            )

            print(
                "  ⚠️ 当前主要问题是 "
                "Primary Evidence Classification"
            )

            print(
                "  ⚠️ 暂时不要调整 BGE-M3"
            )

            print(
                "  ⚠️ 暂时不要调整 Qdrant"
            )

            print(
                "  ⚠️ 暂时不要调整基础召回"
            )

        else:

            print(
                "  ✅ Retrieval 与 Primary "
                "Evidence 均正常"
            )

    else:

        print(
            "  ⚠️ Retrieval 仍存在缺失"
        )

        print(
            "  应优先检查 "
            "Retriever / Reranker"
        )

    if failed == 0:

        print()
        print(
            f"🎉 {VERSION} "
            "回归测试全部通过"
        )

        print(
            "✅ 可以建立 Regression Baseline"
        )

    else:

        print()
        print(
            f"⚠️ {VERSION} "
            f"存在 {failed} 个失败案例"
        )

        print(
            "❌ 暂时不要建立 "
            "Regression Baseline"
        )

    print()
    print(
        f"总耗时："
        f"{total_elapsed:.2f} 秒"
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()