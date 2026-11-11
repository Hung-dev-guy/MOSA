-- PostgreSQL 17 schema for Mosa. Keeps existing text UUID/date and 0/1 API contracts.
-- Initialize tables only; does not import SQLite data or switch the application driver.
BEGIN;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),name TEXT NOT NULL,email TEXT NOT NULL UNIQUE,password TEXT NOT NULL,phone TEXT NOT NULL DEFAULT '',role TEXT NOT NULL DEFAULT 'customer',active BIGINT NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS reset_tokens(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),expires DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),name TEXT NOT NULL,description TEXT NOT NULL,brand TEXT NOT NULL,price BIGINT NOT NULL CHECK(price>0),selling_unit TEXT NOT NULL,attributes TEXT NOT NULL DEFAULT '{}',image TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'ARCHIVED' CHECK(status IN ('ACTIVE','ARCHIVED')),stock BIGINT NOT NULL DEFAULT 0 CHECK(stock>=0),origin TEXT,material TEXT,average_rating DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK(average_rating BETWEEN 0 AND 5),product_type TEXT CHECK(status <> 'ACTIVE' OR product_type IS NOT NULL) CHECK(product_type IN ('pen','notebook','bag','toy','book','electric_device')),created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),updated_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')));
CREATE TABLE IF NOT EXISTS carts(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),owner TEXT NOT NULL UNIQUE,customer_id TEXT UNIQUE REFERENCES users(id),status TEXT NOT NULL DEFAULT 'EMPTY' CHECK(status IN ('EMPTY','HAS_ITEMS')),created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),updated_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')));
CREATE TABLE IF NOT EXISTS cart_items(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),cart_id TEXT NOT NULL REFERENCES carts(id),product_id TEXT NOT NULL REFERENCES products(id),quantity BIGINT NOT NULL CHECK(quantity>0),unit_price BIGINT NOT NULL CHECK(unit_price>=0),created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),updated_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),UNIQUE(cart_id,product_id));
CREATE TABLE IF NOT EXISTS promotions(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),code TEXT UNIQUE NOT NULL,percent BIGINT CHECK(percent BETWEEN 1 AND 50),minimum BIGINT CHECK(minimum>=0),starts_at TEXT NOT NULL,ends_at TEXT NOT NULL,active BIGINT NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),user_id TEXT NOT NULL REFERENCES users(id),idem_key TEXT NOT NULL,request_hash TEXT NOT NULL,recipient TEXT NOT NULL,phone TEXT NOT NULL,address TEXT NOT NULL,subtotal BIGINT NOT NULL,discount BIGINT NOT NULL,shipping BIGINT NOT NULL,total BIGINT NOT NULL,promo TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,UNIQUE(user_id,idem_key));
CREATE TABLE IF NOT EXISTS order_items(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),order_id TEXT NOT NULL REFERENCES orders(id),product_id TEXT NOT NULL REFERENCES products(id),name TEXT NOT NULL,selling_unit TEXT NOT NULL,snapshot_details TEXT NOT NULL DEFAULT '{}',quantity BIGINT NOT NULL CHECK(quantity>0),price BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS payments(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),order_id TEXT NOT NULL UNIQUE REFERENCES orders(id),method TEXT NOT NULL CHECK(method IN ('COD','ONLINE')),status TEXT NOT NULL CHECK(status IN ('PENDING','PROCESSING','PAID','FAILED','REFUNDED')),reference TEXT NOT NULL,amount BIGINT NOT NULL CHECK(amount>=0),idempotency_key TEXT NOT NULL UNIQUE,failure_reason TEXT,created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),updated_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')));
CREATE TABLE IF NOT EXISTS payment_events(event_id TEXT PRIMARY KEY,order_id TEXT REFERENCES orders(id),result TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inventory_movements(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),product_id TEXT REFERENCES products(id),order_id TEXT REFERENCES orders(id),quantity BIGINT NOT NULL,kind TEXT NOT NULL,reason TEXT NOT NULL,actor TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS order_history(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),order_id TEXT REFERENCES orders(id),status TEXT NOT NULL,actor TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),user_id TEXT REFERENCES users(id),message TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),user_id TEXT NOT NULL REFERENCES users(id),product_id TEXT NOT NULL REFERENCES products(id),rating BIGINT NOT NULL CHECK(rating BETWEEN 1 AND 5),comment TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(user_id,product_id));
CREATE TABLE IF NOT EXISTS shipments(order_id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) REFERENCES orders(id),provider TEXT NOT NULL,tracking_code TEXT UNIQUE NOT NULL,status TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tracking_events(event_id TEXT PRIMARY KEY,order_id TEXT REFERENCES orders(id),status TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS service_cases(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),user_id TEXT REFERENCES users(id),order_id TEXT REFERENCES orders(id),product_id TEXT REFERENCES products(id),subject TEXT NOT NULL,message TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',reply TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS replenishments(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),supplier TEXT NOT NULL,product_id TEXT REFERENCES products(id),quantity BIGINT NOT NULL CHECK(quantity>0),status TEXT NOT NULL DEFAULT 'requested',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),actor TEXT NOT NULL,action TEXT NOT NULL,record TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inventory_reservations(order_id TEXT NOT NULL REFERENCES orders(id),product_id TEXT NOT NULL REFERENCES products(id),quantity BIGINT NOT NULL CHECK(quantity>0),PRIMARY KEY(order_id,product_id));
CREATE TABLE IF NOT EXISTS product_image(id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(id)=36),product_id TEXT NOT NULL REFERENCES products(id),image_url TEXT NOT NULL,is_primary BIGINT NOT NULL DEFAULT 0 CHECK(is_primary IN (0,1)),encoder_version TEXT,vector_reference TEXT,created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),UNIQUE(product_id,image_url));
CREATE UNIQUE INDEX IF NOT EXISTS one_primary_product_image ON product_image(product_id) WHERE is_primary=1;
CREATE TABLE IF NOT EXISTS pen(product_id TEXT PRIMARY KEY NOT NULL REFERENCES products(id),color TEXT,type TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS notebook(product_id TEXT PRIMARY KEY NOT NULL REFERENCES products(id),page_num BIGINT NOT NULL CHECK(page_num>0),size TEXT NOT NULL,type TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bag(product_id TEXT PRIMARY KEY NOT NULL REFERENCES products(id),size TEXT NOT NULL,pattern TEXT);
CREATE TABLE IF NOT EXISTS toy(product_id TEXT PRIMARY KEY NOT NULL REFERENCES products(id),type TEXT NOT NULL,minimum_age BIGINT CHECK(minimum_age>=0));
CREATE TABLE IF NOT EXISTS book(product_id TEXT PRIMARY KEY NOT NULL REFERENCES products(id),category TEXT NOT NULL,minimum_age BIGINT CHECK(minimum_age>=0),publisher TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS electric_device(product_id TEXT PRIMARY KEY NOT NULL REFERENCES products(id),minimum_age BIGINT CHECK(minimum_age>=0),weight BIGINT CHECK(weight>=0));
CREATE TABLE IF NOT EXISTS search_query(query_id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(query_id)=36),customer_id TEXT REFERENCES users(id),guest_owner TEXT,modality TEXT NOT NULL CHECK(modality IN ('TEXT','VOICE','IMAGE','MULTIMODAL')),raw_text TEXT,normalized_text TEXT,language TEXT,encoder_version TEXT,created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')));
CREATE TABLE IF NOT EXISTS search_filter(filter_id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(filter_id)=36),query_id TEXT NOT NULL REFERENCES search_query(query_id) ON DELETE CASCADE,filter_type TEXT NOT NULL CHECK(filter_type IN ('CATEGORY','BRAND','MIN_PRICE','MAX_PRICE','AVAILABLE','COLOR','SIZE','MINIMUM_AGE','PUBLISHER')),filter_value TEXT NOT NULL,is_explicit BIGINT NOT NULL DEFAULT 1,is_hard BIGINT NOT NULL DEFAULT 1,was_relaxed BIGINT NOT NULL DEFAULT 0,relaxation_order BIGINT,created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')));
CREATE TABLE IF NOT EXISTS search_result(result_id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(result_id)=36),query_id TEXT NOT NULL REFERENCES search_query(query_id) ON DELETE CASCADE,product_id TEXT NOT NULL REFERENCES products(id),rank_position BIGINT NOT NULL CHECK(rank_position>0),relevance_score DOUBLE PRECISION NOT NULL DEFAULT 0,preference_score DOUBLE PRECISION NOT NULL DEFAULT 0,final_score DOUBLE PRECISION NOT NULL DEFAULT 0,explanation TEXT,created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),UNIQUE(query_id,rank_position));
CREATE TABLE IF NOT EXISTS query_media(media_id TEXT PRIMARY KEY NOT NULL DEFAULT (gen_random_uuid()::text) CHECK(length(media_id)=36),query_id TEXT NOT NULL REFERENCES search_query(query_id) ON DELETE CASCADE,media_type TEXT NOT NULL CHECK(media_type IN ('IMAGE','VOICE')),storage_reference TEXT NOT NULL,mime_type TEXT,file_size_bytes BIGINT,created_at TEXT NOT NULL DEFAULT (to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"')),expires_at TEXT);
CREATE INDEX IF NOT EXISTS reservation_product ON inventory_reservations(product_id);
CREATE INDEX IF NOT EXISTS order_customer_date ON orders(user_id,created_at);
CREATE INDEX IF NOT EXISTS search_customer_date ON search_query(customer_id,created_at);
CREATE INDEX IF NOT EXISTS search_created ON search_query(created_at);
CREATE TABLE IF NOT EXISTS migration_archive(name TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS catalogue_sources(product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,source TEXT NOT NULL,source_product_id TEXT NOT NULL,source_variant_id TEXT NOT NULL,source_url TEXT NOT NULL,source_name TEXT NOT NULL,source_image_url TEXT NOT NULL,source_available BIGINT NOT NULL CHECK(source_available IN (0,1)),demo_available BIGINT NOT NULL CHECK(demo_available>0),imported_at TEXT NOT NULL,UNIQUE(source,source_variant_id));

-- Stable insertion order replaces SQLite's implicit rowid in existing queries.
-- These technical columns do not change product/order UUID primary keys.
ALTER TABLE products ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE cart_items ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE order_history ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE notifications ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE service_cases ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE inventory_movements ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE replenishments ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;
ALTER TABLE audit ADD COLUMN IF NOT EXISTS rowid BIGINT GENERATED ALWAYS AS IDENTITY;

CREATE OR REPLACE FUNCTION mosa_cart_changed() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE affected TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN affected := OLD.cart_id; ELSE affected := NEW.cart_id; END IF;
    UPDATE carts SET status = CASE WHEN EXISTS(SELECT 1 FROM cart_items WHERE cart_id=affected)
        THEN 'HAS_ITEMS' ELSE 'EMPTY' END,
        updated_at=to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"') WHERE id=affected;
    IF TG_OP = 'UPDATE' AND OLD.cart_id IS DISTINCT FROM NEW.cart_id THEN
        UPDATE carts SET status=CASE WHEN EXISTS(SELECT 1 FROM cart_items WHERE cart_id=OLD.cart_id)
            THEN 'HAS_ITEMS' ELSE 'EMPTY' END WHERE id=OLD.cart_id;
    END IF;
    RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS cart_changed ON cart_items;
CREATE TRIGGER cart_changed AFTER INSERT OR UPDATE OR DELETE ON cart_items FOR EACH ROW EXECUTE FUNCTION mosa_cart_changed();

CREATE OR REPLACE FUNCTION mosa_stock_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.stock < COALESCE((SELECT SUM(quantity) FROM inventory_reservations WHERE product_id=NEW.id),0) THEN
        RAISE EXCEPTION 'Stock below reserved quantity' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS stock_guard ON products;
CREATE TRIGGER stock_guard BEFORE UPDATE OF stock ON products FOR EACH ROW EXECUTE FUNCTION mosa_stock_guard();

CREATE OR REPLACE FUNCTION mosa_reservation_guard() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE physical BIGINT; held BIGINT;
BEGIN
    SELECT stock INTO physical FROM products WHERE id=NEW.product_id FOR UPDATE;
    SELECT COALESCE(SUM(quantity),0) INTO held FROM inventory_reservations WHERE product_id=NEW.product_id;
    IF TG_OP='UPDATE' AND OLD.product_id=NEW.product_id THEN held := held-OLD.quantity; END IF;
    IF held+NEW.quantity > physical THEN
        RAISE EXCEPTION 'Insufficient available stock' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS reservation_guard ON inventory_reservations;
CREATE TRIGGER reservation_guard BEFORE INSERT OR UPDATE ON inventory_reservations FOR EACH ROW EXECUTE FUNCTION mosa_reservation_guard();

CREATE OR REPLACE FUNCTION mosa_subtype_guard() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (SELECT product_type FROM products WHERE id=NEW.product_id) IS DISTINCT FROM TG_TABLE_NAME THEN
        RAISE EXCEPTION 'Product subtype mismatch' USING ERRCODE='23514';
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS pen_type_guard ON pen;
CREATE TRIGGER pen_type_guard BEFORE INSERT OR UPDATE ON pen FOR EACH ROW EXECUTE FUNCTION mosa_subtype_guard();
DROP TRIGGER IF EXISTS notebook_type_guard ON notebook;
CREATE TRIGGER notebook_type_guard BEFORE INSERT OR UPDATE ON notebook FOR EACH ROW EXECUTE FUNCTION mosa_subtype_guard();
DROP TRIGGER IF EXISTS bag_type_guard ON bag;
CREATE TRIGGER bag_type_guard BEFORE INSERT OR UPDATE ON bag FOR EACH ROW EXECUTE FUNCTION mosa_subtype_guard();
DROP TRIGGER IF EXISTS toy_type_guard ON toy;
CREATE TRIGGER toy_type_guard BEFORE INSERT OR UPDATE ON toy FOR EACH ROW EXECUTE FUNCTION mosa_subtype_guard();
DROP TRIGGER IF EXISTS book_type_guard ON book;
CREATE TRIGGER book_type_guard BEFORE INSERT OR UPDATE ON book FOR EACH ROW EXECUTE FUNCTION mosa_subtype_guard();
DROP TRIGGER IF EXISTS electric_device_type_guard ON electric_device;
CREATE TRIGGER electric_device_type_guard BEFORE INSERT OR UPDATE ON electric_device FOR EACH ROW EXECUTE FUNCTION mosa_subtype_guard();

CREATE OR REPLACE FUNCTION mosa_product_updated() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.updated_at IS NOT DISTINCT FROM OLD.updated_at THEN
        NEW.updated_at := to_char(CURRENT_TIMESTAMP AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"+00:00"');
    END IF;
    RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS product_updated ON products;
CREATE TRIGGER product_updated BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION mosa_product_updated();
COMMIT;
