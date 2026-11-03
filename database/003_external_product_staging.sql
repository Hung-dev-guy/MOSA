USE [ECommerceMultimodalV1];
GO

IF OBJECT_ID(N'dbo.ExternalProductStaging', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.ExternalProductStaging
    (
        ExternalProductId bigint IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_ExternalProductStaging PRIMARY KEY,
        SourceName nvarchar(100) NOT NULL,
        SourceProductId varchar(50) NOT NULL,
        SourceUrl nvarchar(1000) NOT NULL,
        NameVi nvarchar(500) NOT NULL,
        Brand nvarchar(300) NULL,
        ProductType nvarchar(200) NULL,
        Category varchar(50) NOT NULL,
        Color varchar(50) NULL,
        ColorVi nvarchar(100) NULL,
        Price decimal(18,2) NOT NULL,
        IsAvailable bit NOT NULL,
        DescriptionVi nvarchar(max) NULL,
        ImageUrl nvarchar(1000) NULL,
        LocalImagePath nvarchar(1000) NULL,
        ImageRightsNote nvarchar(1000) NULL,
        SourceJson nvarchar(max) NOT NULL,
        ScrapedAt datetime2(0) NOT NULL,
        ImportedAt datetime2(0) NOT NULL
            CONSTRAINT DF_ExternalProductStaging_ImportedAt DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_ExternalProductStaging_Source UNIQUE (SourceName, SourceProductId)
    );
END;
GO

