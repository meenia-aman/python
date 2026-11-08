BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 3f12cbe68d2c

INSERT INTO alembic_version (version_num) VALUES ('3f12cbe68d2c') RETURNING alembic_version.version_num;

-- Running upgrade 3f12cbe68d2c -> 2f0a046efb79

CREATE TABLE products (
    id UUID NOT NULL, 
    category VARCHAR(11) NOT NULL, 
    price INTEGER NOT NULL, 
    stock_count INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_product_category CHECK (category IN ('CLOTHING', 'ELECTRONICS'))
);

CREATE TABLE users (
    id UUID NOT NULL, 
    name VARCHAR(50) NOT NULL, 
    email VARCHAR(255) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (email)
);

CREATE TABLE orders (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    product_id UUID NOT NULL, 
    total_amount INTEGER NOT NULL, 
    count INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE emails (
    id UUID NOT NULL, 
    user_id UUID NOT NULL, 
    order_id UUID NOT NULL, 
    status VARCHAR(7) DEFAULT 'PENDING' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT ck_email_status CHECK (status IN ('PENDING', 'SENT', 'FAILED'))
);

UPDATE alembic_version SET version_num='2f0a046efb79' WHERE alembic_version.version_num = '3f12cbe68d2c';

COMMIT;

