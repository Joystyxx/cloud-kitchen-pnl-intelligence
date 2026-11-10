# 00 - Scope Lock

## 1. Brands

| brand_id | brand_name | cuisine | target_segment |
|---|---|---|---|
| B01 | Biryani House | Biryani / North Indian | Families, dinner |
| B02 | Wok Street | Chinese / Asian | Young professionals |
| B03 | Burger Lab | Burgers / Fast food | Students, late night |
| B04 | Dosa Corner | South Indian | Breakfast, health |
| B05 | Kebab Junction | Mughlai / Grills | Weekend, groups |
| B06 | Bowl & Co | Salads / Healthy bowls | Fitness, office lunch |

## 2. Platforms

| platform_id | platform_name | commission_rate | refund_policy | settlement_cadence | settlement_lag_days |
|---|---|---|---|---|---|
| P01 | Swiggy | 22% | Partial refund on cold/quality claims; chargeback fee charged to brand | Weekly (Monday) | 7 |
| P02 | Zomato | 20% | Partial refund on quality claims; chargeback fee charged to brand | Weekly (Tuesday) | 7 |
| P03 | Uber Eats | 25% | Full refund on non-delivery; partial on quality | Weekly (Wednesday) | 7 |
| P04 | Direct | 0% | Brand-owned; no platform arbitration | Instant | 0 |

## 3. Grain Matrix

**Rule:** Every fact table has exactly one declared grain. Every join must preserve it. Any model that needs a coarser grain must aggregate first.

| fact_table | grain | primary_key | fan-out risk | mitigation |
|---|---|---|---|---|
| fact_orders | One row per order | order_id | None (root) | n/a |
| fact_order_items | One row per item line in an order | order_id + item_id + line_no | Joining to fact_orders multiplies revenue by item count | Aggregate items to order first, or use order-level measures only from fact_orders |
| fact_payments | One row per payment transaction | payment_id | Split payments per order multiply order totals | Aggregate payments to order before joining to fact_orders |
| fact_refunds | One row per refund event | refund_id | Multiple partial refunds per order | Aggregate refunds to order; never sum per event into P&L without grouping |
| fact_settlements | One row per settlement line per platform | settlement_line_id | Settlement lines span multiple orders | Never join directly to order grain; use reconciliation bridge |
| fact_delivery_events | One row per delivery lifecycle event | event_id | Multiple events per order (assign, cancel, pickup, deliver) | Aggregate to order via event ordering; never sum numeric fields per event |
| fact_brand_daily_pnl | One row per brand per day | brand_id + date_key | None (derived mart) | Only joined to dim_date and dim_brand |
| fact_kitchen_cost_allocation | One row per brand per hour | brand_id + hour_key | 24 rows per brand per day | Aggregate to daily before joining to fact_brand_daily_pnl |
| fact_promotion_redemptions | One row per order-promotion application | order_id + promotion_id | Multiple promotions per order | Aggregate to order before P&L join |
| fact_cost_drivers | One row per driver event | driver_event_id | Many events per order (prep, equipment) | Aggregate to brand-hour before allocation |
| fact_chargeback_allocation | One row per allocated chargeback | allocation_id | Weekly settlements split across brands | Join only at brand-day grain to P&L |

## 4. Source-of-Truth Matrix

**Rule:** Every metric has exactly one authoritative source. Every other source is used only for reconciliation, never summed into the same metric.

| metric | authoritative source | used only for reconciliation | never summed with |
|---|---|---|---|
| Order gross revenue | fact_orders.gross_revenue | - | fact_payments.payment_amount |
| Order net revenue | fact_orders.net_revenue | - | fact_settlements.settlement_amount |
| Item-level revenue | fact_order_items.item_price * quantity | - | fact_orders (unless aggregated first) |
| COGS (direct) | fact_order_items.item_cost * quantity | - | fact_cost_drivers |
| Platform commission (accrual, P&L) | fact_payments.platform_commission | - | fact_settlements.commission_deducted |
| Payment gateway fee | fact_payments.payment_gateway_fee | - | fact_settlements.adjustment |
| Refund (P&L) | fact_refunds.refund_amount | fact_settlements (must reconcile within 1%) | - |
| Chargeback fee (P&L) | fact_chargeback_allocation.allocated_amount | fact_settlements.adjustment | - |
| Actual cash settled | - | fact_settlements.settlement_amount (reconciliation only) | fact_payments, fact_refunds |
| Allocated labour cost | fact_kitchen_cost_allocation.allocated_labour | Actual payroll (monthly reconciliation) | - |
| Allocated utilities | fact_kitchen_cost_allocation.allocated_utilities | Actual utility bills (monthly) | - |
| Brand contribution margin | fact_brand_daily_pnl.net_margin | - | Any ad-hoc recomputation |

**Ingestion pattern note:** Kaggle datasets (orders, payments, refunds, settlements, delivery events) are static snapshots - loaded once on Day 3. Synthetic kitchen cost data is generated daily via Dagster. Both land in raw.* before any transformation.

## 5. P&L Formula

**Frozen. Every engine (dbt, T-SQL, DAX, PySpark) must compute exactly this.**

Brand Contribution Margin (per brand per day) =

    Net Revenue
      = gross_revenue
      - customer_discounts
      - platform_funded_promotions

  - COGS (direct)
      = SUM(item_cost * quantity) from fact_order_items

  - COGS (allocated shared bases)
      = allocated portion from fact_kitchen_cost_allocation

  - Packaging
      = SUM(packaging_cost) from fact_order_items

  - Platform Commission (accrual)
      = fact_payments.platform_commission

  - Payment Gateway Fee
      = fact_payments.payment_gateway_fee

  - Delivery Cost (brand-borne portion only)
      = fact_orders.delivery_cost_brand_borne

  - Refunds (brand-borne portion only)
      = fact_refunds.refund_amount WHERE who_bears_cost = 'brand'

  - Chargeback Fees (allocated)
      = fact_chargeback_allocation.allocated_amount

  - Promotion Discount (brand-funded portion only)
      = fact_promotion_redemptions.discount_amount WHERE funded_by = 'brand'

  - Allocated Shared Costs
      = allocated_labour + allocated_utilities + allocated_rent
        from fact_kitchen_cost_allocation

**Definitions:**

- Gross Revenue = sum of item price x quantity before any discount.
- Net Revenue = gross revenue - customer-facing discounts - platform-funded promotions.
- Contribution Margin = as above (excludes fixed corporate costs, taxes).
- Net Margin = Contribution Margin - TDS - platform TDS deductions (from fact_settlements, reconciliation layer only).

## 6. Allocation Drivers

**Rule:** No driver, no allocation. Every allocated rupee traces to a measurable driver stored in fact_cost_drivers.

| cost_type | allocation_driver | driver_table | unit | allocation_frequency | reconciliation |
|---|---|---|---|---|---|
| Kitchen labour (staff wages) | Order prep minutes per brand | fact_cost_drivers (driver_type='prep_minutes') | minutes | Hourly | Monthly vs payroll +/-2% |
| Utilities - gas | Equipment usage minutes per brand | fact_cost_drivers (driver_type='gas_minutes') | minutes | Hourly | Monthly vs utility bill +/-5% |
| Utilities - electricity | Equipment usage minutes per brand | fact_cost_drivers (driver_type='electricity_minutes') | minutes | Hourly | Monthly vs utility bill +/-5% |
| Rent | Square footage dedicated to brand prep station | dim_brand (dedicated_sqft) | sq ft | Daily (fixed) | Monthly vs lease +/-1% |
| Packaging | Directly attributable per item | fact_order_items.packaging_cost | per item | Per order | Per-order check |
| Ingredients (direct) | Directly attributable per recipe | dim_recipe.standard_cost * quantity | per item | Per order | Weekly vs purchase log +/-3% |
| Shared base ingredients (rice, sauces) | Volume consumed per brand per day | fact_cost_drivers (driver_type='base_volume') | kg / litres | Daily | Daily vs morning prep log |
| Shared base preparation labour | Base prep minutes split by brand consumption share | fact_cost_drivers (driver_type='base_prep_minutes') | minutes | Daily | Weekly vs staff timesheet |

**Senior-question answer (Biryani base shared by B01 and B05):**
Base prep labour for the morning batch is allocated to each brand in proportion to that brand's consumption of the base that day. Consumption comes from fact_cost_drivers (driver_type = 'base_volume'). Allocation is stored in fact_kitchen_cost_allocation with allocation_method = 'abc_base_volume' and reconciled weekly against actual staff timesheets for the prep shift.

## 7. DQ Gates

**Rule:** These are hard gates. If any gate fails, the pipeline halts and the dashboard does NOT refresh.

| gate_id | gate_name | rule | failure_action | owner |
|---|---|---|---|---|
| DQ01 | Order item sum matches order total | SUM(item_price * quantity) = fact_orders.gross_revenue +/- 1 | Halt | dbt test |
| DQ02 | Payment sum matches order net | SUM(payment_amount) = fact_orders.net_revenue +/- 1 | Halt | dbt test |
| DQ03 | Refund never exceeds order value | refund_amount <= fact_orders.net_revenue | Halt | Great Expectations |
| DQ04 | Every payment has a matching order | fact_payments LEFT JOIN fact_orders -> 0 orphans | Halt | dbt test |
| DQ05 | Every settlement line traces to at least 1 order | fact_settlements unmatched = 0 | Warn + log | Great Expectations |
| DQ06 | Commission reconciliation | SUM(fact_payments.platform_commission) ~= SUM(fact_settlements.commission_deducted) +/-1% | Halt | dbt test |
| DQ07 | Refund reconciliation | SUM(fact_refunds.refund_amount) ~= SUM(fact_settlements.refund_adjustment) +/-1% | Warn + log | dbt test |
| DQ08 | Allocated labour reconciles to payroll | SUM(fact_kitchen_cost_allocation.allocated_labour) ~= payroll_monthly +/-2% | Halt | Great Expectations |
| DQ09 | Allocated utilities reconcile to bills | SUM(allocated_utilities) ~= utility_bill_monthly +/-5% | Halt | Great Expectations |
| DQ10 | No null brand_id in any fact | All fact tables: brand_id NOT NULL | Halt | dbt test |
| DQ11 | No negative revenue | fact_orders.net_revenue >= 0 | Halt | dbt test |
| DQ12 | No future-dated orders | order_date <= today | Warn + log | dbt test |
| DQ13 | Prep minutes allocated fully | SUM(allocated_prep_minutes) = total_prep_minutes for each day +/-0.1 | Halt | dbt test |
| DQ14 | Promotion funded split valid | funded_by IN ('platform','brand','shared') | Halt | dbt test |
| DQ15 | Grain preserved on marts | fact_brand_daily_pnl: COUNT(brand_id, date_key) = COUNT(DISTINCT brand_id, date_key) | Halt | dbt test |