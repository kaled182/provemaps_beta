-- ============================================================================
-- Script de Auditoria de Banco de Dados - Código Legado
-- Data: 2026-02-02
-- Propósito: Auditar estado antes de remoção de código legado
-- ============================================================================

-- ⚠️ IMPORTANTE: Execute no ambiente Docker
-- ═══════════════════════════════════════════════════════════════════════════
-- Todo o ecossistema do projeto funciona sob Docker, incluindo PostgreSQL + PostGIS.
-- Para executar este script:
--
--     # Via psql no container Docker:
--     docker compose -f docker/docker-compose.yml exec db psql -U mapsprovefiber -d mapsprovefiber -f /tmp/audit_legacy_database.sql
--
--     # Ou copiar para o container e executar:
--     docker compose -f docker/docker-compose.yml cp backend/tests/audit_legacy_database.sql db:/tmp/
--     docker compose -f docker/docker-compose.yml exec db psql -U mapsprovefiber -d mapsprovefiber -f /tmp/audit_legacy_database.sql

\echo '============================================================================'
\echo '🔍 AUDITORIA DE CÓDIGO LEGADO - BANCO DE DADOS'
\echo '============================================================================'

\echo ''
\echo '📊 1. VERIFICAÇÃO DE TABELAS LEGACY (zabbix_api_*)'
\echo '--------------------------------------------------------------------'

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public' 
  AND tablename LIKE 'zabbix_api_%'
ORDER BY tablename;

\echo ''
\echo '📊 2. COMPARAÇÃO DE CONTAGENS: Legacy vs Inventory'
\echo '--------------------------------------------------------------------'

-- Sites
\echo '   Sites:'
DO $$
DECLARE
    legacy_count INTEGER;
    inventory_count INTEGER;
BEGIN
    -- Tentar contar na tabela legacy (pode não existir)
    BEGIN
        SELECT COUNT(*) INTO legacy_count FROM zabbix_api_site;
    EXCEPTION WHEN undefined_table THEN
        legacy_count := 0;
    END;
    
    -- Contar na tabela inventory
    SELECT COUNT(*) INTO inventory_count FROM inventory_site;
    
    RAISE NOTICE '      Legacy (zabbix_api_site): %', legacy_count;
    RAISE NOTICE '      Inventory (inventory_site): %', inventory_count;
    
    IF legacy_count > 0 AND inventory_count >= legacy_count THEN
        RAISE NOTICE '      ✅ Dados migrados (inventory >= legacy)';
    ELSIF legacy_count > 0 THEN
        RAISE NOTICE '      ⚠️  ATENÇÃO: inventory tem menos registros que legacy!';
    ELSE
        RAISE NOTICE '      ✅ Tabela legacy não existe';
    END IF;
END $$;

-- Fiber Cables
\echo ''
\echo '   Fiber Cables:'
DO $$
DECLARE
    legacy_count INTEGER;
    inventory_count INTEGER;
BEGIN
    BEGIN
        SELECT COUNT(*) INTO legacy_count FROM zabbix_api_fibercable;
    EXCEPTION WHEN undefined_table THEN
        legacy_count := 0;
    END;
    
    SELECT COUNT(*) INTO inventory_count FROM inventory_fibercable;
    
    RAISE NOTICE '      Legacy (zabbix_api_fibercable): %', legacy_count;
    RAISE NOTICE '      Inventory (inventory_fibercable): %', inventory_count;
    
    IF legacy_count > 0 AND inventory_count >= legacy_count THEN
        RAISE NOTICE '      ✅ Dados migrados (inventory >= legacy)';
    ELSIF legacy_count > 0 THEN
        RAISE NOTICE '      ⚠️  ATENÇÃO: inventory tem menos registros que legacy!';
    ELSE
        RAISE NOTICE '      ✅ Tabela legacy não existe';
    END IF;
END $$;

\echo ''
\echo '📊 3. ANÁLISE DE CAMPOS DEPRECATED (coordinates vs path)'
\echo '--------------------------------------------------------------------'

SELECT 
    'Cabos com coordinates E path' AS categoria,
    COUNT(*) AS quantidade
FROM inventory_fibercable
WHERE coordinates IS NOT NULL 
  AND path IS NOT NULL

UNION ALL

SELECT 
    'Cabos APENAS com coordinates (⚠️ migração pendente)',
    COUNT(*)
FROM inventory_fibercable
WHERE coordinates IS NOT NULL 
  AND path IS NULL

UNION ALL

SELECT 
    'Cabos APENAS com path (✅ migrado)',
    COUNT(*)
FROM inventory_fibercable
WHERE coordinates IS NULL 
  AND path IS NOT NULL

UNION ALL

SELECT 
    'Cabos SEM coordenadas',
    COUNT(*)
FROM inventory_fibercable
WHERE coordinates IS NULL 
  AND path IS NULL;

\echo ''
\echo '📊 4. ANÁLISE DE UTILIZAÇÃO DE CAMPOS'
\echo '--------------------------------------------------------------------'

\echo '   Campo coordinates (JSONField - deprecated):'
SELECT 
    CASE 
        WHEN coordinates IS NULL THEN 'NULL (não usado)'
        WHEN jsonb_typeof(coordinates::jsonb) = 'array' THEN 'Array válido'
        ELSE 'Outro tipo'
    END AS tipo_dados,
    COUNT(*) AS quantidade
FROM inventory_fibercable
GROUP BY 1
ORDER BY 2 DESC;

\echo ''
\echo '   Campo path (PostGIS LineString - novo):'
SELECT 
    CASE 
        WHEN path IS NULL THEN 'NULL (não usado)'
        WHEN ST_GeometryType(path) = 'ST_LineString' THEN 'LineString válido'
        ELSE 'Outro tipo: ' || ST_GeometryType(path)
    END AS tipo_geometria,
    COUNT(*) AS quantidade,
    ROUND(AVG(ST_Length(path::geography))/1000, 2) AS avg_length_km
FROM inventory_fibercable
GROUP BY 1
ORDER BY 2 DESC;

\echo ''
\echo '📊 5. ANÁLISE DE ROTAS (routes_builder_* vs inventory_route*)'
\echo '--------------------------------------------------------------------'

-- Verificar tabelas de rotas
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public' 
  AND (tablename LIKE 'routes_builder_%' OR tablename LIKE 'inventory_route%')
ORDER BY tablename;

\echo ''
\echo '📊 6. ÍNDICES PostGIS'
\echo '--------------------------------------------------------------------'

SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND indexdef LIKE '%USING gist%'
ORDER BY tablename, indexname;

\echo ''
\echo '📊 7. DEPENDÊNCIAS DE TABELAS LEGACY'
\echo '--------------------------------------------------------------------'

-- Foreign keys que apontam para tabelas legacy
SELECT 
    tc.table_name AS dependent_table,
    kcu.column_name AS fk_column,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND ccu.table_name LIKE 'zabbix_api_%'
ORDER BY tc.table_name, kcu.column_name;

\echo ''
\echo '📊 8. ESTATÍSTICAS DE ARMAZENAMENTO'
\echo '--------------------------------------------------------------------'

SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
  AND (tablename LIKE 'inventory_%' OR tablename LIKE 'zabbix_api_%')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 20;

\echo ''
\echo '============================================================================'
\echo '✅ AUDITORIA CONCLUÍDA'
\echo '============================================================================'
\echo ''
\echo 'Próximos passos:'
\echo '  1. Revisar tabelas zabbix_api_* encontradas'
\echo '  2. Verificar dados não migrados (coordinates sem path)'
\echo '  3. Executar testes: pytest backend/tests/test_legacy_code_audit.py -v'
\echo '  4. Prosseguir com migração se tudo estiver OK'
\echo ''
