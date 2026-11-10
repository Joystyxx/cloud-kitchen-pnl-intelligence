import pandas as pd
import numpy as np
import urllib.parse
from sqlalchemy import create_engine
from datetime import datetime, timedelta

# 1. Connect to SQL Server
password = urllib.parse.quote_plus("CloudKitchen#2025")
engine = create_engine(f"mssql+pyodbc://sa:{password}@localhost:1433/cloud_kitchen_pnl?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes")

print("Generating raw data...")
np.random.seed(42)
n_orders = 500

brands = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06']
platforms = ['P01', 'P02', 'P03', 'P04']

# 2. Generate fact_orders
orders = []
for i in range(1, n_orders + 1):
    brand = np.random.choice(brands)
    platform = np.random.choice(platforms)
    gross = round(np.random.uniform(150, 800), 2)
    disc = round(gross * np.random.uniform(0, 0.1), 2) if platform != 'P04' else 0
    net = gross - disc
    order_date = datetime.now() - timedelta(days=np.random.randint(0, 30))
    
    orders.append({
        'order_id': f'ORD{i:05d}',
        'brand_id': brand,
        'platform_id': platform,
        'order_date': order_date,
        'gross_revenue': gross,
        'net_revenue': net,
        'order_status': 'completed',
        'prep_time_minutes': np.random.randint(10, 30)
    })

# Inject the interview scenario: Swiggy, Brand A, cold food
orders[0].update({'brand_id': 'B01', 'platform_id': 'P01', 'order_status': 'refunded', 'gross_revenue': 500.0, 'net_revenue': 500.0})
df_orders = pd.DataFrame(orders)

# 3. Generate fact_payments
payments = []
for o in orders:
    comm_rate = 0.22 if o['platform_id'] == 'P01' else (0.20 if o['platform_id'] == 'P02' else (0.25 if o['platform_id'] == 'P03' else 0))
    comm = round(o['net_revenue'] * comm_rate, 2)
    gateway = round(o['net_revenue'] * 0.02, 2) if o['platform_id'] == 'P04' else 0
    
    payments.append({
        'payment_id': f'PAY{o["order_id"]}',
        'order_id': o['order_id'],
        'payment_amount': o['net_revenue'],
        'platform_commission': comm,
        'payment_gateway_fee': gateway
    })
df_payments = pd.DataFrame(payments)

# 4. Generate fact_refunds & chargebacks
refunds = [{
    'refund_id': 'REF001',
    'order_id': 'ORD00001',
    'refund_amount': 200.0, # 40% of 500
    'refund_reason': 'Cold food',
    'chargeback_fee': 50.0,
    'who_bears_cost': 'brand'
}]
df_refunds = pd.DataFrame(refunds)

# 5. Generate synthetic shared kitchen costs (fact_kitchen_cost_allocation)
costs = []
for i in range(30): # 30 days of data
    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    for b in brands:
        costs.append({
            'brand_id': b,
            'date_key': date,
            'allocated_labour': round(np.random.uniform(1000, 3000), 2),
            'allocated_utilities': round(np.random.uniform(200, 500), 2),
            'allocated_rent': 500.0,
            'allocation_method': 'abc_simulated'
        })
df_costs = pd.DataFrame(costs)

# 6. Load to SQL Server raw schema
print("Loading to SQL Server...")
df_orders.to_sql('fact_orders', engine, schema='raw', if_exists='replace', index=False)
df_payments.to_sql('fact_payments', engine, schema='raw', if_exists='replace', index=False)
df_refunds.to_sql('fact_refunds', engine, schema='raw', if_exists='replace', index=False)
df_costs.to_sql('fact_kitchen_cost_allocation', engine, schema='raw', if_exists='replace', index=False)

print("Success! Raw data loaded into SQL Server.")