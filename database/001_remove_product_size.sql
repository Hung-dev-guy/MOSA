USE [ECommerceMultimodalV1];
GO

SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.ProductSize', N'U') IS NOT NULL
BEGIN
    DECLARE @sql nvarchar(max) = N'';

    SELECT @sql += N'ALTER TABLE '
        + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + N'.'
        + QUOTENAME(OBJECT_NAME(parent_object_id))
        + N' DROP CONSTRAINT ' + QUOTENAME(name) + N';'
    FROM sys.foreign_keys
    WHERE referenced_object_id = OBJECT_ID(N'dbo.ProductSize');

    EXEC sys.sp_executesql @sql;
    DROP TABLE dbo.ProductSize;
    PRINT N'Dropped dbo.ProductSize.';
END
ELSE
BEGIN
    PRINT N'dbo.ProductSize is already absent; no change required.';
END;

COMMIT TRANSACTION;
GO

