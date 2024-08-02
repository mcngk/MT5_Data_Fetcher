-- SELECT * FROM public.mt5_db
-- ORDER BY "time" ASC, symbol ASC, "interval" ASC 

-- SELECT * FROM mt5_db WHERE interval = '15 minutes' 

-- ALTER TABLE mt5_db
-- ADD CONSTRAINT mt5_db_pkey PRIMARY KEY (time, symbol, interval);

-- CREATE TABLE crossover_dates_tb (
--     symbol VARCHAR(10),
--     date DATE
-- );

-- ALTER TABLE crossover_dates_tb
-- ADD CONSTRAINT unique_symbol_date UNIQUE (symbol, date);

-- ALTER TABLE crossover_dates_tb
-- ALTER COLUMN date TYPE timestamp USING date::timestamp;

-- SELECT * FROM public.crossover_dates_tb

-- DELETE FROM crossover_dates_tb;

-- ALTER TABLE crossover_dates_tb
-- ADD CONSTRAINT crossover_dates_tb_pkey PRIMARY KEY (date, symbol);


