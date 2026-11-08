"""Script to generate an enhanced, user-friendly Excel template for DAG Forge."""

from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.comments import Comment
from openpyxl.utils import get_column_letter

def build_enhanced_template(output_path: str = "input_files/enhanced_starter.xlsx") -> None:
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    font_title = Font(name="Calibri", size=15, bold=True, color="1E293B")
    font_subtitle = Font(name="Calibri", size=11, italic=True, color="475569")
    font_section = Font(name="Calibri", size=12, bold=True, color="1E3A8A")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=10, bold=True, color="1E293B")
    font_regular = Font(name="Calibri", size=10, color="0F172A")
    font_code = Font(name="Consolas", size=9.5, color="0F172A")

    fill_navy = PatternFill("solid", fgColor="1E3A8A")       # Dag_config header
    fill_teal = PatternFill("solid", fgColor="0F766E")       # Task_details header
    fill_indigo = PatternFill("solid", fgColor="4338CA")     # Dependency_flow header
    fill_slate = PatternFill("solid", fgColor="334155")      # CheatSheet header
    fill_alt = PatternFill("solid", fgColor="F8FAFC")        # Zebra stripe
    fill_legend_req = PatternFill("solid", fgColor="DBEAFE") # Blue tint (required)
    fill_legend_opt = PatternFill("solid", fgColor="F1F5F9") # Gray tint (optional)
    fill_legend_rel = PatternFill("solid", fgColor="E0E7FF") # Indigo tint (links)

    border_thin = Side(border_style="thin", color="CBD5E1")
    box_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    bottom_double = Border(bottom=Side(border_style="double", color="94A3B8"))

    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_wrap_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    # -------------------------------------------------------------
    # 1. Sheet: Start here
    # -------------------------------------------------------------
    ws_start = wb.create_sheet(title="Start here")
    ws_start.views.sheetView[0].showGridLines = True

    ws_start["B2"] = "🔥 DAG Forge — Workflow Authoring Workbook"
    ws_start["B2"].font = font_title

    ws_start["B3"] = "Design Airflow workflows directly in Excel and compile them into dag-factory YAML configurations."
    ws_start["B3"].font = font_subtitle

    # Guide Table
    instructions = [
        ("Step 1: Set DAG Details", "Configure DAG ID, schedule, owner, and tags on the 'Dag_config' tab.", "Use dropdown for schedule_type (manual, preset, cron)."),
        ("Step 2: Add Tasks", "Define tasks on 'Task_details'. Pick operator from dropdown in 'task_type'.", "Enter primary spec in task_specs (e.g. bash command or python function)."),
        ("Step 3: Define Flow", "Specify execution order on 'Dependency_flow' by setting upstream_task_id.", "The upstream task completes before task_id runs."),
        ("Step 4: Validate & Build", "Run CLI commands from terminal to validate and generate YAML:", "dagforge validate input/starter.xlsx\ndagforge generate input/starter.xlsx -o output"),
        ("Reference: Instructions", "See the separate workbook 'input_files/operator_instructions.xlsx' for all 18 operators.", "Details primary payloads, required parameters, and copyable examples.")
    ]

    ws_start["B5"] = "Quick Start Guide"
    ws_start["B5"].font = font_section

    row = 6
    for step, desc, note in instructions:
        ws_start.cell(row=row, column=2, value=step).font = font_bold
        ws_start.cell(row=row, column=3, value=desc).font = font_regular
        ws_start.cell(row=row, column=4, value=note).font = font_code
        ws_start.cell(row=row, column=2).alignment = align_left
        ws_start.cell(row=row, column=3).alignment = align_wrap_left
        ws_start.cell(row=row, column=4).alignment = align_wrap_left
        for col in range(2, 5):
            ws_start.cell(row=row, column=col).border = box_border
        row += 1

    ws_start.column_dimensions["B"].width = 24
    ws_start.column_dimensions["C"].width = 50
    ws_start.column_dimensions["D"].width = 50

    # -------------------------------------------------------------
    # 2. Sheet: Dag_config
    # -------------------------------------------------------------
    ws_dag = wb.create_sheet(title="Dag_config")
    ws_dag.views.sheetView[0].showGridLines = True

    dag_headers = [
        ("dag_ref", "Key used across sheets to connect DAG config, tasks, and dependencies (e.g. 'pipeline_1')"),
        ("dag_id", "Airflow DAG identifier (letters, numbers, underscores)"),
        ("schedule_type", "Schedule type: manual, preset, cron, or exact (use dropdown)"),
        ("schedule", "Cron expression (e.g. '0 6 * * *') or preset ('@daily', '@hourly'). Leave blank for manual."),
        ("description", "Human-readable description of workflow"),
        ("default_args", "Comma-separated defaults (e.g. 'owner: data-team, start_date: 2024-01-01, retries: 1')"),
        ("tags", "Comma-separated tags for filtering in Airflow UI (e.g. 'etl, sales, prod')"),
        ("dag_parameters", "Optional DAG-level overrides (e.g. 'catchup: false, max_active_runs: 1')")
    ]

    for col_idx, (hdr, tooltip) in enumerate(dag_headers, start=1):
        cell = ws_dag.cell(row=1, column=col_idx, value=hdr)
        cell.font = font_header
        cell.fill = fill_navy
        cell.alignment = align_center
        cell.border = box_border
        cell.comment = Comment(tooltip, "DAG Forge")
        cell.comment.width = 260
        cell.comment.height = 70

    dag_sample_data = [
        ("sales_etl", "daily_sales_pipeline", "preset", "@daily", "Daily sales extract, transform and reporting", "owner: analytics, start_date: 2024-01-01, retries: 1", "sales, reporting, prod", "catchup: false"),
        ("sync_db", "hourly_db_sync", "cron", "0 * * * *", "Sync Postgres table changes to BigQuery", "owner: data-eng, start_date: 2024-01-01", "sync, postgres, bq", "max_active_runs: 1"),
        ("manual_maintenance", "weekly_db_vacuum", "manual", "", "Ad-hoc manual database maintenance pipeline", "owner: dba, start_date: 2024-01-01", "maintenance, db", "")
    ]

    for row_idx, row_data in enumerate(dag_sample_data, start=2):
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_dag.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_regular
            cell.border = box_border
            cell.alignment = align_left if col_idx != 3 else align_center

    # Data Validation: schedule_type dropdown
    dv_schedule = DataValidation(type="list", formula1='"manual,preset,cron,exact"', allow_blank=False)
    dv_schedule.error = "Please select a valid schedule type: manual, preset, cron, or exact."
    dv_schedule.errorTitle = "Invalid Schedule Type"
    dv_schedule.prompt = "Choose manual, preset, cron, or exact."
    dv_schedule.promptTitle = "Schedule Type"
    ws_dag.add_data_validation(dv_schedule)
    dv_schedule.add("C2:C100")

    # Column widths
    col_widths_dag = [16, 26, 16, 16, 36, 42, 24, 26]
    for idx, w in enumerate(col_widths_dag, start=1):
        ws_dag.column_dimensions[get_column_letter(idx)].width = w

    # -------------------------------------------------------------
    # 3. Sheet: Task_details
    # -------------------------------------------------------------
    ws_tasks = wb.create_sheet(title="Task_details")
    ws_tasks.views.sheetView[0].showGridLines = True

    task_headers = [
        ("dag_ref", "Must match a dag_ref defined in the Dag_config tab"),
        ("task_id", "Unique task name within this DAG (e.g. 'extract_api', 'run_sql')"),
        ("task_type", "Operator type (select from dropdown: bash, python, postgres, etc.)"),
        ("task_specs", "Main command / argument (e.g. bash command, python callable, sql query, container image)"),
        ("task_parameters", "Optional parameters as 'key: value, key2: value2' (see Operator_CheatSheet)")
    ]

    for col_idx, (hdr, tooltip) in enumerate(task_headers, start=1):
        cell = ws_tasks.cell(row=1, column=col_idx, value=hdr)
        cell.font = font_header
        cell.fill = fill_teal
        cell.alignment = align_center
        cell.border = box_border
        cell.comment = Comment(tooltip, "DAG Forge")
        cell.comment.width = 280
        cell.comment.height = 70

    task_sample_data = [
        ("sales_etl", "start", "empty", "", ""),
        ("sales_etl", "fetch_api", "http", "api/v2/orders", "method: GET, http_conn_id: sales_http"),
        ("sales_etl", "process_sales", "python", "pipelines.sales.process_daily_orders", "retries: 2"),
        ("sales_etl", "send_slack_alert", "slack", "", "channel: #pipeline-alerts, text: Daily sales ETL completed successfully"),
        ("sync_db", "check_pg_ready", "sql_sensor", "", "conn_id: postgres_prod, sql: SELECT 1 FROM sync_log WHERE status='ready'"),
        ("sync_db", "extract_pg", "postgres", "", "sql: SELECT * FROM orders WHERE updated_at >= NOW() - INTERVAL '1 hour'"),
        ("sync_db", "upload_gcs", "gcs_to_bigquery", "", "bucket: sales-landing-bucket, source_objects: orders.csv, destination_project_dataset_table: my_proj.sales.raw_orders"),
        ("manual_maintenance", "vacuum_db", "postgres", "", "sql: VACUUM ANALYZE")
    ]

    for row_idx, row_data in enumerate(task_sample_data, start=2):
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_tasks.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_code if col_idx in (2, 3, 4, 5) else font_regular
            cell.border = box_border
            cell.alignment = align_left if col_idx != 3 else align_center

    # Data Validation: task_type dropdown (18 operators)
    op_list_str = '"empty,bash,python,branch_python,short_circuit,http,email,slack,postgres,mysql,bigquery,docker,kubernetes_pod,gcs_to_bigquery,s3_to_gcs,sql_sensor,external_task_sensor,trigger_dag_run"'
    dv_op = DataValidation(type="list", formula1=op_list_str, allow_blank=False)
    dv_op.error = "Select a valid operator from the dropdown list."
    dv_op.errorTitle = "Invalid Operator"
    dv_op.prompt = "Choose from 18 supported Airflow operators."
    dv_op.promptTitle = "Operator Type"
    ws_tasks.add_data_validation(dv_op)
    dv_op.add("C2:C200")

    col_widths_tasks = [16, 22, 18, 38, 55]
    for idx, w in enumerate(col_widths_tasks, start=1):
        ws_tasks.column_dimensions[get_column_letter(idx)].width = w

    # -------------------------------------------------------------
    # 4. Sheet: Dependency_flow
    # -------------------------------------------------------------
    ws_deps = wb.create_sheet(title="Dependency_flow")
    ws_deps.views.sheetView[0].showGridLines = True

    dep_headers = [
        ("dag_ref", "Must match dag_ref defined in Dag_config"),
        ("task_id", "The downstream task that waits for upstream_task_id to finish"),
        ("upstream_task_id", "The prerequisite task that must succeed before task_id runs")
    ]

    for col_idx, (hdr, tooltip) in enumerate(dep_headers, start=1):
        cell = ws_deps.cell(row=1, column=col_idx, value=hdr)
        cell.font = font_header
        cell.fill = fill_indigo
        cell.alignment = align_center
        cell.border = box_border
        cell.comment = Comment(tooltip, "DAG Forge")
        cell.comment.width = 260
        cell.comment.height = 70

    dep_sample_data = [
        ("sales_etl", "fetch_api", "start"),
        ("sales_etl", "process_sales", "fetch_api"),
        ("sales_etl", "send_slack_alert", "process_sales"),
        ("sync_db", "extract_pg", "check_pg_ready"),
        ("sync_db", "upload_gcs", "extract_pg")
    ]

    for row_idx, row_data in enumerate(dep_sample_data, start=2):
        for col_idx, val in enumerate(row_data, start=1):
            cell = ws_deps.cell(row=row_idx, column=col_idx, value=val)
            cell.font = font_code if col_idx in (2, 3) else font_regular
            cell.border = box_border
            cell.alignment = align_left

    col_widths_deps = [18, 26, 26]
    for idx, w in enumerate(col_widths_deps, start=1):
        ws_deps.column_dimensions[get_column_letter(idx)].width = w

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    print(f"Successfully generated enhanced workbook: {output_path}")

if __name__ == "__main__":
    build_enhanced_template("input_files/enhanced_starter.xlsx")
