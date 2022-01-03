IF EXISTS(SELECT * FROM sysobjects WHERE name = 'SP_CHECK_DISK_USAGE' AND xtype = 'P')
DROP PROC SP_CHECK_DISK_USAGE
GO
CREATE   PROCEDURE dbo.SP_CHECK_DISK_USAGE  
AS        
SET NOCOUNT ON        
BEGIN        
 DECLARE @Driveslist TABLE        
 (        
   Idx    INT IDENTITY(1,1) NOT NULL PRIMARY KEY,        
   Drive    CHAR(1) NOT NULL,        
   FreeSpaceMB INT NULL,        
   TotalSizeMB INT NULL        
 )        
        
 DECLARE @config TABLE        
 (        
   name   NVARCHAR(35),        
   min    INT,        
   max    INT,        
   config INT,        
   run    INT        
 )        
        
 DECLARE @ObjectToken INT,        
         @drive    CHAR(1),        
         @odrive   INT,        
         @TotalSize   VARCHAR(20),        
         @MB    BIGINT,        
         @DriveCnt    INT,        
         @Idx    INT,        
         @ori_sao     INT,        
         @ori_oap     INT,    
         @tablehtml   VARCHAR(MAX)    
        
 SET @MB = 1048576        
 SET @DriveCnt = 0        
 SET @Idx = 1        
        
 INSERT @Driveslist(Drive, FreeSpaceMB)         
 EXEC MASTER.dbo.xp_fixeddrives        
        
 SET @DriveCnt = @@ROWCOUNT        
        
 INSERT INTO @config EXEC sp_configure        
        
 IF(SELECT config FROM @config WHERE NAME = N'show advanced options') = 0        
 BEGIN        
  SET @ori_sao = 0        
        
  EXEC sp_configure 'show advanced options', 1        
  RECONFIGURE WITH OVERRIDE        
        
  DELETE FROM @config        
  INSERT INTO @config EXEC sp_configure        
 END        
 ELSE        
 BEGIN        
  SET @ori_sao = 1        
 END        
        
 IF(SELECT config FROM @config WHERE NAME = N'Ole Automation Procedures') = 0        
 BEGIN        
     SET @ori_oap = 0        
        
  EXEC sp_configure 'Ole Automation Procedures', 1        
  RECONFIGURE WITH OVERRIDE        
 END        
 ELSE        
 BEGIN        
     SET @ori_oap = 1        
 END        
        
 EXEC sp_OACreate 'Scripting.FileSystemObject', @ObjectToken OUT  --Creates an instance of the OLE object on an instance of SQL Server.        
        
 WHILE @Idx <= @DriveCnt        
 BEGIN        
  SELECT @drive = drive FROM @Driveslist WHERE Idx = @Idx        
        
  EXEC sp_OAMethod @ObjectToken, 'GetDrive', @odrive OUT, @drive          
                 
  -- Gets a property TotalSize        
  EXEC sp_OAGetProperty @odrive,'TotalSize', @TotalSize OUT        
          
  UPDATE @Driveslist        
  SET TotalSizeMB = @TotalSize / @MB        
   WHERE Idx = @Idx        
        
     SET @Idx = @Idx + 1        
 END        
        
 EXEC sp_OADestroy @ObjectToken        
        
 IF @ori_oap = 0        
 BEGIN        
  EXEC sp_configure 'Ole Automation Procedures', 0        
  RECONFIGURE WITH OVERRIDE        
 END        
        
 IF @ori_sao = 0        
 BEGIN        
     EXEC sp_configure 'show advanced options', 0        
     RECONFIGURE WITH OVERRIDE        
 END        
        
  IF EXISTS(SELECT * FROM @Driveslist WHERE CAST(FreeSpaceMB/1024.0 AS DECIMAL(10,2)) < CAST(TotalSizeMB/1024.0 AS DECIMAL(10,2)) * 0.25)    
  BEGIN    
   SET @tablehtml=    
       N'<h1>[웹DB] 디스크 사용량</h1>'+    
       N'<table border="1">'+    
       N'<tr>'+    
       N'<th>드라이브</th>'+    
       N'<th>여유디스크공간(MB)</th>'+    
       N'<th>총디스크공간(MB)</th>'+    
       N'<th>여유디스크공간(GB)</th>'+    
       N'<th>총디스크공간(GB)</th>'+    
	   N'<th>여유공간(%)</th>'+    
       '</tr>'+    
       CAST((    
              SELECT td=drive,'',        
      td=FreeSpaceMB,'',        
      td=TotalSizeMB,'',        
      td=CAST(FreeSpaceMB/1024.0 AS DECIMAL(10,2)),'',        
      td=CAST(TotalSizeMB/1024.0 AS DECIMAL(10,2)),'',        
      td=CAST((FreeSpaceMB/(TotalSizeMB * 1.0)) * 100.0 AS DECIMAL(5,2)),''    
       FROM @Driveslist     
      WHERE CAST(FreeSpaceMB/1024.0 AS DECIMAL(10,2)) < CAST(TotalSizeMB/1024.0 AS DECIMAL(10,2)) * 0.25    
      ORDER BY drive    
                     for xml path('tr'),TYPE    
       )AS NVARCHAR(MAX))+    
       N'</table>';    
    
     EXEC msdb.dbo.sp_send_dbmail            
       @profile_name = 'test_profile',            
       @recipients = 'test@naver.com',        
       @body = @tablehtml,    
       @body_format = 'HTML',    
       @subject = 'Disk Usage is High'     
  END    
END