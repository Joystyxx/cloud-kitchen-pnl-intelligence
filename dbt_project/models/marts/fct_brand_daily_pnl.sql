WITH orders AS (
    SELECT brand_id, CAST(order_date AS DATE) AS date_key, order_id, net_revenue
    FROM {{ ref('stg_orders') }}
),
payments AS (
    SELECT order_id, SUM(platform_commission) AS platform_commission, SUM(payment_gateway_fee) AS payment_gateway_fee
    FROM {{ ref('stg_payments') }}
    GROUP BY order_id
),
refunds AS (
    SELECT order_id, SUM(refund_amount) AS refund_amount, SUM(chargeback_fee) AS chargeback_fee
    FROM {{ ref('stg_refunds') }}
    WHERE who_bears_cost = 'brand'
    GROUP BY order_id
),
daily_orders AS (
    SELECT 
        o.brand_id,
        o.date_key,
        SUM(o.net_revenue) AS net_revenue,
        SUM(p.platform_commission) AS platform_commission,
        SUM(p.payment_gateway_fee) AS payment_gateway_fee,
        SUM(COALESCE(r.refund_amount, 0)) AS refunds,
        SUM(COALESCE(r.chargeback_fee, 0)) AS chargebacks
    FROM orders o
    LEFT JOIN payments p ON o.order_id = p.order_id
    LEFT JOIN refunds r ON o.order_id = r.order_id
    GROUP BY o.brand_id, o.date_key
),
costs AS (
    SELECT brand_id, CAST(date_key AS DATE) AS date_key, allocated_labour, allocated_utilities, allocated_rent
    FROM {{ ref('stg_kitchen_costs') }}
)
SELECT 
    do.brand_id,
    do.date_key,
    do.net_revenue,
    do.platform_commission,
    do.payment_gateway_fee,
    do.refunds,
    do.chargebacks,
    COALESCE(c.allocated_labour, 0) AS allocated_labour,
    COALESCE(c.allocated_utilities, 0) AS allocated_utilities,
    COALESCE(c.allocated_rent, 0) AS allocated_rent,
    (do.net_revenue - do.platform_commission - do.payment_gateway_fee - do.refunds - do.chargebacks - COALESCE(c.allocated_labour, 0) - COALESCE(c.allocated_utilities, 0) - COALESCE(c.allocated_rent, 0)) AS net_margin
FROM daily_orders do
LEFT JOIN costs c ON do.brand_id = c.brand_id AND do.date_key = c.date_key