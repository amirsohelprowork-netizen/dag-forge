# DAG Forge 🔥

> Author and check Airflow workflows using Excel, YAML, or JSON.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**DAG Forge** turns task lists and dependencies into dag-factory YAML for Apache Airflow. Teams can start from a spreadsheet, check task settings and organizational policies, and preview the workflow before handing the generated configuration to their Airflow team.

---

## 🚀 Key Features (Why DAG Forge?)

- 📊 **Excel-to-Airflow Pipeline Automation** — Empower non-engineers to design Airflow DAGs using structured Excel templates (`Dag_config`, `Task_details`, `Dependency_flow`).
- 🤖 **dag-factory Native Integration** — Generate YAML for an Airflow deployment configured to load it with dag-factory.
- ✅ **Deep Validation & Linting** — Validate parameters for 18 built-in Airflow operators before deployment. Catch typos, missing required variables, and invalid references early.
- 🔗 **Graph Analysis & Cycle Detection** — Inspect task order and critical paths, and catch dependency cycles before generation.
- 📐 **Jinja2 Template Engine** — Stop repeating yourself. Use built-in dynamic templates for common architectures (ETL pipelines, Sensor-Processor-Notify, Data Quality Checks).
- 🛡️ **Organizational Policy Engine** — Enforce enterprise-grade standards automatically. Require specific tags, enforce owners, and restrict manual schedules to maintain hygiene across your Airflow deployment.
- 🌍 **Environment Management** — Seamlessly inject `dev`, `staging`, or `prod` overlays onto your DAGs to dynamically rewrite connections, override pool sizes, or disable schedules in lower environments.
- 🧩 **Modular Operator Registry** — Natively supports 18 operators out-of-the-box. Easily extend the ecosystem by dropping a single Python specification file into the registry to support custom task types with deeply nested parameters.
- 🔌 **Extensible Plugin Architecture** — Use Python `entry_points` to inject custom Parsers, Validators, Renderers, and Policies explicitly tailored to your organization.

## 🛠️ Operators Supported
DAG Forge deeply validates configurations and complex nested parameters for 18 built-in Airflow operators out-of-the-box:
- **Compute/Bash:** `BashOperator`, `PythonOperator`, `EmptyOperator`, `BranchPythonOperator`, `ShortCircuitOperator`
- **Sensors:** `ExternalTaskSensor`, `SqlSensor`
- **Notifications & HTTP:** `EmailOperator`, `SlackAPIPostOperator`, `SimpleHttpOperator`
- **Databases:** `PostgresOperator`, `MySqlOperator`
- **Cloud & Modern Data Stack:** `BigQueryInsertJobOperator`, `GCSToBigQueryOperator`, `S3ToGCSOperator`
- **Containers:** `DockerOperator`, `KubernetesPodOperator`

---

## 📦 Installation

From the repository checkout with Python 3.11 or later, run:

```bash
python -m pip install .
```

---

## ⚡ Quick Start

### 1. Create a project and try the sample

```bash
dagforge init --dir my_data_project
cd my_data_project
dagforge validate input/starter.xlsx
dagforge generate input/starter.xlsx -o output
```

Open `input/starter.xlsx` and read the **Start here** tab. The sample starts with an empty task, then runs a Bash command that prints a greeting. It uses a manual schedule and requires no Airflow connections. The last command writes `output/starter_pipeline.yaml`.

### 2. Edit and check your workflow

- Set the DAG ID, owner, description, and tags in `Dag_config`.
- Set the tasks in `Task_details`. For `bash`, enter the shell command in `task_specs`. Enter optional settings such as `retries: 1` in `task_parameters`.
- Add a row per dependency in `Dependency_flow`. The task in `upstream_task` runs before the task in `task_id`. Use the same `dag_ref` on all three input tabs.

Save the workbook and rerun validation and generation. Excel diagnostics point to cells or sheets when available, for example `Task_details!D3` for a missing Bash command. Use `dagforge preview input/starter.xlsx` to inspect the task order.

Both commands use the validators and policies configured for the project. Run them from the project directory so they can read `dagforge.toml`. If you configure an environment overlay, use the same `--env prod` on both commands. Use `--strict` to fail on warnings. A parse failure stops generation for the whole input batch.

Load and test the generated YAML in your target Airflow and dag-factory environment before deploying it.

---

## 📐 Template Engine

Leverage Jinja2-powered abstractions to generate complex, standardized DAGs efficiently.

List available templates:
```bash
dagforge template list
```

Show template parameters (e.g., for the built-in ETL pipeline):
```bash
dagforge template show etl_pipeline
```

Interactively scaffold a DAG from a template:
```bash
dagforge template use etl_pipeline -o output/my_etl_dag.yaml
```

---

## 🔍 SEO Keywords
*Apache Airflow, Data Engineering, ETL Pipeline Generator, Excel to Airflow, dag-factory, DAG Automation, Data Pipeline Validation, Python Airflow Toolkit, DAG Dependency Graphing, Data Operations (DataOps).*

## 📄 License
This project is licensed under the MIT License. Feel free to use, modify, and distribute it as needed in both personal and commercial settings.
