# DAG Forge 🔥

> **The Ultimate DAG Factory Development Toolkit for Apache Airflow Data Engineers**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Airflow 2.0+](https://img.shields.io/badge/airflow-2.0+-green.svg)](https://airflow.apache.org/)

**DAG Forge** is an open-source, production-grade Python toolkit that enables Data Engineers to author, validate, preview, and generate Apache Airflow DAGs from multiple input formats—including Excel spreadsheets, YAML, and JSON. 

By abstracting away raw Python DAG writing, DAG Forge enables business analysts, data scientists, and engineers to easily construct highly complex data pipelines without writing code. Under the hood, it converts your simplified pipeline requirements into 100% compliant `dag-factory` YAML configurations.

---

## 🚀 Key Features (Why DAG Forge?)

- 📊 **Excel-to-Airflow Pipeline Automation** — Empower non-engineers to design Airflow DAGs using structured Excel templates (`Dag_config`, `Task_details`, `Dependency_flow`).
- 🤖 **dag-factory Native Integration** — The output is perfectly valid `dag-factory` YAML. Drop it directly into your Airflow DAGs folder.
- ✅ **Deep Validation & Linting** — Validate parameters for 8+ critical Airflow operators before deployment. Catch typos, missing required variables, and invalid references early.
- 🔗 **Graph Analysis & Cycle Detection** — Built-in dependency cycle detection, topological sorting, and critical path highlighting prevents broken DAG deployments.
- 📐 **Jinja2 Template Engine** — Stop repeating yourself. Use built-in dynamic templates for common architectures (ETL pipelines, Sensor-Processor-Notify, Data Quality Checks).
- 🛡️ **Organizational Policy Engine** — Enforce enterprise-grade standards automatically. Require specific tags, enforce owners, and restrict manual schedules to maintain hygiene across your Airflow deployment.
- 🌍 **Environment Management** — Seamlessly inject `dev`, `staging`, or `prod` overlays onto your DAGs to dynamically rewrite connections, override pool sizes, or disable schedules in lower environments.
- 🔌 **Extensible Plugin Architecture** — Use Python `entry_points` to inject custom Parsers, Validators, Renderers, and Policies explicitly tailored to your organization.

## 🛠️ Operators Supported
DAG Forge deeply validates configurations for the following Airflow operators:
- **Compute/Bash:** `BashOperator`, `PythonOperator`, `EmptyOperator`, `BranchPythonOperator`, `ShortCircuitOperator`
- **Sensors:** `ExternalTaskSensor`, `SqlSensor`
- **Notifications & HTTP:** `EmailOperator`, `SlackAPIPostOperator`, `SimpleHttpOperator`
- **Databases:** `PostgresOperator`, `MySqlOperator`
- **Cloud & Modern Data Stack:** `BigQueryInsertJobOperator`, `GCSToBigQueryOperator`, `S3ToGCSOperator`
- **Containers:** `DockerOperator`, `KubernetesPodOperator`

---

## 📦 Installation

```bash
pip install dag-forge
```

---

## ⚡ Quick Start

### 1. Initialize a Project
Scaffold a standard DAG Forge project directory structure (`input/`, `output/`, `templates/`) and policy configuration (`dagforge.toml`):
```bash
dagforge init --dir my_data_project
cd my_data_project
```

### 2. Generate Airflow DAGs (dag-factory YAML)
Convert an Excel pipeline design document into deployable Airflow DAG definitions:
```bash
dagforge generate input/pipeline_design.xlsx -o output_yamls/
```

### 3. Apply Environment Overlays (Dev/Prod)
Deploying to production? Generate the DAG while dynamically applying the `prod` configuration overlay from `dagforge.toml`:
```bash
dagforge generate input/pipeline_design.xlsx -o output_yamls/ --env prod
```

### 4. Validate & Preview Before Deploying
Run deep validation and organization policy checks without generating files:
```bash
dagforge validate input/pipeline_design.xlsx
```
Preview the graph topology (DAG dependencies) directly in your terminal:
```bash
dagforge preview input/pipeline_design.xlsx
```

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
