USE [ECommerceMultimodalV1];
GO

UPDATE dbo.Products
SET IsActive = 0,
    UpdatedAt = SYSUTCDATETIME()
WHERE ProductCode LIKE 'VP%';
GO

