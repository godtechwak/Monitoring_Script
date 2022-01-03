IF EXISTS(SELECT * FROM sysobjects WHERE name = 'SP_CHECK_CPU_USAGE' AND xtype = 'P')
DROP PROC SP_CHECK_CPU_USAGE
GO
CREATE   PROCEDURE SP_CHECK_CPU_USAGE  
AS  
  
 DECLARE @tablehtml VARCHAR(MAX)  
 DECLARE @cpu_check TABLE    
 (    
  record_id   INT PRIMARY KEY,    
  record_time DATETIME,    
  system_idle INT,    
  sql_server  INT,    
  os_process  INT,    
  total_used  INT    
 )    
  
 INSERT INTO @cpu_check  
 SELECT record_id     
    ,CAST(CONVERT(CHAR(16), record_time, 20) AS DATETIME) AS [record_time]  
    ,systemidle               AS [System Idle]  
    ,sqlsvcutilization          AS [SQL Server CPU Usage]  
    ,(100 - systemidle - sqlsvcutilization)        AS [OS CPU Usage]    
    ,(100 - systemidle)             AS [Total CPU Usage]  
   FROM ( SELECT record.value('(./Record/@id)[1]', 'int')               AS record_id     
          ,record.value('(./Record/SchedulerMonitorEvent/SystemHealth/SystemIdle)[1]','int')     AS systemidle     
          ,record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]','int') AS sqlsvcutilization     
          ,record_time    
         FROM ( SELECT DATEADD(ms, r.[timestamp] - sys.ms_ticks, GETDATE()) AS record_time  
       ,CONVERT(XML, record)           AS record     
         FROM sys.dm_os_ring_buffers   AS r WITH(NOLOCK)    
         cross join sys.dm_os_sys_info AS sys WITH(NOLOCK)    
     WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'     
          AND record LIKE '%<SystemHealth>%'    
          AND DATEADD(ms, r.[timestamp] - sys.ms_ticks, GETDATE()) >= GETDATE() - 1.0 / 24 / 6    
     ) x    
      ) y    
  WHERE sqlsvcutilization > 80 OR (100 - systemidle) > 85  
  ORDER BY record_id DESC  
  
  
  IF EXISTS(SELECT * FROM @cpu_check)  
  BEGIN  
   SET @tablehtml=    
       N'<h1>[웹DB] CPU 사용량</h1>'+    
       N'<table border="1">'+    
       N'<tr>'+    
       N'<th>레코드 Id</th>'+    
       N'<th>레코드 시간</th>'+    
       N'<th>System Idle(%)</th>'+    
       N'<th>SQL Server CPU 사용량(%)</th>'+    
       N'<th>OS CPU 사용량(%)</th>'+    
    N'<th>총 CPU 사용량(%)</th>'+    
       '</tr>'+    
       CAST((    
              SELECT td=record_id,'',        
         td=record_time,'',        
         td=system_idle,'',        
         td=sql_server,'',        
         td=os_process,'',        
         td=total_used,''    
      FROM @cpu_check     
                     for xml path('tr'),TYPE    
   )AS NVARCHAR(MAX)) + N'</table>';    
  
    EXEC msdb.dbo.sp_send_dbmail            
     @profile_name = 'test_profile',            
     @recipients = 'test@naver.com',        
     @body = @tablehtml,    
     @body_format = 'HTML',    
     @subject = 'CPU Usage is High'  
  END  
  