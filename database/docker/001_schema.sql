IF DB_ID(N'__MOSA_DATABASE__') IS NULL CREATE DATABASE [__MOSA_DATABASE__];
GO
USE [__MOSA_DATABASE__];
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

IF OBJECT_ID(N'dbo.Products', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.[Products]
    (
        [ProductId] int NOT NULL,
        [ProductCode] varchar(10) NOT NULL,
        [Name] nvarchar(200) NOT NULL,
        [NameVi] nvarchar(200) NULL,
        [Brand] nvarchar(100) NOT NULL,
        [Category] varchar(50) NOT NULL,
        [Color] varchar(50) NOT NULL,
        [Price] decimal(12,2) NOT NULL,
        [Stock] int NOT NULL,
        [Description] nvarchar(500) NULL,
        [DescriptionVi] nvarchar(500) NULL,
        [ImagePath] nvarchar(260) NOT NULL,
        [IsActive] bit NOT NULL CONSTRAINT [DF_Products_IsActive] DEFAULT ((1)),
        [UpdatedAt] datetime2(0) NOT NULL CONSTRAINT [DF_Products_UpdatedAt] DEFAULT (sysutcdatetime()),
        CONSTRAINT [PK_Products] PRIMARY KEY ([ProductId]),
        CONSTRAINT [UQ_Products_Code] UNIQUE ([ProductCode])
    );
END;
GO

IF OBJECT_ID(N'dbo.SearchEvents', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.[SearchEvents]
    (
        [SearchEventId] bigint IDENTITY(1,1) NOT NULL,
        [SearchMode] varchar(20) NOT NULL,
        [InputText] nvarchar(1000) NOT NULL CONSTRAINT [DF_SearchEvents_Input] DEFAULT (N''),
        [CandidateCount] int NOT NULL,
        [ResultJson] nvarchar(max) NOT NULL,
        [DurationMs] decimal(12,3) NOT NULL,
        [CreatedAt] datetime2(0) NOT NULL CONSTRAINT [DF_SearchEvents_CreatedAt] DEFAULT (sysutcdatetime()),
        CONSTRAINT [PK_SearchEvents] PRIMARY KEY ([SearchEventId])
    );
END;
GO

IF OBJECT_ID(N'dbo.ExternalProductStaging', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.[ExternalProductStaging]
    (
        [ExternalProductId] bigint IDENTITY(1,1) NOT NULL,
        [SourceName] nvarchar(100) NOT NULL,
        [SourceProductId] varchar(50) NOT NULL,
        [SourceUrl] nvarchar(1000) NOT NULL,
        [NameVi] nvarchar(500) NOT NULL,
        [Brand] nvarchar(300) NULL,
        [ProductType] nvarchar(200) NULL,
        [Category] varchar(50) NOT NULL,
        [Color] varchar(50) NULL,
        [ColorVi] nvarchar(100) NULL,
        [Price] decimal(18,2) NOT NULL,
        [IsAvailable] bit NOT NULL,
        [DescriptionVi] nvarchar(max) NULL,
        [ImageUrl] nvarchar(1000) NULL,
        [LocalImagePath] nvarchar(1000) NULL,
        [ImageRightsNote] nvarchar(1000) NULL,
        [SourceJson] nvarchar(max) NOT NULL,
        [ScrapedAt] datetime2(0) NOT NULL,
        [ImportedAt] datetime2(0) NOT NULL CONSTRAINT [DF_ExternalProductStaging_ImportedAt] DEFAULT (sysutcdatetime()),
        CONSTRAINT [PK_ExternalProductStaging] PRIMARY KEY ([ExternalProductId]),
        CONSTRAINT [UQ_ExternalProductStaging_Source] UNIQUE ([SourceName], [SourceProductId])
    );
END;
GO
