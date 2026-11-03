USE [ECommerceMultimodalV1];
GO

SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF SCHEMA_ID(N'archive') IS NULL
    EXEC(N'CREATE SCHEMA archive AUTHORIZATION dbo;');

IF OBJECT_ID(N'archive.Products_20261103_BeforeStationery', N'U') IS NULL
    SELECT * INTO archive.Products_20261103_BeforeStationery FROM dbo.Products;

UPDATE product
SET ProductCode = source.ProductCode,
    Name = source.Name,
    NameVi = source.NameVi,
    Brand = source.Brand,
    Category = source.Category,
    Color = source.Color,
    Price = source.Price,
    Stock = source.Stock,
    Description = source.Description,
    DescriptionVi = source.DescriptionVi,
    ImagePath = source.ImagePath,
    IsActive = 1,
    UpdatedAt = SYSUTCDATETIME()
FROM dbo.Products AS product
JOIN (VALUES
    (1,  'VP001', N'Thien Long TL-027 Gel Pen', N'Bút gel Thiên Long TL-027', N'Thiên Long', 'but-viet', 'blue', 6000.00, 120, N'Smooth 0.5 mm blue gel pen for study and office work.', N'Mực gel xanh 0,5 mm viết êm, khô nhanh, phù hợp học tập và văn phòng.', N'images/stationery/VP001.svg'),
    (2,  'VP002', N'Pastel Highlighter Set of 6', N'Bộ bút highlight pastel 6 màu', N'MOSA Select', 'but-viet', 'yellow', 45000.00, 48, N'Six soft pastel highlighters with a chisel tip.', N'Bộ 6 màu pastel dịu mắt, đầu vát linh hoạt để đánh dấu và lettering.', N'images/stationery/VP002.svg'),
    (3,  'VP003', N'FlexOffice FO-03 Ballpoint Pen', N'Bút bi FlexOffice FO-03', N'FlexOffice', 'but-viet', 'blue', 5000.00, 160, N'Reliable blue ballpoint pen with comfortable grip.', N'Bút bi mực xanh, tay cầm êm, nét đều cho nhu cầu sử dụng hằng ngày.', N'images/stationery/VP003.svg'),
    (4,  'VP004', N'A5 Leather Notebook', N'Sổ tay bìa da A5', N'MOSA Paper', 'so-giay', 'brown', 68000.00, 35, N'Premium A5 ruled notebook with an elastic closure.', N'Sổ A5 bìa da mềm, giấy kem chống lóa, có dây thun và đánh dấu trang.', N'images/stationery/VP004.svg'),
    (5,  'VP005', N'200-page Ruled Notebook', N'Vở kẻ ngang 200 trang', N'Hồng Hà', 'so-giay', 'blue', 28000.00, 75, N'B5 ruled notebook with bright, smooth paper.', N'Vở B5 200 trang, giấy trắng mịn, dòng kẻ rõ và đóng gáy chắc chắn.', N'images/stationery/VP005.svg'),
    (6,  'VP006', N'Five-color Pastel Sticky Notes', N'Giấy note pastel 5 màu', N'Deli', 'so-giay', 'yellow', 32000.00, 62, N'Five reusable pastel sticky-note pads for planning.', N'Bộ giấy ghi chú 5 màu pastel, độ bám tốt, tiện phân loại công việc.', N'images/stationery/VP006.svg'),
    (7,  'VP007', N'30 cm Transparent Ruler', N'Thước kẻ trong suốt 30 cm', N'Thiên Long', 'dung-cu', 'white', 12000.00, 94, N'Durable transparent 30 cm ruler with clear markings.', N'Thước nhựa trong 30 cm, vạch chia sắc nét, phù hợp học sinh và văn phòng.', N'images/stationery/VP007.svg'),
    (8,  'VP008', N'Stainless Steel Office Scissors', N'Kéo văn phòng thép không gỉ', N'Deli', 'dung-cu', 'grey', 38000.00, 41, N'Comfort-grip stainless steel scissors for paper and crafts.', N'Kéo lưỡi thép không gỉ, tay cầm êm, cắt giấy và vật liệu thủ công.', N'images/stationery/VP008.svg'),
    (9,  'VP009', N'Mini Stapler Set', N'Bộ bấm kim mini', N'Plus', 'dung-cu', 'red', 42000.00, 38, N'Compact stapler with remover and one box of staples.', N'Bộ bấm kim nhỏ gọn kèm gỡ kim và một hộp kim, tiện mang theo.', N'images/stationery/VP009.svg'),
    (10, 'VP010', N'A4 Lever Arch File 5 cm', N'Bìa còng A4 5 cm', N'King Jim', 'luu-tru', 'blue', 75000.00, 29, N'Five-centimeter A4 lever arch file for document storage.', N'Bìa còng A4 lưng 5 cm, khóa chắc chắn và có nhãn phân loại hồ sơ.', N'images/stationery/VP010.svg'),
    (11, 'VP011', N'Desktop Pen Organizer', N'Hộp đựng bút để bàn', N'MOSA Desk', 'do-ban', 'white', 95000.00, 24, N'Modular desktop organizer for pens, notes and small items.', N'Hộp đựng bút nhiều ngăn tối giản, giúp bàn học và bàn làm việc gọn gàng.', N'images/stationery/VP011.svg'),
    (12, 'VP012', N'Casio AX-120B Calculator', N'Máy tính Casio AX-120B', N'Casio', 'do-ban', 'black', 285000.00, 18, N'Twelve-digit desktop calculator with a large display.', N'Máy tính để bàn 12 chữ số, màn hình lớn, phím bền và dễ thao tác.', N'images/stationery/VP012.svg')
) AS source(ProductId, ProductCode, Name, NameVi, Brand, Category, Color, Price, Stock, Description, DescriptionVi, ImagePath)
    ON source.ProductId = product.ProductId;

IF (SELECT COUNT(*) FROM dbo.Products WHERE ProductCode LIKE 'VP%') <> 12
    THROW 51000, N'Catalog stationery update did not affect all 12 products.', 1;

COMMIT TRANSACTION;
GO

