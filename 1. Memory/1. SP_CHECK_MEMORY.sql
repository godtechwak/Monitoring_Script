IF EXISTS(SELECT * FROM sysobjects WHERE name = 'SP_CHECK_MEMORY' AND xtype = 'P')
DROP PROC [dbo].[SP_CHECK_MEMORY]
GO
CREATE PROC [dbo].[SP_CHECK_MEMORY]  
@limit INT
AS        
 DECLARE @Text NVARCHAR(MAX)        
        ,@physical_memory_gb INT -- 시스템 물리 메모리        
        ,@committed_target_gb INT -- SQL Server 최대 메모리        
        ,@committed_gb INT -- SQL Server 현재 메모리        
        ,@available_physical_memory_gb INT -- 사용 가능한 메모리        
        ,@system_memory_state_desc VARCHAR(100)        
        ,@usage_percent INT        
 
 -- SQL Server 현재 메모리/SQL Server 최대 메모리
 SELECT @usage_percent = CEILING(((A.committed_kb * 1.0 / 1024 / 1024)/(A.committed_target_kb * 1.0 / 1024 / 1024) * 100))        
   FROM sys.dm_os_sys_info AS A         
        
 IF @usage_percent > @limit
 BEGIN        
     SELECT @physical_memory_gb = CEILING(A.physical_memory_kb * 1.0 / 1024 / 1024)         
           ,@committed_target_gb = CEILING(A.committed_target_kb * 1.0 / 1024 / 1024)        
           ,@committed_gb = CEILING(A.committed_kb * 1.0 / 1024 / 1024)         
           ,@available_physical_memory_gb = CEILING(B.available_physical_memory_kb * 1.0 / 1024 / 1024)        
           ,@system_memory_state_desc = system_memory_state_desc        
       FROM sys.dm_os_sys_info   as A         
      CROSS JOIN sys.dm_os_sys_memory as B        
        
     SELECT @Text = N'<게임웹DB 메모리 사용량>' + CHAR(10) +        
                    N'시스템 물리 메모리 = ' + CONVERT(NVARCHAR(3), @physical_memory_gb) + '(GB)' + CHAR(10) +        
                    N'SQL Server 최대 메모리 = ' +  CONVERT(NVARCHAR(3), @committed_target_gb) + '(GB)' + CHAR(10) +        
                    N'SQL Server 현재 메모리 = ' +  CONVERT(NVARCHAR(3), @committed_gb) + '(GB)' + CHAR(10) +        
                    N'사용 가능한 메모리 = ' +  CONVERT(NVARCHAR(3), @available_physical_memory_gb) + '(GB)' + CHAR(10) +        
                    N'메모리 사용율 = ' + CONVERT(NVARCHAR(3), @usage_percent) + '%' + CHAR(10) +        
                    N'시스템 메모리 상태 = ' +  @system_memory_state_desc        
                
          
	  EXEC msdb.dbo.sp_send_dbmail        
		   @profile_name = '프로필명',        
		   @recipients = 'test@naver.com',        
		   @Body = @Text,        
		   @subject = '[game_web] Memory Usage is High'        
 END
