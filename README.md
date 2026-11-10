# 🍳 Cloud Kitchen Multi-Brand P&L Intelligence Platform

An end-to-end Data Engineering and Analytics pipeline designed to calculate the **true contribution margin** of six virtual restaurant brands operating from a single shared commissary (cloud kitchen).

## 📌 The Business Problem
A cloud kitchen operates 6 virtual brands (Biryani, Burgers, Wok, etc.) from one physical location. They share the same staff, equipment, and ingredients, but list on multiple delivery platforms (Swiggy, Zomato, Uber Eats, Direct) with different commission structures. 

The business needed to answer: *Which brands are actually profitable after platform commissions, refunds, and shared cost allocation?*

## 🏗️ Architecture & Tech Stack
* **Infrastructure:** Docker (SQL Server 2025 Developer Edition)
* **Ingestion:** Python (`pandas`, `SQLAlchemy`, `pyodbc`)
* **Transformation:** dbt-sqlserver (Staging to Marts)
* **Orchestration:** Dagster
* **Business Intelligence:** Power BI Desktop (with custom DAX measures)
* **Data Quality:** dbt built-in testing (`not_null`, `relationships`)

## 🗂️ Data Model (Grain Matrix)
To prevent double-counting (the most common trap in P&L modeling), strict grains were enforced across the schema:
* `fact_orders`: 1 row per order
* `fact_payments`: 1 row per transaction
* `fact_refunds`: 1 row per refund event
* `fact_kitchen_cost_allocation`: 1 row per brand per hour

## 🧮 The P&L Formula (Activity-Based Costing)
The `fct_brand_daily_pnl` mart computes Net Margin dynamically using the following logic:

Net Margin = Net Revenue - Platform Commission - Gateway Fees - Refunds - Chargebacks - Allocated Labour - Allocated Utilities - Allocated Rent

## 🚧 Key Engineering Challenges Solved
1. **BOM Encoding Errors:** Wrote a PowerShell script to strip Byte Order Marks (BOM) from SQL files to prevent SQL Server syntax errors during dbt compilation.
2. **dbt Schema Routing:** Overrode dbt's default `generate_schema_name` macro to prevent it from concatenating schema names (e.g., `staging_marts`).
3. **Power BI SSPI Context Error:** Bypassed Windows Authentication (SSPI) failures on Docker containers by utilizing a custom ODBC connection string via Power Query.
4. **Docker SQL Server 2025:** Configured local Docker networking to bridge Python, dbt, and Power BI safely to the containerized database.

## 📊 Key Business Insights Uncovered
1. **The Revenue Illusion:** While the brands generate solid top-line revenue, the allocated shared kitchen overhead (labour, utilities, rent) is currently **2x** the total net revenue, resulting in a massive net loss.
2. **Platform Bleed:** Platform commissions (20-25%) are the second-largest expense. The data proves that shifting volume toward Direct (0% commission) orders is mathematically necessary to reach profitability.
3. **Failure Attribution:** The pipeline successfully isolated a "cold food" complaint on Brand B01. The P&L accurately absorbed the exact 200.00 refund and 50.00 chargeback fee, proving the model correctly attributes failure costs without diluting them across the kitchen.
