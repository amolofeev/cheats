drop table if exists event_log;
create table event_log
(
    schema      text        not null,
    table_name  text        not null,
    operation   text        not null,
    pk          jsonb       not null,
    changes     jsonb       not null,
    created_at  timestamptz not null default current_timestamp,
    client_ip   text        not null,
    client_port int         not null,
    txid bigint not null,
    client text not null
);

CREATE OR REPLACE FUNCTION debug_function()
    RETURNS TRIGGER AS
$$
DECLARE
    diff       jsonb := '{}';
    pk_columns text[];
    pk_values  jsonb := '{}';
    col_record text;
    col_value  text;
BEGIN
    IF TG_OP = 'INSERT' THEN
        diff = row_to_json(NEW);
    END IF;

    IF TG_OP = 'UPDATE' THEN
        SELECT jsonb_object_agg(key, value)
        INTO diff
        FROM jsonb_each(to_jsonb(NEW)) AS new_data(key, value)
        WHERE new_data.value IS DISTINCT FROM (SELECT jsonb_extract_path(to_jsonb(OLD), new_data.key));
    END IF;
    IF TG_OP = 'DELETE' THEN
        diff = row_to_json(OLD);
    END IF;

    IF diff is not null then
        -- некоторая магия, чтобы получить PK вида {col: val, col:val}
        SELECT array_agg(a.attname)
        INTO pk_columns
        FROM pg_constraint c
                 JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
        WHERE c.conrelid = TG_RELID
          AND c.contype = 'p';
        FOREACH col_record IN ARRAY pk_columns
            LOOP
                EXECUTE format('SELECT ($1).%I::text', col_record)
                    INTO col_value
                    USING CASE WHEN TG_OP in ('DELETE', 'UPDATE') THEN OLD ELSE NEW END;
                pk_values = jsonb_set(pk_values, ARRAY [col_record], to_jsonb(col_value));
            END LOOP;
        -- пишем дифф в БД.
        insert into event_log(schema, table_name, operation, pk, changes, client_ip, client_port, txid, client)
        values (
                TG_TABLE_SCHEMA,
                TG_TABLE_NAME,
                TG_OP,
                pk_values,
                diff,
                inet_client_addr()::text,
                inet_client_port(),
                txid_current(),
                coalesce(current_setting('my_app.user_id', true), coalesce(current_setting('application_name', true), 'unknown')));
    end if;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- триггер надо вешать на каждую конкретную таблицу в тч всякие m2m для полноты картины, а так же на саму таблицу аудит лога.
CREATE TRIGGER test_event_log_on_users
    AFTER INSERT OR UPDATE OR DELETE
    ON users
    FOR EACH ROW
EXECUTE FUNCTION debug_function();

/*
set my_app.user_id = "xyz
insert/update/delete
*/