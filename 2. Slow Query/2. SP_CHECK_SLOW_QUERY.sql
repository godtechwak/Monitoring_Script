IF EXISTS(SELECT * FROM sysobjects WHERE name = 'SP_CHECK_SLOW_QUERY' AND xtype = 'P')
DROP PROC [dbo].[SP_CHECK_SLOW_QUERY]
GO
-- [SP_CHECK_SLOW_QUERY]              
CREATE OR ALTER PROC [dbo].[SP_CHECK_SLOW_QUERY]              
@duration DATETIME    
AS              
SET NOCOUNT ON              
DECLARE @A XML            
       ,@tablehtml VARCHAR(MAX)    
    
DECLARE @Slow_Query TABLE     
(    
 ServerName VARCHAR(100)    
   ,[timestamp] DATETIME2    
   ,Duration BIGINT    
   ,Row_Count INT    
   ,DatabaseName VARCHAR(100)    
   ,Sql_Text VARCHAR(MAX)    
   ,username VARCHAR(100)
)    
    
SELECT @A = CAST(target_data AS XML)                 
  FROM sys.dm_xe_sessions   AS a              
      JOIN sys.dm_xe_session_targets AS b ON CAST(a.address AS BINARY(8)) = CAST(b.event_session_address AS BINARY(8))              
WHERE a.name   = 'XE_QUERY'              
  AND target_name ='ring_buffer'              
    
    
    INSERT INTO @Slow_Query    
 SELECT @@SERVERNAME as servername,            
   --c.value('(@name)[1]', 'varchar(100)')           as Eventname              
   dateadd(hh,9, c.value('(@timestamp)[1]', 'datetime2'))       as [Timestamp]              
    --, c.value('(./data[@name="cpu_time" ]/value)[1]','BIGINT')               as cpu_time                                               
    , c.value('(./data[@name="duration" ]/value)[1]','BIGINT')               as [duration]              
    --, c.value('(./data[@name="physical_reads" ]/value)[1]','BIGINT')         as [physical_reads]              
    --, c.value('(./data[@name="logical_reads" ]/value)[1]' ,'BIGINT')         as [logical_reads]              
    --, c.value('(./data[@name="writes" ]/value)[1]','BIGINT')                 as [writes]              
    , c.value('(./data[@name="row_count" ]/value)[1]','INT')              as [row_count]              
    --, c.value('(action[@name="client_app_name"]/value)[1]','VARCHAR(100)')   as client_app_name              
    --, c.value('(action[@name="client_hostname"]/value)[1]','VARCHAR(100)')   as client_hostname              
    , c.value('(action[@name="database_name"]/value)[1]','VARCHAR(50)')     as [database_name]            
    --, c.value('(action[@name="num_response_rows"]/value)[1]','VARCHAR(100)') as num_response_rows              
    --, c.value('(action[@name="plan_handle"]/value)[1]','VARCHAR(100)')    as plan_handle              
    --, c.value('(action[@name="query_hash"]/value)[1]','VARCHAR(100)')     as query_hash              
    --, c.value('(action[@name="query_plan_hash"]/value)[1]','VARCHAR(100)')   as query_plan_hash              
    --, c.value('(action[@name="session_id"]/value)[1]','VARCHAR(100)')     as session_id              
    , c.value('(action[@name="sql_text"]/value)[1]','VARCHAR(max)')     as sql_text              
    , c.value('(action[@name="username"]/value)[1]','VARCHAR(100)')     as username              
    --, CAST(c.query('.') AS NVARCHAR(MAX)) AS [EventData]              
     FROM @A.nodes('/RingBufferTarget/event') B (c)               
    WHERE dateadd(hh,9, c.value('(@timestamp)[1]', 'datetime2')) > @duration              
    
    
   IF EXISTS(SELECT * FROM @Slow_Query)      
   BEGIN      
     SET @tablehtml=        
      N'<h1>[게임웹DB] 슬로우 쿼리</h1>'+        
      N'<table border="1">'+        
      N'<tr>'+        
      N'<th>서버명</th>'+        
      N'<th>시간</th>'+        
      N'<th>지연시간</th>'+        
      N'<th>총 ROW 수</th>'+        
      N'<th>데이터베이스명</th>'+        
	  N'<th>사용자명</th>'+        
      N'<th>쿼리문</th>'+        
      '</tr>'+        
      CAST((        
       SELECT td=servername,'',            
     td=timestamp,'',            
     td=duration,'',            
     td=row_count,'',            
     td=DatabaseName,'',
	 td=username,'',
     td=sql_text,''        
     FROM @Slow_Query         
        for xml path('tr'),TYPE        
     )AS NVARCHAR(MAX)) + N'</table>';        
      
   EXEC msdb.dbo.sp_send_dbmail                
		@profile_name = 'test_profile',                
        @recipients = 'test@naver.com',            
        @body = @tablehtml,        
        @body_format = 'HTML',        
        @subject = 'Slow Query Detected'      
  END      
  RETURN    
    
    