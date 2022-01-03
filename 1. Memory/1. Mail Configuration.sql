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

-- �ʼ� ������ �Է�
SELECT @account_name_param = '' -- ex) test_account
      ,@description_param1 = '' -- ex) test_account
	  ,@email_address_param = '' -- ex) test@naver.com (�������� �ʴ� ���� �ּҵ� ��� ����)
	  ,@mailserver_name_param = '' -- ex) smtp server��
	  ,@username_param = '' -- ex) ����� ������ ���� ID
	  ,@password_param = '' -- ex) ����� ������ ���� PW
	  ,@profile_name_param = '' -- ex) test_account
	  ,@description_param2 = '' -- ex) test_account
	  ,@recipients_param = '' -- ex) test@naver.com (�޴»�� �̸��� �ּ�)
	  ,@port_param = 0 -- ex) 25, 7925

-- 1. �����ͺ��̽� ���� Ȯ�� ���� ���ν��� Ȱ��ȭ
-- To enable Database Mail
IF EXISTS ( SELECT 1 FROM sys.configurations WHERE NAME = 'Database Mail XPs' AND VALUE = 0)
BEGIN
    PRINT 'Enabling Database Mail XPs'
    EXEC sp_configure 'show advanced options', 1;
    RECONFIGURE
    EXEC sp_configure 'Database Mail XPs', 1;
    RECONFIGURE
END

--2. �����ͺ��̽� ���� ���� ����
-- Create a Database Mail account  
EXECUTE msdb.dbo.sysmail_add_account_sp
    @account_name = @account_name_param,
    @description = @description_param1,
    @email_address = @email_address_param,
    @mailserver_name = @mailserver_name_param,
    @port = @port_param,
    @username = @username_param, -- ���� ������ ���� ID
    @password = @password_param; -- ���� ������ ���� PW

--3. �����ͺ��̽� ���� ������ ����
-- Create a Database Mail profile
EXEC msdb.dbo.sysmail_add_profile_sp
  @profile_name = @profile_name_param,
  @description = @description_param2

--4. �����ʿ� ���� �߰�
--Add the account to the profile
EXEC msdb.dbo.sysmail_add_profileaccount_sp
  @profile_name = @profile_name_param,
  @account_name = @account_name_param,
  @sequence_number = 1

--5-1. �����ͺ��̽� ���� ����� ���� ���� (Public)
-- Grant access to the profile to the DBMailUsers role (Public)
EXEC msdb.dbo.sysmail_add_principalprofile_sp
  @profile_name = @profile_name_param,
  @principal_name = 'public',
  @is_default = 1

--5-2. �����ͺ��̽� ���� Ȯ�� ���� ���ν��� Ȱ��ȭ (Private)
-- Grant access to the profile to the DBMailUsers role (Private)
EXEC msdb.dbo.sysmail_add_principalprofile_sp
  @profile_name = @profile_name_param,
  @principal_name = '##MS_PolicyEventProcessingLogin##',
  @is_default = 0

--6. �׽�Ʈ ���� �߼�
EXEC msdb.dbo.sp_send_dbmail
  @profile_name = @profile_name_param -- ������ �����ʸ�
 ,@recipients = @recipients_param -- �޴»�� �����ּ�
 ,@body = 'test is test' -- ���ϳ���
 ,@subject = 'test'; -- ��������
