"""Generate a standalone Operator Instructions & Parameter Reference workbook."""

from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from dagforge.operators import operator_registry

def build_operator_instructions(output_path: str = "input_files/operator_instructions.xlsx") -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # Remove default sheet

    # Typography & Styles
    font_title = Font(name="Calibri", size=15, bold=True, color="0F172A")
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="475569")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True, color="0F172A")
    font_regular = Font(name="Calibri", size=10, color="0F172A")
    font_code = Font(name="Consolas", size=9.5, color="0F172A")
    font_badge_req = Font(name="Calibri", size=9.5, bold=True, color="991B1B")
    font_badge_opt = Font(name="Calibri", size=9.5, color="166534")

    fill_navy = PatternFill("solid", fgColor="1E3A8A")
    fill_teal = PatternFill("solid", fgColor="0F766E")
    fill_slate = PatternFill("solid", fgColor="334155")
    fill_alt = PatternFill("solid", fgColor="F8FAFC")
    fill_req = PatternFill("solid", fgColor="FEE2E2")
    fill_opt = PatternFill("solid", fgColor="DCFCE7")

    border_thin = Side(border_style="thin", color="CBD5E1")
    box_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # ------------------------------------------------------------------
    # Sheet 1: Overview & Rules
    # ------------------------------------------------------------------
    ws_ov = wb.create_sheet(title="Overview & Rules")
    ws_ov.views.sheetView[0].showGridLines = True

    ws_ov["B2"] = "📘 DAG Forge — Operator Specifications & Parameters Guide"
    ws_ov["B2"].font = font_title
    ws_ov["B3"] = "Standalone reference explaining primary payloads (task_specs) vs key-value parameters (task_parameters)."
    ws_ov["B3"].font = font_subtitle

    ws_ov["B5"] = "Core Principles"
    ws_ov["B5"].font = font_section

    rules = [
        ("1. Primary Payload (task_specs)", "What it is", "The single primary command, callable, image, SQL query, or endpoint that the operator fundamentally runs."),
        ("", "How to use", "Enter the exact string directly in 'task_specs'. Preserves quotes, commas, and formatting without splitting."),
        ("", "When to leave blank", "If an operator has no single primary argument (e.g. empty, slack, email, bigquery, sensors), leave task_specs completely blank."),
        ("2. Parameters (task_parameters)", "What it is", "All supporting settings, connection IDs, timeouts, retries, and extra arguments."),
        ("", "Syntax", "Comma-separated key-value pairs: 'key1: value1, key2: value2'. Values are auto-cast to int, bool, or string."),
        ("", "Multiple Pairs", "Simply separate with commas, for example: 'retries: 2, pool: etl_pool, timeout: 1800'."),
        ("3. Airflow Resolution", "dag-factory output", "DAG Forge merges task_specs (under its proper operator argument name) with task_parameters into a unified parameter dict.")
    ]

    row_idx = 6
    for section, col2, col3 in rules:
        ws_ov.cell(row=row_idx, column=2, value=section).font = font_bold if section else font_regular
        ws_ov.cell(row=row_idx, column=3, value=col2).font = font_bold
        ws_ov.cell(row=row_idx, column=4, value=col3).font = font_regular
        ws_ov.cell(row=row_idx, column=2).alignment = align_left
        ws_ov.cell(row=row_idx, column=3).alignment = align_left
        ws_ov.cell(row=row_idx, column=4).alignment = align_wrap
        for c in range(2, 5):
            ws_ov.cell(row=row_idx, column=c).border = box_border
        row_idx += 1

    ws_ov.column_dimensions["B"].width = 28
    ws_ov.column_dimensions["C"].width = 24
    ws_ov.column_dimensions["D"].width = 75

    # ------------------------------------------------------------------
    # Sheet 2: Primary_Payload_Guide (task_specs)
    # ------------------------------------------------------------------
    ws_prim = wb.create_sheet(title="Primary_Payloads")
    ws_prim.views.sheetView[0].showGridLines = True

    prim_headers = [
        "Task Type (task_type)",
        "Primary Airflow Param",
        "Required in task_specs?",
        "What It Expects in task_specs",
        "Concrete Example Value"
    ]

    for col_idx, h in enumerate(prim_headers, start=1):
        cell = ws_prim.cell(row=1, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_teal
        cell.alignment = align_center
        cell.border = box_border

    primary_payload_data = [
        ("bash", "bash_command", "Yes", "Shell script or command to execute", 'echo "Hello World"'),
        ("python", "python_callable", "Yes", "Import path of Python callable", "my_module.my_functions.run_etl"),
        ("branch_python", "python_callable", "Yes", "Callable path that returns downstream task_id", "my_module.branching.choose_path"),
        ("short_circuit", "python_callable", "Yes", "Callable path returning boolean True/False", "my_module.checks.is_data_available"),
        ("http", "endpoint", "Yes", "Relative URL path for the API endpoint", "api/v2/orders/daily"),
        ("postgres", "sql", "Yes", "SQL statement or path to .sql file", "SELECT * FROM sales WHERE status = 'complete'"),
        ("mysql", "sql", "Yes", "SQL statement or path to .sql file", "SELECT count(*) FROM orders"),
        ("docker", "image", "Yes", "Container image name with tag", "python:3.11-slim"),
        ("kubernetes_pod", "image", "Yes", "Container image name with tag", "apache/spark:3.5.0"),
        ("trigger_dag_run", "trigger_dag_id", "Yes", "Target DAG ID to trigger", "downstream_analytics_dag"),
        ("empty", "(None)", "No — leave blank", "EmptyOperator has no primary payload", "(blank)"),
        ("email", "(None)", "No — leave blank", "All parameters (to, subject, html_content) go in task_parameters", "(blank)"),
        ("slack", "(None)", "No — leave blank", "All parameters (channel, text) go in task_parameters", "(blank)"),
        ("bigquery", "(None)", "No — leave blank", "Job configuration dictionary goes in task_parameters", "(blank)"),
        ("gcs_to_bigquery", "(None)", "No — leave blank", "Transfer parameters go in task_parameters", "(blank)"),
        ("s3_to_gcs", "(None)", "No — leave blank", "Transfer parameters go in task_parameters", "(blank)"),
        ("sql_sensor", "(None)", "No — leave blank", "conn_id and sql query go in task_parameters", "(blank)"),
        ("external_task_sensor", "(None)", "No — leave blank", "external_dag_id & task_id go in task_parameters", "(blank)")
    ]

    for row_idx, row_vals in enumerate(primary_payload_data, start=2):
        row_fill = fill_alt if row_idx % 2 == 0 else PatternFill(fill_type=None)
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws_prim.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_code if col_idx in (1, 2, 5) else font_regular
            cell.border = box_border
            if row_fill.fill_type:
                cell.fill = row_fill
            if col_idx in (1, 2):
                cell.alignment = align_center
            elif col_idx == 3:
                cell.alignment = align_center
                if val == "Yes":
                    cell.fill = fill_req
                    cell.font = font_badge_req
                else:
                    cell.fill = fill_opt
                    cell.font = font_badge_opt
            else:
                cell.alignment = align_wrap

    col_widths_prim = [22, 24, 24, 45, 45]
    for idx, w in enumerate(col_widths_prim, start=1):
        ws_prim.column_dimensions[get_column_letter(idx)].width = w

    # ------------------------------------------------------------------
    # Sheet 3: Parameters_Reference (task_parameters)
    # ------------------------------------------------------------------
    ws_params = wb.create_sheet(title="Parameters_Reference")
    ws_params.views.sheetView[0].showGridLines = True

    param_headers = [
        "Task Type",
        "Parameter Name",
        "Expected Type",
        "Where to Put It",
        "Required?",
        "Default Value",
        "Description & Syntax Example"
    ]

    for col_idx, h in enumerate(param_headers, start=1):
        cell = ws_params.cell(row=1, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = box_border

    row_idx = 2
    for op_key in sorted(operator_registry._specs.keys()):
        spec = operator_registry.get(op_key)
        for p in spec.params:
            is_primary = (p.name == spec.task_specs_param)
            placement = "task_specs" if is_primary else "task_parameters"
            req_str = "Required" if p.required else "Optional"
            default_str = str(p.default) if p.default is not None else "(none)"
            desc_example = p.description or ""

            ws_params.cell(row=row_idx, column=1, value=op_key).font = font_code
            ws_params.cell(row=row_idx, column=2, value=p.name).font = font_code
            ws_params.cell(row=row_idx, column=3, value=p.type).font = font_code
            ws_params.cell(row=row_idx, column=4, value=placement).font = font_bold
            ws_params.cell(row=row_idx, column=5, value=req_str).font = font_badge_req if p.required else font_badge_opt
            ws_params.cell(row=row_idx, column=6, value=default_str).font = font_code
            ws_params.cell(row=row_idx, column=7, value=desc_example).font = font_regular

            for c in range(1, 8):
                ws_params.cell(row=row_idx, column=c).border = box_border
                if c in (1, 2, 3, 4, 5, 6):
                    ws_params.cell(row=row_idx, column=c).alignment = align_center
                else:
                    ws_params.cell(row=row_idx, column=c).alignment = align_wrap

            if p.required:
                ws_params.cell(row=row_idx, column=5).fill = fill_req
            else:
                ws_params.cell(row=row_idx, column=5).fill = fill_opt

            row_idx += 1

    col_widths_params = [18, 24, 16, 18, 14, 20, 60]
    for idx, w in enumerate(col_widths_params, start=1):
        ws_params.column_dimensions[get_column_letter(idx)].width = w

    # ------------------------------------------------------------------
    # Sheet 4: Complete_Examples
    # ------------------------------------------------------------------
    ws_ex = wb.create_sheet(title="Complete_Examples")
    ws_ex.views.sheetView[0].showGridLines = True

    ex_headers = [
        "Task Type",
        "Airflow Class",
        "Sample task_specs",
        "Sample task_parameters (key: value pairs)"
    ]

    for col_idx, h in enumerate(ex_headers, start=1):
        cell = ws_ex.cell(row=1, column=col_idx, value=h)
        cell.font = font_header
        cell.fill = fill_slate
        cell.alignment = align_center
        cell.border = box_border

    examples_data = [
        ("bash", "BashOperator", 'echo "Running step 1"', 'retries: 2, env: {"ENV": "prod"}'),
        ("python", "PythonOperator", "pipelines.etl.run_batch", "op_kwargs: {'batch_size': 1000}, retries: 1"),
        ("branch_python", "BranchPythonOperator", "pipelines.logic.decide_branch", "op_args: ['staging']"),
        ("short_circuit", "ShortCircuitOperator", "pipelines.checks.is_active", "ignore_downstream_trigger_rules: false"),
        ("http", "SimpleHttpOperator", "api/v2/orders", "method: GET, http_conn_id: sales_http_conn"),
        ("postgres", "PostgresOperator", "SELECT * FROM users", "postgres_conn_id: pg_warehouse, autocommit: true"),
        ("mysql", "MySqlOperator", "SELECT count(*) FROM orders", "mysql_conn_id: mysql_warehouse"),
        ("docker", "DockerOperator", "python:3.11-slim", "container_name: etl_runner, auto_remove: true"),
        ("kubernetes_pod", "KubernetesPodOperator", "apache/spark:3.5.0", "name: spark_job, namespace: default, in_cluster: true"),
        ("trigger_dag_run", "TriggerDagRunOperator", "downstream_pipeline", "wait_for_completion: true, reset_dag_run: false"),
        ("empty", "EmptyOperator", "", "retries: 0"),
        ("slack", "SlackAPIPostOperator", "", "channel: #alerts, text: Pipeline completed successfully, slack_conn_id: slack_default"),
        ("email", "EmailOperator", "", "to: team@example.com, subject: Alert, html_content: <p>Completed</p>"),
        ("bigquery", "BigQueryInsertJobOperator", "", "configuration: {'query': {'query': 'SELECT 1', 'useLegacySql': False}}"),
        ("gcs_to_bigquery", "GCSToBigQueryOperator", "", "bucket: raw_bucket, source_objects: data.csv, destination_project_dataset_table: prj.ds.tbl"),
        ("s3_to_gcs", "S3ToGCSOperator", "", "source_bucket: s3_raw, source_object: file.csv, destination_bucket: gcs_raw"),
        ("sql_sensor", "SqlSensor", "", "conn_id: pg_conn, sql: SELECT 1 FROM ready_flag, poke_interval: 60, timeout: 1800"),
        ("external_task_sensor", "ExternalTaskSensor", "", "external_dag_id: upstream_dag, external_task_id: final_step, timeout: 3600")
    ]

    for row_idx, row_vals in enumerate(examples_data, start=2):
        row_fill = fill_alt if row_idx % 2 == 0 else PatternFill(fill_type=None)
        for col_idx, val in enumerate(row_vals, start=1):
            cell = ws_ex.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_code if col_idx in (1, 3, 4) else font_regular
            cell.border = box_border
            if row_fill.fill_type:
                cell.fill = row_fill
            cell.alignment = align_left if col_idx != 1 else align_center

    col_widths_ex = [20, 26, 32, 65]
    for idx, w in enumerate(col_widths_ex, start=1):
        ws_ex.column_dimensions[get_column_letter(idx)].width = w

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    print(f"Generated standalone operator instructions workbook: {output_path}")

if __name__ == "__main__":
    build_operator_instructions("input_files/operator_instructions.xlsx")
