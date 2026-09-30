DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'llm_ro') THEN
    CREATE ROLE llm_ro LOGIN PASSWORD 'llm_ro_dev_pw';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE tickets TO llm_ro;
GRANT USAGE ON SCHEMA public TO llm_ro;
GRANT SELECT ON v_tickets TO llm_ro;