"""
全链路测试执行脚本
解析 openapi.json → 生成用例 → 生成 pytest → 执行 → 输出报告
"""
import sys
import os
import json
import time

# 确保项目根在 path
sys.path.insert(0, os.path.dirname(__file__))

from app.tools.openapi_parser import parse_openapi
from app.tools.test_file_writer import write_test_file
from app.tools.pytest_runner import run_pytest_all


# ═══════════════════════════════════════════════════════════
# 全面测试用例（手工精心设计，覆盖 5 种 case_type）
# ═══════════════════════════════════════════════════════════

TEST_CASES = {
    "POST /api/user/login": [
        # ── normal ──
        {
            "case_name": "正常登录_admin",
            "case_type": "normal",
            "request_data": {"username": "admin", "password": "123456"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "message", "data"]},
        },
        {
            "case_name": "正常登录_验证通过",
            "case_type": "normal",
            "request_data": {"username": "admin", "password": "123456"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "message", "data"]},
        },
        # ── auth_error ──
        {
            "case_name": "密码错误",
            "case_type": "auth_error",
            "request_data": {"username": "admin", "password": "wrong_password"},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "用户名不存在",
            "case_type": "auth_error",
            "request_data": {"username": "nobody", "password": "123456"},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        # ── missing_param ──
        {
            "case_name": "用户名为空字符串",
            "case_type": "missing_param",
            "request_data": {"username": "", "password": "123456"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "密码为空字符串",
            "case_type": "missing_param",
            "request_data": {"username": "admin", "password": ""},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        # ── boundary ──
        {
            "case_name": "用户名太短_2位",
            "case_type": "boundary",
            "request_data": {"username": "ab", "password": "123456"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "用户名边界_刚好3位",
            "case_type": "boundary",
            "request_data": {"username": "abc", "password": "123456"},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "用户名太长_21位",
            "case_type": "boundary",
            "request_data": {"username": "a" * 21, "password": "123456"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "密码太短_5位",
            "case_type": "boundary",
            "request_data": {"username": "admin", "password": "12345"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "密码边界_刚好6位",
            "case_type": "boundary",
            "request_data": {"username": "admin", "password": "123456"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        # ── invalid_type ──
        {
            "case_name": "用户名含特殊字符",
            "case_type": "invalid_type",
            "request_data": {"username": "admin<script>", "password": "123456"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "用户名含空格",
            "case_type": "invalid_type",
            "request_data": {"username": "ad min", "password": "123456"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
    ],

    "GET /api/user/info": [
        # ── normal ──
        {
            "case_name": "正常获取用户信息",
            "case_type": "normal",
            "request_data": {},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        # ── auth_error ──
        {
            "case_name": "缺少token",
            "case_type": "auth_error",
            "request_data": {},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "token无效",
            "case_type": "auth_error",
            "request_data": {},
            "headers": {"Authorization": "Bearer wrong-token"},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "token格式错误",
            "case_type": "auth_error",
            "request_data": {},
            "headers": {"Authorization": "mock-token-2024"},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
    ],

    "GET /api/product/list": [
        # ── normal ──
        {
            "case_name": "默认分页参数",
            "case_type": "normal",
            "request_data": {},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        {
            "case_name": "指定page和page_size",
            "case_type": "normal",
            "request_data": {"page": 2, "page_size": 20},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        {
            "case_name": "关键词搜索",
            "case_type": "normal",
            "request_data": {"keyword": "商品_1"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        # ── boundary ──
        {
            "case_name": "page为0",
            "case_type": "boundary",
            "request_data": {"page": 0},
            "expected_status": 400,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "page为负数",
            "case_type": "boundary",
            "request_data": {"page": -1},
            "expected_status": 400,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "page_size为0",
            "case_type": "boundary",
            "request_data": {"page_size": 0},
            "expected_status": 400,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "page_size超上限_101",
            "case_type": "boundary",
            "request_data": {"page_size": 101},
            "expected_status": 400,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "page_size边界_刚好1",
            "case_type": "boundary",
            "request_data": {"page_size": 1},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        {
            "case_name": "page_size边界_刚好100",
            "case_type": "boundary",
            "request_data": {"page_size": 100},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        {
            "case_name": "keyword超长_51字符",
            "case_type": "boundary",
            "request_data": {"keyword": "x" * 51},
            "expected_status": 400,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "page超出范围_2000",
            "case_type": "boundary",
            "request_data": {"page": 2000, "page_size": 10},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
    ],

    "POST /api/order/create": [
        # ── normal ──
        {
            "case_name": "正常创建订单",
            "case_type": "normal",
            "request_data": {"product_id": 1, "count": 2},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        {
            "case_name": "创建订单_最大数量",
            "case_type": "normal",
            "request_data": {"product_id": 10, "count": 999},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 200,
            "assert_rules": {"contains_fields": ["code", "data"]},
        },
        # ── auth_error ──
        {
            "case_name": "下单_缺少token",
            "case_type": "auth_error",
            "request_data": {"product_id": 1, "count": 2},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        {
            "case_name": "下单_token无效",
            "case_type": "auth_error",
            "request_data": {"product_id": 1, "count": 2},
            "headers": {"Authorization": "Bearer bad-token"},
            "expected_status": 401,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
        # ── missing_param ──
        {
            "case_name": "下单_缺少product_id",
            "case_type": "missing_param",
            "request_data": {"count": 2},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "下单_缺少count",
            "case_type": "missing_param",
            "request_data": {"product_id": 1},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        # ── boundary ──
        {
            "case_name": "下单_product_id为0",
            "case_type": "boundary",
            "request_data": {"product_id": 0, "count": 2},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "下单_product_id为负数",
            "case_type": "boundary",
            "request_data": {"product_id": -5, "count": 2},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "下单_count为0",
            "case_type": "boundary",
            "request_data": {"product_id": 1, "count": 0},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "下单_count为负数",
            "case_type": "boundary",
            "request_data": {"product_id": 1, "count": -3},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        {
            "case_name": "下单_count超上限_1000",
            "case_type": "boundary",
            "request_data": {"product_id": 1, "count": 1000},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 422,
            "assert_rules": {"contains_fields": ["detail"]},
        },
        # ── invalid_type / 业务校验 ──
        {
            "case_name": "下单_商品不存在",
            "case_type": "invalid_type",
            "request_data": {"product_id": 999, "count": 1},
            "headers": {"Authorization": "Bearer mock-token-2024"},
            "expected_status": 404,
            "assert_rules": {"contains_fields": ["code", "message"]},
        },
    ],
}


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  API Test Agent — 全链路测试")
    print("=" * 60)

    # 1. 解析 OpenAPI
    print("\n[1/4] 解析 openapi.json ...")
    endpoints = parse_openapi("openapi.json")
    print(f"       解析到 {len(endpoints)} 个接口")

    # 2. 匹配用例 + 生成 pytest 脚本
    print("\n[2/4] 生成 pytest 测试脚本 ...")
    total_cases = 0
    files = []
    for ep in endpoints:
        key = f"{ep['method']} {ep['path']}"
        cases = TEST_CASES.get(key, [])
        if cases:
            file_path = write_test_file(ep, cases)
            files.append(file_path)
            normal = sum(1 for c in cases if c["case_type"] == "normal")
            auth = sum(1 for c in cases if c["case_type"] == "auth_error")
            bound = sum(1 for c in cases if c["case_type"] == "boundary")
            missing = sum(1 for c in cases if c["case_type"] == "missing_param")
            invalid = sum(1 for c in cases if c["case_type"] == "invalid_type")
            total_cases += len(cases)
            print(f"       {key}")
            print(f"         → {file_path}")
            print(f"         → {len(cases)} cases (normal:{normal} auth:{auth} boundary:{bound} missing:{missing} invalid:{invalid})")

    # 3. 执行测试
    print(f"\n[3/4] 执行 {total_cases} 个测试用例 ...")
    print(f"       (确保 mock_server 已在 8001 端口运行)")
    start_time = time.time()
    result = run_pytest_all("generated_tests")
    elapsed = time.time() - start_time

    summary = result.get("summary", {})
    total = summary.get("total", 0)
    passed = summary.get("passed", 0)
    failed = summary.get("failed", 0)
    skipped = summary.get("skipped", 0)
    error = summary.get("error", 0)
    pass_rate = round(passed / total * 100, 1) if total > 0 else 0

    # 4. 输出报告
    print(f"\n[4/4] 测试报告")
    print("=" * 60)
    print(f"""
    ┌────────────────────────────┐
    │       测试结果汇总           │
    ├────────────────────────────┤
    │  接口数量:   {len(endpoints):>3}              │
    │  用例总数:   {total:>3}              │
    │  通过:       {passed:>3}  ✅           │
    │  失败:       {failed:>3}  ❌           │
    │  跳过:       {skipped:>3}              │
    │  错误:       {error:>3}              │
    │  通过率:     {pass_rate:>5.1f}%          │
    │  耗时:       {elapsed:>5.2f}s           │
    └────────────────────────────┘
    """)

    # 打印失败的用例
    stdout = result.get("stdout", "")
    if failed > 0:
        print("  ── 失败用例详情 ──")
        for line in stdout.splitlines():
            if "FAILED" in line:
                print(f"    {line.strip()}")
        print()

    # 按 case_type 分析
    print("  ── 按类型分析 ──")
    type_stats = {"normal": [0, 0], "auth_error": [0, 0], "boundary": [0, 0], "missing_param": [0, 0], "invalid_type": [0, 0]}
    # 简易统计：全部期望非 2xx 的应该能通过
    for cases in TEST_CASES.values():
        for c in cases:
            ct = c.get("case_type", "normal")
            if ct in type_stats:
                type_stats[ct][0] += 1

    for ct, (cnt, _) in type_stats.items():
        if cnt > 0:
            print(f"    {ct:15s}: {cnt} 个用例")

    # 失败分析
    if failed > 0:
        print()
        print("  ── 失败原因分析 ──")
        # 解析具体失败
        fail_lines = [l for l in stdout.splitlines() if "FAILED" in l]
        for fl in fail_lines:
            print(f"    {fl.strip()}")

    print()
    print("=" * 60)
    if pass_rate >= 85:
        print("  结果: 通过率达标 ✅  V1 验证成功")
    else:
        print(f"  结果: 通过率 {pass_rate}%，建议检查失败用例")
    print("=" * 60)

    return pass_rate


if __name__ == "__main__":
    main()
