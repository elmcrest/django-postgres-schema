CREATE OR REPLACE FUNCTION delete_schema(target_schema text) RETURNS void AS
$$
DECLARE
    schema_exists boolean;
    terminated_pid integer;
BEGIN
    SELECT EXISTS(
        SELECT 1 FROM information_schema.schemata 
        WHERE schema_name = target_schema
    ) INTO schema_exists;

    IF schema_exists THEN
        IF target_schema IN ('public', 'information_schema', 'pg_catalog', 'pg_toast') THEN
            RAISE EXCEPTION 'Cannot delete protected schema: %', target_schema;
        END IF;

        EXECUTE 'REVOKE ALL ON ALL TABLES IN SCHEMA ' || quote_ident(target_schema) || ' FROM PUBLIC CASCADE';
        EXECUTE 'REVOKE ALL ON SCHEMA ' || quote_ident(target_schema) || ' FROM PUBLIC CASCADE';

        FOR terminated_pid IN 
            SELECT pid::integer
            FROM pg_stat_activity 
            WHERE current_schema = target_schema
            AND pid != pg_backend_pid()
        LOOP
            PERFORM pg_terminate_backend(terminated_pid);
        END LOOP;

        EXECUTE 'DROP SCHEMA ' || quote_ident(target_schema) || ' CASCADE';
    END IF;

    RETURN;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE EXCEPTION 'Insufficient privileges to delete schema: %', target_schema;
    WHEN OTHERS THEN
        RAISE EXCEPTION 'Error deleting schema %: %', target_schema, SQLERRM;
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;