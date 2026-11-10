IF DB_ID('cloud_kitchen_pnl') IS NULL
    CREATE DATABASE cloud_kitchen_pnl;
GO

USE cloud_kitchen_pnl;
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'raw') EXEC('CREATE SCHEMA raw');
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging') EXEC('CREATE SCHEMA staging');
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'marts') EXEC('CREATE SCHEMA marts');
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'validation') EXEC('CREATE SCHEMA validation');
GO