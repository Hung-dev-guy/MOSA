USE [ECommerceMultimodalV1];
GO

IF SCHEMA_ID(N'archive') IS NULL
    EXEC(N'CREATE SCHEMA archive AUTHORIZATION dbo;');

IF OBJECT_ID(N'archive.Products_20261103_BeforeAdcBookPromotion', N'U') IS NULL
    SELECT * INTO archive.Products_20261103_BeforeAdcBookPromotion FROM dbo.Products;
GO

