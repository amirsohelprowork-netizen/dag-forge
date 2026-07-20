import pandas as pd

# Dag_config
dags = [
    {"dag_ref": "DAG_1", "dag_id": "compute_dag", "schedule_type": "preset", "schedule": "daily", "description": "Compute tasks", "default_args": "owner: data-team, start_date: 2024-01-01", "tags": "compute, testing"},
    {"dag_ref": "DAG_2", "dag_id": "data_dag", "schedule_type": "cron", "schedule": "0 6 * * *", "description": "Data tasks", "default_args": "owner: data-team, start_date: 2024-01-01", "tags": "data, testing"},
    {"dag_ref": "DAG_3", "dag_id": "db_cloud_dag", "schedule_type": "manual", "schedule": "", "description": "DB and Cloud tasks", "default_args": "owner: data-team, start_date: 2024-01-01", "tags": "db, cloud"},
    {"dag_ref": "DAG_4", "dag_id": "container_dag", "schedule_type": "manual", "schedule": "", "description": "Container tasks", "default_args": "owner: data-team, start_date: 2024-01-01", "tags": "container, k8s"}
]

# Task_details
tasks = [
    # Compute
    {"dag_ref": "DAG_1", "task_id": "start", "task_type": "empty", "task_specs": "", "task_parameters": ""},
    {"dag_ref": "DAG_1", "task_id": "run_bash", "task_type": "bash", "task_specs": "echo 'hello'", "task_parameters": ""},
    {"dag_ref": "DAG_1", "task_id": "run_python", "task_type": "python", "task_specs": "my_module.my_func", "task_parameters": ""},
    {"dag_ref": "DAG_1", "task_id": "branch_task", "task_type": "branch_python", "task_specs": "my_module.branch_func", "task_parameters": ""},
    {"dag_ref": "DAG_1", "task_id": "short_circuit_task", "task_type": "short_circuit", "task_specs": "my_module.check_func", "task_parameters": ""},
    
    # Data
    {"dag_ref": "DAG_2", "task_id": "check_api", "task_type": "http", "task_specs": "api/v1/status", "task_parameters": "method: GET"},
    {"dag_ref": "DAG_2", "task_id": "send_email", "task_type": "email", "task_specs": "", "task_parameters": "to: admin@local, subject: Alert, html_content: <p>Hi</p>"},
    {"dag_ref": "DAG_2", "task_id": "send_slack", "task_type": "slack", "task_specs": "", "task_parameters": "channel: #general, text: Hello from Airflow"},
    {"dag_ref": "DAG_2", "task_id": "wait_for_dag", "task_type": "external_task_sensor", "task_specs": "", "task_parameters": "external_dag_id: compute_dag"},
    {"dag_ref": "DAG_2", "task_id": "trigger_other", "task_type": "trigger_dag_run", "task_specs": "db_cloud_dag", "task_parameters": ""},
    
    # DB & Cloud
    {"dag_ref": "DAG_3", "task_id": "wait_for_data", "task_type": "sql_sensor", "task_specs": "", "task_parameters": "conn_id: pg_default, sql: SELECT 1"},
    {"dag_ref": "DAG_3", "task_id": "run_pg", "task_type": "postgres", "task_specs": "", "task_parameters": "sql: SELECT * FROM users"},
    {"dag_ref": "DAG_3", "task_id": "run_mysql", "task_type": "mysql", "task_specs": "", "task_parameters": "sql: SELECT * FROM orders"},
    {"dag_ref": "DAG_3", "task_id": "s3_to_gcs_task", "task_type": "s3_to_gcs", "task_specs": "", "task_parameters": "source_bucket: s3-bucket, source_object: data.csv, destination_bucket: gcs-bucket"},
    {"dag_ref": "DAG_3", "task_id": "gcs_to_bq_task", "task_type": "gcs_to_bigquery", "task_specs": "", "task_parameters": "bucket: gcs-bucket, source_objects: data.csv, destination_project_dataset_table: project.dataset.table"},
    {"dag_ref": "DAG_3", "task_id": "run_bq", "task_type": "bigquery", "task_specs": "", "task_parameters": "configuration: SELECT 1"},
    
    # Container
    {"dag_ref": "DAG_4", "task_id": "run_docker", "task_type": "docker", "task_specs": "ubuntu:latest", "task_parameters": "container_name: my-container"},
    {"dag_ref": "DAG_4", "task_id": "run_k8s", "task_type": "kubernetes_pod", "task_specs": "ubuntu:latest", "task_parameters": "name: my-pod, namespace: default"}
]

# Dependency_flow
deps = [
    # Compute
    {"dag_ref": "DAG_1", "task_id": "run_bash", "upstream_task": "start"},
    {"dag_ref": "DAG_1", "task_id": "run_python", "upstream_task": "run_bash"},
    {"dag_ref": "DAG_1", "task_id": "branch_task", "upstream_task": "run_python"},
    {"dag_ref": "DAG_1", "task_id": "short_circuit_task", "upstream_task": "start"},
    
    # Data
    {"dag_ref": "DAG_2", "task_id": "send_email", "upstream_task": "check_api"},
    {"dag_ref": "DAG_2", "task_id": "send_slack", "upstream_task": "check_api"},
    {"dag_ref": "DAG_2", "task_id": "wait_for_dag", "upstream_task": "check_api"},
    {"dag_ref": "DAG_2", "task_id": "trigger_other", "upstream_task": "wait_for_dag"},
    
    # DB & Cloud
    {"dag_ref": "DAG_3", "task_id": "run_pg", "upstream_task": "wait_for_data"},
    {"dag_ref": "DAG_3", "task_id": "run_mysql", "upstream_task": "wait_for_data"},
    {"dag_ref": "DAG_3", "task_id": "s3_to_gcs_task", "upstream_task": "run_pg"},
    {"dag_ref": "DAG_3", "task_id": "gcs_to_bq_task", "upstream_task": "s3_to_gcs_task"},
    {"dag_ref": "DAG_3", "task_id": "run_bq", "upstream_task": "gcs_to_bq_task"},
    
    # Container
    {"dag_ref": "DAG_4", "task_id": "run_k8s", "upstream_task": "run_docker"}
]

with pd.ExcelWriter("input_files/all_operators.xlsx", engine="openpyxl") as writer:
    pd.DataFrame(dags).to_excel(writer, sheet_name="Dag_config", index=False)
    pd.DataFrame(tasks).to_excel(writer, sheet_name="Task_details", index=False)
    pd.DataFrame(deps).to_excel(writer, sheet_name="Dependency_flow", index=False)

print("Excel file created at input_files/all_operators.xlsx")
