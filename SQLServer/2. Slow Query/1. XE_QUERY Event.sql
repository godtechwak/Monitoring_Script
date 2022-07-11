-- 조건 확인하여 변경
CREATE EVENT SESSION [XE_QUERY] ON SERVER 
ADD EVENT sqlserver.rpc_completed(
    ACTION(sqlserver.client_app_name,sqlserver.client_connection_id,sqlserver.client_hostname,sqlserver.database_name,sqlserver.session_id,sqlserver.sql_text,sqlserver.username)
    WHERE ([package0].[greater_than_uint64]([duration],(100000)) AND [sqlserver].[equal_i_sql_unicode_string]([sqlserver].[database_name],N'test') AND [sqlserver].[not_equal_i_sql_unicode_string]([sqlserver].[client_app_name],N'.Net SqlClient Data Provider') AND [sqlserver].[not_equal_i_sql_unicode_string]([sqlserver].[username],N'도메인\bhlee425') AND [sqlserver].[not_equal_i_sql_unicode_string]([sqlserver].[username],N'도메인\서비스계정'))),
ADD EVENT sqlserver.sql_batch_completed(
    ACTION(sqlserver.client_app_name,sqlserver.client_connection_id,sqlserver.client_hostname,sqlserver.database_name,sqlserver.session_id,sqlserver.sql_text,sqlserver.username)
    WHERE ([package0].[greater_than_uint64]([duration],(100000)) AND [sqlserver].[equal_i_sql_unicode_string]([sqlserver].[database_name],N'test') AND [sqlserver].[not_equal_i_sql_unicode_string]([sqlserver].[client_app_name],N'.Net SqlClient Data Provider') AND [sqlserver].[not_equal_i_sql_unicode_string]([sqlserver].[username],N'도메인\bhlee425') AND [sqlserver].[not_equal_i_sql_unicode_string]([sqlserver].[username],N'도메인\서비스계정')))
ADD TARGET package0.ring_buffer(SET max_memory=(2048))
WITH (MAX_MEMORY=16384 KB,EVENT_RETENTION_MODE=ALLOW_MULTIPLE_EVENT_LOSS,MAX_DISPATCH_LATENCY=30 SECONDS,MAX_EVENT_SIZE=0 KB,MEMORY_PARTITION_MODE=PER_CPU,TRACK_CAUSALITY=OFF,STARTUP_STATE=ON)
GO


