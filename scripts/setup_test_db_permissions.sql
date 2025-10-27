-- ============================================================================
-- Script para configurar permissões de teste no MariaDB
-- ============================================================================
-- 
-- Este script concede ao usuário 'app' permissões necessárias para:
-- 1. Criar base de dados de teste (test_app)
-- 2. Executar migrations
-- 3. Criar/dropar tabelas durante testes
-- 4. Inserir/atualizar/deletar dados de teste
--
-- Uso:
--   docker exec -i mapsprovefiber-db-1 mariadb -u root -padmin < scripts/setup_test_db_permissions.sql
--
-- Ou interativamente:
--   docker exec -it mapsprovefiber-db-1 mariadb -u root -padmin
--   source /app/scripts/setup_test_db_permissions.sql
-- ============================================================================

-- Concede todas as permissões ao usuário 'app' para criar e gerenciar databases de teste
GRANT ALL PRIVILEGES ON *.* TO 'app'@'%' WITH GRANT OPTION;

-- Aplica as mudanças imediatamente
FLUSH PRIVILEGES;

-- Verifica as permissões concedidas
SHOW GRANTS FOR 'app'@'%';

-- Mensagem de confirmação
SELECT '✅ Permissões de teste configuradas com sucesso!' AS Status;
SELECT 'O usuário app agora pode criar/dropar databases de teste.' AS Info;
