DECLARE @account_name_param VARCHAR(100)
       ,@description_param1 VARCHAR(100)
	   ,@email_address_param VARCHAR(100)
	   ,@mailserver_name_param VARCHAR(100)
	   ,@username_param VARCHAR(100)
	   ,@password_param VARCHAR(100)
	   ,@profile_name_param VARCHAR(100)
	   ,@description_param2 VARCHAR(100)
	   ,@recipients_param VARCHAR(100)
	   ,@port_param INT

-- 필수 데이터 입력
SELECT @account_name_param = '' -- ex) test_account
      ,@description_param1 = '' -- ex) test_account
	  ,@email_address_param = '' -- ex) test@naver.com (존재하지 않는 메일 주소도 상관 없음)
	  ,@mailserver_name_param = '' -- ex) smtp server명
	  ,@username_param = '' -- ex) 사용자 도메인 계정 ID
	  ,@password_param = '' -- ex) 사용자 도메인 계정 PW
	  ,@profile_name_param = '' -- ex) test_account
	  ,@description_param2 = '' -- ex) test_account
	  ,@recipients_param = '' -- ex) test@naver.com (받는사람 이메일 주소)
	  ,@port_param = 0 -- ex) 25, 7925

-- 1. 데이터베이스 메일 확장 저장 프로시저 활성화
-- To enable Database Mail
IF EXISTS ( SELECT 1 FROM sys.configurations WHERE NAME = 'Database Mail XPs' AND VALUE = 0)
BEGIN
    PRINT 'Enabling Database Mail XPs'
    EXEC sp_configure 'show advanced options', 1;
    RECONFIGURE
    EXEC sp_configure 'Database Mail XPs', 1;
    RECONFIGURE
END

--2. 데이터베이스 메일 계정 생성
-- Create a Database Mail account  
EXECUTE msdb.dbo.sysmail_add_account_sp
    @account_name = @account_name_param,
    @description = @description_param1,
    @email_address = @email_address_param,
    @mailserver_name = @mailserver_name_param,
    @port = @port_param,
    @username = @username_param, -- 본인 도메인 계정 ID
    @password = @password_param; -- 본인 도메인 계정 PW

--3. 데이터베이스 메일 프로필 생성
-- Create a Database Mail profile
EXEC msdb.dbo.sysmail_add_profile_sp
  @profile_name = @profile_name_param,
  @description = @description_param2

--4. 프로필에 계정 추가
--Add the account to the profile
EXEC msdb.dbo.sysmail_add_profileaccount_sp
  @profile_name = @profile_name_param,
  @account_name = @account_name_param,
  @sequence_number = 1

--5-1. 데이터베이스 메일 사용자 권한 설정 (Public)
-- Grant access to the profile to the DBMailUsers role (Public)
EXEC msdb.dbo.sysmail_add_principalprofile_sp
  @profile_name = @profile_name_param,
  @principal_name = 'public',
  @is_default = 1

--5-2. 데이터베이스 메일 확장 저장 프로시저 활성화 (Private)
-- Grant access to the profile to the DBMailUsers role (Private)
EXEC msdb.dbo.sysmail_add_principalprofile_sp
  @profile_name = @profile_name_param,
  @principal_name = '##MS_PolicyEventProcessingLogin##',
  @is_default = 0

--6. 테스트 메일 발송
EXEC msdb.dbo.sp_send_dbmail
  @profile_name = @profile_name_param -- 생성한 프로필명
 ,@recipients = @recipients_param -- 받는사람 메일주소
 ,@body = 'test is test' -- 메일내용
 ,@subject = 'test'; -- 메일제목
