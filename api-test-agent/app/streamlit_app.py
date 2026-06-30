"""
Streamlit 前端 — API Test Agent 可视化界面
启动: streamlit run app/streamlit_app.py
"""
import sys
import os
import json
import time

# 确保项目根在 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

from app.tools.openapi_parser import parse_openapi
from app.tools.test_file_writer import write_test_file
from app.tools.pytest_runner import run_pytest_all
from app.services.parse_service import parse_by_content
from app.services.testcase_service import generate_for_endpoint, get_case_type_stats
from app.agents.report_agent import analyze_all_failures
from app.db import (
    setup as db_setup, create_project, save_endpoints, save_test_cases, save_execution,
    list_executions, get_pass_rate_trend, list_projects, get_endpoints,
)
from app.config import settings

# ── 页面配置 ──────────────────────────────────────────

st.set_page_config(
    page_title="API Test Agent",
    page_icon="",
    layout="wide",
)

# ── 初始化 DB ─────────────────────────────────────────

db_setup()

# ── 侧边栏 ────────────────────────────────────────────

st.sidebar.title("API Test Agent")
st.sidebar.markdown(f"**Model:** {settings.MODEL_NAME}")
st.sidebar.markdown(f"**Target:** {settings.TEST_BASE_URL}")

page = st.sidebar.radio(
    "Navigation",
    ["Run Tests", "History", "Projects"],
)

# ══════════════════════════════════════════════════════
# Page: Run Tests
# ══════════════════════════════════════════════════════

if page == "Run Tests":
    st.title("Run API Tests")

    # --- Step 1: Upload ---
    st.header("1. Upload OpenAPI Document")
    uploaded_file = st.file_uploader("Choose openapi.json", type=["json", "yaml", "yml"])

    if uploaded_file:
        raw = uploaded_file.read()
        if uploaded_file.name.endswith((".yaml", ".yml")):
            import yaml
            content = yaml.safe_load(raw)
        else:
            content = json.loads(raw)
        title = content.get("info", {}).get("title", uploaded_file.name)
        st.success(f"Loaded: **{title}**")

        # --- Step 2: Parse ---
        st.header("2. Parse Endpoints")
        if st.button("Parse", key="btn_parse"):
            with st.spinner("Parsing..."):
                endpoints = parse_by_content(content)
                st.session_state["endpoints"] = endpoints

                # 入库
                project = create_project(name=title, openapi_filename=uploaded_file.name)
                save_endpoints(project.id, endpoints)
                st.session_state["project_id"] = project.id

                st.success(f"Parsed {len(endpoints)} endpoints")
                df = pd.DataFrame([
                    {"Method": ep["method"], "Path": ep["path"], "Summary": ep.get("summary", ""),
                     "Params": len(ep.get("request_body", {}))}
                    for ep in endpoints
                ])
                st.dataframe(df, use_container_width=True)

        # --- Step 3: Generate ---
        if "endpoints" in st.session_state:
            st.header("3. Generate Test Cases (LLM)")
            if st.button("Generate with LLM", key="btn_generate"):
                all_cases = {}
                total = 0
                progress = st.progress(0)
                status = st.empty()

                for i, ep in enumerate(st.session_state["endpoints"]):
                    key = f"{ep['method']} {ep['path']}"
                    status.text(f"Generating for {key}...")
                    try:
                        cases = generate_for_endpoint(ep)
                    except Exception as e:
                        st.warning(f"LLM failed for {key}: {e}")
                        cases = []
                    all_cases[key] = cases
                    total += len(cases)
                    progress.progress((i + 1) / len(st.session_state["endpoints"]))

                st.session_state["test_cases"] = all_cases
                progress.empty()
                status.empty()
                st.success(f"Generated {total} test cases across {len(st.session_state['endpoints'])} endpoints")

                # 显示各接口用例数
                for key, cases in all_cases.items():
                    stats = get_case_type_stats(cases)
                    with st.expander(f"{key} — {len(cases)} cases"):
                        cols = st.columns(5)
                        cols[0].metric("Normal", stats.get("normal", 0))
                        cols[1].metric("Missing", stats.get("missing_param", 0))
                        cols[2].metric("Invalid", stats.get("invalid_type", 0))
                        cols[3].metric("Boundary", stats.get("boundary", 0))
                        cols[4].metric("Auth", stats.get("auth_error", 0))

        # --- Step 4: Execute ---
        if "test_cases" in st.session_state:
            st.header("4. Execute Tests")
            if st.button("Run Tests", key="btn_execute", type="primary"):
                # 清空旧脚本（不删目录本身，Docker volume 挂载点不能删）
                import shutil, os
                if os.path.exists("generated_tests"):
                    for f in os.listdir("generated_tests"):
                        fp = os.path.join("generated_tests", f)
                        if os.path.isfile(fp):
                            os.remove(fp)
                        elif os.path.isdir(fp):
                            shutil.rmtree(fp)

                for ep in st.session_state["endpoints"]:
                    key = f"{ep['method']} {ep['path']}"
                    cases = st.session_state["test_cases"].get(key, [])
                    valid = [c for c in cases if "error" not in c]
                    if valid:
                        write_test_file(ep, valid)

                # 实时日志容器
                log_container = st.empty()
                status_container = st.empty()

                # 用 run_pytest_stream 实时执行
                from app.tools.pytest_runner import run_pytest_stream

                log_lines = []
                progress_placeholder = st.empty()

                def on_line(line: str):
                    log_lines.append(line)
                    # 只保留最后 20 行显示
                    log_container.code("\n".join(log_lines[-20:]), language="text")

                start = time.time()
                result = run_pytest_stream("generated_tests", on_line=on_line)
                elapsed = time.time() - start

                log_container.empty()

                summary = result.get("summary", {})
                total = summary.get("total", 0)
                passed = summary.get("passed", 0)
                failed = summary.get("failed", 0)
                pass_rate = round(passed / total * 100, 1) if total > 0 else 0

                st.session_state["last_result"] = {
                    "total": total, "passed": passed, "failed": failed,
                    "pass_rate": pass_rate, "duration": round(elapsed, 2),
                    "result": result,
                }

                # 入库
                project_id = st.session_state.get("project_id", 1)
                save_execution(
                    project_id=project_id,
                    total=total, passed=passed, failed=failed,
                    pass_rate=pass_rate, duration=round(elapsed, 2),
                    is_llm=True,
                    stdout=result.get("stdout", ""),
                )

                # 显示结果
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total", total)
                col2.metric("Passed", passed, delta=None)
                col3.metric("Failed", failed, delta=None if failed == 0 else f"-{failed}")
                col4.metric("Pass Rate", f"{pass_rate}%")
                st.progress(pass_rate / 100)

                # 失败详情
                if failed > 0:
                    st.subheader(f"Failed Cases ({failed})")
                    json_report = result.get("json_report", {})
                    for test in json_report.get("tests", []):
                        if test.get("outcome") == "failed":
                            nodeid = test.get("nodeid", "").split("::")[-1]
                            call = test.get("call", {})
                            st.error(f"**{nodeid}**")
                            st.code(call.get("longrepr", "")[:600])

        # --- Step 5: Analyze ---
        if "last_result" in st.session_state and st.session_state["last_result"]["failed"] > 0:
            st.header("5. Failure Analysis (LLM)")
            if st.button("Analyze Failures", key="btn_analyze"):
                with st.spinner("Analyzing with LLM..."):
                    last = st.session_state["last_result"]
                    json_report = last["result"].get("json_report", {})
                    endpoints = st.session_state.get("endpoints", [])

                    failures = []
                    for test in json_report.get("tests", []):
                        if test.get("outcome") != "failed":
                            continue
                        matched_ep = endpoints[0] if endpoints else {}
                        for ep in endpoints:
                            ep_file = f"test_{ep['method'].lower()}_{ep['path'].strip('/').replace('/', '_').replace('-', '_')}"
                            if ep_file in test.get("nodeid", ""):
                                matched_ep = ep
                                break
                        failures.append({
                            "endpoint": matched_ep,
                            "test_case": {"case_name": test.get("nodeid", "").split("::")[-1]},
                            "error": test.get("call", {}).get("longrepr", ""),
                        })

                    analysis = analyze_all_failures(failures, settings)
                    st.session_state["analysis"] = analysis

                    for ar in analysis:
                        a = ar.get("analysis", {})
                        severity_color = "red" if a.get("severity") == "critical" else "orange" if a.get("severity") == "major" else "blue"
                        with st.expander(f"{ar.get('case_name', '?')} — {a.get('failure_type', '?')}"):
                            st.markdown(f"**Root Cause:** {a.get('root_cause', '?')}")
                            st.markdown(f"**Severity:** :{severity_color}[{a.get('severity', '?')}]")
                            if a.get("suggestions"):
                                st.markdown("**Suggestions:**")
                                for s in a["suggestions"]:
                                    st.markdown(f"- {s}")


# ══════════════════════════════════════════════════════
# Page: History
# ══════════════════════════════════════════════════════

elif page == "History":
    st.title("Execution History")

    projects = list_projects()
    if not projects:
        st.info("No projects yet. Run a test first.")
    else:
        project_names = {p.id: p.name for p in projects}
        selected_pid = st.selectbox(
            "Project",
            options=[p.id for p in projects],
            format_func=lambda x: project_names.get(x, str(x)),
        )

        executions = list_executions(selected_pid, limit=20)
        if executions:
            # 趋势图
            trend = get_pass_rate_trend(selected_pid, limit=10)
            if trend:
                st.subheader("Pass Rate Trend")
                chart_data = pd.DataFrame(trend)
                st.line_chart(chart_data.set_index("time")["pass_rate"])

            # 历史表格
            st.subheader("Execution History")
            df = pd.DataFrame([
                {
                    "ID": e.id,
                    "Total": e.total,
                    "Passed": e.passed,
                    "Failed": e.failed,
                    "Rate": f"{e.pass_rate}%",
                    "Duration": f"{e.duration}s",
                    "LLM": "Yes" if e.is_llm_generated else "No",
                    "Time": e.created_at.isoformat()[:19] if e.created_at else "",
                }
                for e in executions
            ])
            st.dataframe(df, use_container_width=True)

            # 选中某次执行的详情
            selected_eid = st.selectbox("Select execution to view details", [e.id for e in executions])
            if selected_eid:
                for e in executions:
                    if e.id == selected_eid and e.stdout:
                        with st.expander("Pytest Output"):
                            st.code(e.stdout[:5000])
                        break
        else:
            st.info("No execution history for this project.")


# ══════════════════════════════════════════════════════
# Page: Projects
# ══════════════════════════════════════════════════════

elif page == "Projects":
    st.title("Projects")

    projects = list_projects()
    if projects:
        data = []
        for p in projects:
            trend = get_pass_rate_trend(p.id, limit=1)
            latest_rate = f"{trend[0]['pass_rate']}%" if trend else "N/A"
            data.append({
                "ID": p.id,
                "Name": p.name,
                "OpenAPI File": p.openapi_filename,
                "Latest Pass Rate": latest_rate,
                "Created": p.created_at.isoformat()[:19] if p.created_at else "",
            })
        st.dataframe(pd.DataFrame(data), use_container_width=True)
    else:
        st.info("No projects yet. Upload an OpenAPI document to get started.")
