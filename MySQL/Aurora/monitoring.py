#!/usr/bin/python
# -*- coding: utf-8 -*-
import boto3
import json
import time
import pymysql
import math
import os
from influxdb import InfluxDBClient
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import threading
from pprint import pprint
from decimal import *
import datetime
import re
import warnings
warnings.filterwarnings('ignore')



#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def FUNC_AURORA_LIST_INFO( _env ):
    _describe_db_instances = clientRds.describe_db_instances()
    _describe_db_clusters  = clientRds.describe_db_clusters()
    _Parsing_Data          = {}
    for _DBInstance in _describe_db_instances['DBInstances']:
        for key in _DBInstance.keys():
            if key == 'EnhancedMonitoringResourceArn':
                for _DBCluster in _describe_db_clusters['DBClusters']:
                    _Endpoint       = _DBCluster['Endpoint']
                    _ReaderEndpoint = _DBCluster['ReaderEndpoint']
                    for _DBClusterMember in _DBCluster['DBClusterMembers']:
                        if "load" in _DBClusterMember['DBInstanceIdentifier'] and _DBClusterMember['DBInstanceIdentifier'] == _DBInstance['DBInstanceIdentifier']:
                            if _DBClusterMember['IsClusterWriter'] == 1:
                                _Parsing_Data.update( {_DBClusterMember['DBInstanceIdentifier']: _Endpoint} )
                            if _DBClusterMember['IsClusterWriter'] == 0:
                                _Parsing_Data.update({ _DBClusterMember['DBInstanceIdentifier']: _ReaderEndpoint} )
                            DB_INSTANCE_RESOURCE_ID.update({_DBInstance['DBInstanceIdentifier']: _DBInstance['DbiResourceId']})
                        elif "prd" in _DBClusterMember['DBInstanceIdentifier'] and _DBClusterMember['DBInstanceIdentifier'] == _DBInstance['DBInstanceIdentifier']:
                            if _DBClusterMember['IsClusterWriter'] == 1:
                                _Parsing_Data.update( {_DBClusterMember['DBInstanceIdentifier']: _Endpoint} )
                            if _DBClusterMember['IsClusterWriter'] == 0:
                                _Parsing_Data.update({ _DBClusterMember['DBInstanceIdentifier']: _ReaderEndpoint} )
                            DB_INSTANCE_RESOURCE_ID.update({_DBInstance['DBInstanceIdentifier']: _DBInstance['DbiResourceId']})
    return _Parsing_Data

def execute_AWS_List(second=120.0):
    FUNC_AURORA_LIST_INFO(GATHERING_ENV)
    threading.Timer(second, execute_AWS_List).start()


#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def FUNC_AURORA_INSTANCE_INFO( _DATE_TIME ):
    _Parsing_Data          = {}
    _Parsing_Data_MetaAdd  = {}
    _Parsing_Data_AddList  = []
    _describe_db_instances = clientRds.describe_db_instances()
    _describe_db_clusters  = clientRds.describe_db_clusters()
    _TABLE_NAME            = "aurora_instance_info"

    for _DBCluster in _describe_db_clusters['DBClusters']:
        for _DBInstance in _describe_db_instances['DBInstances']:
           if _DBCluster['Status'] == 'available' and _DBCluster['DBClusterIdentifier'] == _DBInstance['DBClusterIdentifier'] :
               _DBInstanceIdentifier = _DBInstance['DBInstanceIdentifier']
               #regex                 = re.compile(r'.*-' + GATHERING_ENV + '-(.*)')
               regex                 = re.compile(r'.*-.*-(.*)')
               match                 = regex.search(_DBInstanceIdentifier)

               if match == None :
                   break
               else :
                   _host     = match.group(1)
                   _host_env = GATHERING_ENV

               DB_INSTANCE_TYPE.update({_DBInstance['DBInstanceIdentifier']: _DBInstance['DBInstanceClass']})

               for ClusterWriter in _DBCluster['DBClusterMembers']:
                   if isinstance(ClusterWriter,dict) and ClusterWriter['DBInstanceIdentifier'] == _DBInstanceIdentifier :
                       _IsClusterWriter=ClusterWriter.get('IsClusterWriter')

               _DBInstance_Address = _DBInstance['Endpoint']['Address'] 
               _DBInstance_Port    = _DBInstance['Endpoint']['Port'] 
               DB_INSTANCE_ENDPOINT.update({ _DBInstance['DBInstanceIdentifier'] : { "Endpoint": _DBInstance_Address, "Port":_DBInstance_Port, "Cluster_Write":_IsClusterWriter}  })
               _Parsing_Data_MetaAdd = {
                   "measurement": _TABLE_NAME,
                   "tags": { "host": _host, "host2": _DBInstanceIdentifier },
                   "fields": {
                       "EngineVersion":              _DBCluster['EngineVersion'],
                       "DBInstanceClass":            _DBInstance['DBInstanceClass'],
                       "PreferredMaintenanceWindow": _DBCluster['PreferredMaintenanceWindow'],
                       "PreferredBackupWindow":      _DBCluster['PreferredBackupWindow'],
                       "BackupRetentionPeriod":      _DBCluster['BackupRetentionPeriod'],
                       "IsClusterWriter":            _IsClusterWriter,
                       "DBInstance_Endpoint":        _DBInstance_Address,
                       "DBInstance_Port":            _DBInstance_Port
                   },
                   "time": _DATE_TIME,
               }
               _Parsing_Data_AddList.append(_Parsing_Data_MetaAdd)

    _Update_Count = 0
    for server_name in DB_INSTANCE_ENDPOINT.keys():
        for i in range(len(SERVERLISTS)):
            if SERVERLISTS[i] == server_name:
                _Update_Count = 1
        if _Update_Count == 0:
            SERVERLISTS.append(server_name)
        else:
            _Update_Count = 0
    clientInflux.write_points(_Parsing_Data_AddList, database='PERF', time_precision='ms', protocol='json')

def execute_AWS_INSTANCE(second=60.0):
    FUNC_AURORA_INSTANCE_INFO(int(time.time() * 1000))
    threading.Timer(second, execute_AWS_List).start()





#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def FUNC_DB_GET_RDS_STATUS(_TimeStamp, _InstanceID, _EndPoint, _Port):
    _Parsing_Data          = {}
    _Parsing_Data_MetaAdd  = {}
    _Parsing_Data_AddList  = []
    auroradb               = pymysql.connect( _EndPoint, DB_ID, DB_PW, "mysql", port=_Port )
    _IsWriter              = 'Writer' if DB_INSTANCE_ENDPOINT[_InstanceID]['Cluster_Write'] is True else 'Reader'
    _AuroraClient          = auroradb.cursor()
    _TABLE_NAME            = "aurora_mysql_status"
    _Query = '''
        show global status where variable_name in (
            'Innodb_buffer_pool_pages_misc', 'open_files', 'open_tables', 'opened_tables', 'Innodb_buffer_pool_pages_total','Innodb_buffer_pool_pages_free', 
            'Innodb_buffer_pool_pages_flushed', 'Innodb_buffer_pool_read_requests', 'Innodb_buffer_pool_write_requests', 'Innodb_buffer_pool_reads', 
            'Innodb_row_lock_current_waits', 'Innodb_page_size', 'Innodb_buffer_pool_pages_dirty', 'Innodb_buffer_pool_pages_data', 'Innodb_pages_created', 
            'Innodb_pages_read', 'Innodb_pages_written', 'Uptime_since_flush_status', 'Questions', 'com_delete', 'Queries', 'Max_used_connections', 
            'Aborted_clients', 'Aborted_connects', 'Connections', 'Threads_connected', 'Threads_cached', 'Threads_created', 'Threads_running', 
            'Innodb_row_lock_current_waits', 'Innodb_row_lock_time', 'Innodb_row_lock_time_avg', 'Innodb_row_lock_time_max', 'Innodb_row_lock_waits', 
            'Created_tmp_disk_tables', 'Created_tmp_files','Created_tmp_tables', 'Table_locks_immediate','Table_locks_waited','Sort_merge_passes',
            'Sort_range','Sort_rows','Sort_scan','Select_full_join','Select_full_range_join', 'Select_range','Select_range_check','Select_scan',
            'Handler_read_first','Slow_queries','Bytes_sent','Bytes_received','com_insert','com_update', 'com_commit','com_begin','com_admin_commands',
            'com_show_status','com_show_variables','com_set_option','com_select','qcache_free_memory', 'qcache_total_blocks','qcache_hits','qcache_inserts',
            'qcache_not_cached','qcache_lowmem_prunes','qcache_queries_in_cache','open_files', 'open_tables','opened_tables','Innodb_buffer_pool_bytes_data',
            'Innodb_buffer_pool_bytes_dirty','Innodb_buffer_pool_wait_free','Innodb_buffer_pool_reads', 'Innodb_buffer_pool_read_requests','Handler_read_first',
            'Handler_read_last','Handler_read_rnd_next','Handler_read_rnd','Handler_read_next','Handler_write', 'Handler_update','Handler_delete','Handler_commit',
            'Handler_rollback','Handler_read_key','Handler_read_prev','Qcache_inserts','qcache_not_cached', 'qcache_lowmem_prunes','Qcache_queries_in_cache')'''
    _AuroraClient.execute(_Query)
    for whatever in _AuroraClient.fetchall():
        _Parsing_Data[whatever[0]] = float(whatever[1])
    _Parsing_Data_MetaAdd      = { "measurement": _TABLE_NAME, "tags": { "host": _InstanceID, "regin": "ap-northeast-1", "IsClusterWriter": _IsWriter }, "fields": _Parsing_Data, "time": _TimeStamp, }
    _Parsing_Data_AddList.append(_Parsing_Data_MetaAdd)
    clientInflux.write_points(_Parsing_Data_AddList, database='PERF', time_precision='ms', protocol='json')

def execute_RDS_Status(second=60.0):
    GLOBAL_POOL.map(do_process_RDS_Status, SERVERLISTS)
    threading.Timer(second, execute_RDS_Status).start()

def do_process_RDS_Status(SERVER):
    _EndPoint         = DB_INSTANCE_ENDPOINT[SERVER]['Endpoint']
    _Port             = DB_INSTANCE_ENDPOINT[SERVER]['Port']
    _CURRENT_GET_TIME = int(time.time() * 1000)
    try:
        FUNC_DB_GET_RDS_STATUS( _CURRENT_GET_TIME, SERVER, _EndPoint, _Port)
    except Exception as e:
        print(e)



#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def FUNC_DB_GET_AWS_ENHANCED( _StreamName, _CURRENT_GET_TIME):
    _Parsing_Data          = {}
    _Parsing_Data_MetaAdd  = {}
    _Parsing_Data_AddList  = []
    _TABLE_NAME            = "aurora_mysql_enhanced"
    _TimeStamp_NOW         = time.time()
    _StartTime             = int(_TimeStamp_NOW) - 20
    result = clientLog.get_log_events(**{ 'logGroupName': 'RDSOSMetrics', 'logStreamName': _StreamName, 'startTime': _StartTime, 'limit': 1 }).get('events')[0].get('message').decode('utf-8')
    data = json.loads(result)
    _InstanceID = data["instanceID"]
    _Parsing_Data = {
        'task_total': data["tasks"]["total"],                           'task_zombie': data["tasks"]["zombie"],
        'task_blocked': data["tasks"]["blocked"],                       'task_running': data["tasks"]["running"],
        'task_stopped': data["tasks"]["stopped"],                       'task_sleeping': data["tasks"]["sleeping"],
        'diskIO_readIOsPS': data["diskIO"][0]["readIOsPS"],             'diskIO_writeIOsPS': data["diskIO"][0]["writeIOsPS"],
        'diskIO_readLatency': data["diskIO"][0]["readLatency"],         'diskIO_writeLatency': data["diskIO"][0]["writeLatency"],
        'diskIO_diskQueueDepth': data["diskIO"][0]["diskQueueDepth"],   'diskIO_readThroughput': data["diskIO"][0]["readThroughput"],
        'diskIO_writeThroughput': data["diskIO"][0]["writeThroughput"], 'Aurora_diskIO_tps': data["diskIO"][1]["tps"],
        'Aurora_diskIO_util': data["diskIO"][1]["util"],                'Aurora_diskIO_await': data["diskIO"][1]["await"],
        'Aurora_diskIO_device': data["diskIO"][1]["device"],            'Aurora_diskIO_readKb': data["diskIO"][1]["readKb"],
        'Aurora_diskIO_rrqmPS': data["diskIO"][1]["rrqmPS"],            'Aurora_diskIO_wrqmPS': data["diskIO"][1]["wrqmPS"],
        'Aurora_diskIO_writeKb': data["diskIO"][1]["writeKb"],          'Aurora_diskIO_avgReqSz': data["diskIO"][1]["avgReqSz"],
        'Aurora_diskIO_readKbPS': data["diskIO"][1]["readKbPS"],        'Aurora_diskIO_readIOsPS': data["diskIO"][1]["readIOsPS"],
        'Aurora_diskIO_writeKbPS': data["diskIO"][1]["writeKbPS"],      'Aurora_diskIO_writeIOsPS': data["diskIO"][1]["writeIOsPS"],
        'Aurora_diskIO_avgQueueLen': data["diskIO"][1]["avgQueueLen"],  'memory_free': data["memory"]["free"],
        'memory_slab': data["memory"]["slab"],                          'memory_dirty': data["memory"]["dirty"],
        'memory_total': data["memory"]["total"],                        'memory_active': data["memory"]["active"],
        'memory_cached': data["memory"]["cached"],                      'memory_mapped': data["memory"]["mapped"],
        'memory_buffers': data["memory"]["buffers"],                    'memory_inactive': data["memory"]["inactive"],
        'memory_writeback': data["memory"]["writeback"],                'memory_pageTables': data["memory"]["pageTables"],
        'memory_hugePagesFree': data["memory"]["hugePagesFree"],        'memory_hugePagesRsvd': data["memory"]["hugePagesRsvd"],
        'memory_hugePagesSize': data["memory"]["hugePagesSize"],        'memory_hugePagesSurp': data["memory"]["hugePagesSurp"],
        'memory_hugePagesTotal': data["memory"]["hugePagesTotal"],      'cpuUtilization_irq': data["cpuUtilization"]["irq"],
        'cpuUtilization_idle': data["cpuUtilization"]["idle"],          'cpuUtilization_nice': data["cpuUtilization"]["nice"],
        'cpuUtilization_user': data["cpuUtilization"]["user"],          'cpuUtilization_wait': data["cpuUtilization"]["wait"],
        'cpuUtilization_guest': data["cpuUtilization"]["guest"],        'cpuUtilization_steal': data["cpuUtilization"]["steal"],
        'cpuUtilization_total': data["cpuUtilization"]["total"],        'cpuUtilization_system': data["cpuUtilization"]["system"],
        'swap_in': data["swap"]["in"],                                  'swap_out': data["swap"]["out"],
        'swap_free': data["swap"]["free"],                              'swap_total': data["swap"]["total"],
        'swap_cached': data["swap"]["cached"],                          'network_rx': data["network"][0]["rx"],
        'network_tx': data["network"][0]["tx"],                         'network_interface': data["network"][0]["interface"],
        'fileSys_name': data["fileSys"][0]["name"],                     'fileSys_used': data["fileSys"][0]["used"],
        'fileSys_total': data["fileSys"][0]["total"],                   'fileSys_maxFiles': data["fileSys"][0]["maxFiles"],
        'fileSys_usedFiles': data["fileSys"][0]["usedFiles"],           'fileSys_mountPoint': data["fileSys"][0]["mountPoint"],
        'fileSys_usedPercent': data["fileSys"][0]["usedPercent"],       'fileSys_usedFilePercent': data["fileSys"][0]["usedFilePercent"],
        'loadAverageOne': data["loadAverageMinute"]["one"],             'loadAveragefive': data["loadAverageMinute"]["five"],
        'loadAveragefifteen': data["loadAverageMinute"]["fifteen"],     'engine': data["engine"],
        'uptime': data["uptime"],                                       'numVCPUs': data["numVCPUs"],
        'version': data["version"]
    }
    _Parsing_Data_MetaAdd = { "measurement": _TABLE_NAME, "tags": { "instanceid": _InstanceID, "regin": "ap-northeast-1" }, "fields": _Parsing_Data, "time": _CURRENT_GET_TIME, }
    _Parsing_Data_AddList = []
    _Parsing_Data_AddList.append(_Parsing_Data_MetaAdd)
    clientInflux.write_points(_Parsing_Data_AddList, database='PERF', time_precision='ms', protocol='json')

def execute_AWS_Enhanced(second=30.0):
    GLOBAL_POOL.map(do_process_AWS_Enhanced, SERVERLISTS)
    threading.Timer(second, execute_AWS_Enhanced).start()

def do_process_AWS_Enhanced(SERVER):
    _StreamName       = DB_INSTANCE_RESOURCE_ID[SERVER]
    _CURRENT_GET_TIME = int(time.time() * 1000)  # milli
    try:
        FUNC_DB_GET_AWS_ENHANCED( _StreamName, _CURRENT_GET_TIME )
    except Exception as e:
        print(e)



#----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def FUNC_DB_GET_RDS_QUERY( _InstanceID, _DB_EndPoint, _Port ):
    _Parsing_Data          = {}
    _Parsing_Data_MetaAdd  = {}
    _Parsing_Data_AddList  = []
    _IsWriter              = 'Writer' if DB_INSTANCE_ENDPOINT[_InstanceID]['Cluster_Write'] is True else 'Reader'

    auroradb               = pymysql.connect( _DB_EndPoint, DB_ID, DB_PW, "mysql", port=_Port)
    _AuroraClient          = auroradb.cursor()
    for _Querys in AURORA_QUERY:
        _CURRENT_GET_TIME      = int(time.time() * 1000)
        _Measurement           = _Querys['measurement']
        _Query                 = _Querys['query']
        _AuroraClient.execute(_Query)
        _Result                = _AuroraClient.fetchall()
        _Columns               = _AuroraClient.description

        if len(_Result) != 0:
            for whatever in _Result:
                data={}
                for (index,value) in enumerate(whatever):
                    _Column_Name = str(_Columns[index][0])

                    if isinstance(value, datetime.datetime):
                        data[_Column_Name] = str(value)
                    elif isinstance(value, datetime.timedelta):
                        data[_Column_Name] = str(value)
                    elif isinstance(value, str):
                        data[_Column_Name] = value
                    elif isinstance(value, int):
                        data[_Column_Name] = value
                    elif isinstance(value, type(None)):
                        data[_Column_Name] = None
                    elif isinstance(value, type(Decimal(1))):
                        data[_Column_Name] = float(value)

                data['IsWriter'] = _IsWriter
                _Parsing_Data_MetaAdd = { "measurement": _Measurement, "tags":{ "host": _InstanceID, "region": "ap-northeast-1" }, "fields": data, }
                _Parsing_Data_AddList.append(_Parsing_Data_MetaAdd)
        
                if _Parsing_Data_AddList:
                    try:
                        #if _Measurement == "aurora_mysql_innodb_metrics":
                        #    pprint(_Parsing_Data_AddList)
                        #else:
                        clientInflux.write_points( _Parsing_Data_AddList, database='PERF', time_precision='ms', protocol='json')
                    except Exception as e:
                        print(e)
                _Parsing_Data_AddList=[]

    auroradb.close()


def execute_RDS_Query(second=60.0):
    GLOBAL_POOL.map(do_process_RDS_Query, SERVERLISTS)
    threading.Timer(second, execute_RDS_Query).start()

def do_process_RDS_Query(SERVER):
    _EndPoint         = DB_INSTANCE_ENDPOINT[SERVER]['Endpoint']
    _Port             = DB_INSTANCE_ENDPOINT[SERVER]['Port']
    FUNC_DB_GET_RDS_QUERY( SERVER, _EndPoint, _Port )






if __name__ == "__main__":
#--------------------------------------- connection
    clientLog                        = boto3.client('logs', 'ap-northeast-1')
    clientRds                        = boto3.client('rds',  'ap-northeast-1')  
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rds.html
    clientInflux                     = InfluxDBClient(host='10.255.10.197', port=8086)

    DB_INSTANCE_RESOURCE_ID          = {}
    DB_INSTANCE_ENDPOINT             = {}
    GATHERING_ENV                    = 'prd'
    DB_INSTANCE_TYPE                 = {}
    SERVERLISTS                      = []
    DB_ID                            = 'monitor'
    DB_PW                            = 'TlTmfhrm*!15zkrxl'
    CPU_CORE                         = multiprocessing.cpu_count() / 2
    GLOBAL_POOL                      = ThreadPoolExecutor(max_workers=math.floor(CPU_CORE))
    CURRENT_END_TIME                 = int(time.time() * 1000)  # milliseconds
    os.system('sudo updatedb')

    AURORA_QUERY = [
    { 
        "measurement": "aurora_mysql_query_digest",
        "query":"""SELECT NOW() AS GET_TIME,
            ifnull(SCHEMA_NAME, 'NONE') AS SCHEMA_NAME,
            DIGEST_TEXT AS QUERY,
            IF(SUM_NO_GOOD_INDEX_USED > 0 OR SUM_NO_INDEX_USED > 0, '*', '') AS FULL_SCAN,
            COUNT_STAR AS EXEC_COUNT, 
            SUM_ERRORS AS ERR_COUNT_TOTAL,
            SUM_WARNINGS AS WARN_COUNT_TOTAL,
            SEC_TO_TIME(SUM_TIMER_WAIT/1000000000000) AS EXEC_TIME_TOTAL,
            SEC_TO_TIME(MAX_TIMER_WAIT/1000000000000) AS EXEC_TIME_MAX,
            SEC_TO_TIME(AVG_TIMER_WAIT/1000000000000) AS EXEC_TIME_AVG_MS,
            SUM_ROWS_AFFECTED AS ROWS_AFFECTED_TOTAL,
            SUM_ROWS_SENT AS ROWS_SENT_TOTAL,
            ROUND(SUM_ROWS_SENT / COUNT_STAR) AS ROWS_SENT_AVG,
            SUM_ROWS_EXAMINED AS ROWS_EXAMINED_TOTAL,
            SUM_CREATED_TMP_DISK_TABLES AS CREATED_TMP_DISK_TABLES_TOTAL,
            SUM_CREATED_TMP_TABLES AS CREATED_TMP_TABLES_TOTAL,
            SUM_SORT_MERGE_PASSES AS SORT_MERGE_PASSES_TOTAL,
            SUM_SORT_ROWS AS SORT_ROWS_TOTAL,
            SEC_TO_TIME(SUM_TIMER_WAIT/1000000000000) AS TIMER_WAIT_TOTAL,
            DIGEST
        FROM performance_schema.events_statements_summary_by_digest 
        WHERE SCHEMA_NAME not in ('performance_schema','information_schema','mysql') AND
              last_seen > DATE_SUB(NOW(), INTERVAL 60 SECOND) AND
              DIGEST not in ( '3fbede30fc54358140a607cb66b667f6', '5d58d43500e3850d9cd35d6dc302fb58',
                              '20381e49cdd9c4f151494275cec46e08', '8c692e5b6e1769681d4065a63bf755ae',
                              'e31e405cc080a7d3192978de1e1ee3a8', '484e5667b83173ea26515f6aeba53c83',
                              '5e2b475312099e505fd05617c4f87bb9', '638f731fea5c925671608d60bb0066bb',
                              '0ed3a30b0fd2cdf82cca420a1867ba0d');"""
    },{
        "measurement": "aurora_mysql_query_full_table_scan",
        "query":"""SELECT NOW() AS GET_TIME, 
            object_schema AS OBJECT_SCHEMA, 
            object_name AS OBJECT_NAME, 
            rows_full_scanned AS ROWS_FULL_SCANNED, 
            SEC_TO_TIME(latency/1000000000000) AS LATENCY
         FROM {} 
         WHERE object_schema not in ('information_schema','mysql','nxdba','performance_schema','sys') 
         ORDER BY rows_full_scanned DESC,latency DESC; """.format('sys.x$schema_tables_with_full_table_scans')
    },{
        "measurement": "aurora_mysql_innodb_metrics",
        "query": """SELECT NOW() AS GET_TIME,
             `NAME` AS `NAME`, 
             SUBSYSTEM AS `SUBSYSTEM`,
             `COUNT` AS `COUNT` 
        FROM INFORMATION_SCHEMA.INNODB_METRICS WHERE STATUS = 'enabled';"""
    },{
        "measurement": "aurora_mysql_query_processlist",
        "query": """SELECT NOW() AS GET_TIME, 
            ps_th.PROCESSLIST_USER AS PROCESSLIST_USER, 
            ps_th.PROCESSLIST_HOST AS PROCESSLIST_HOST, 
            ps_th.PROCESSLIST_DB AS PROCESSLIST_DB, 
            ps_th.PROCESSLIST_COMMAND AS PROCESSLIST_COMMAND, 
            ps_th.PROCESSLIST_TIME AS THREAD_TIME, 
            ps_th.PROCESSLIST_INFO AS PROCESSLIST_INFO, 
            SEC_TO_TIME(ps_esc.TIMER_WAIT/1000000000000) AS TIMER_WAIT , 
            IF(ps_esc.LOCK_TIME>0,SEC_TO_TIME(ps_esc.LOCK_TIME/1000000000000),'00:00:00.000') AS LOCK_TIME, 
            ps_esc.SQL_TEXT AS SQL_TEXT, 
            ps_esc.DIGEST AS DIGEST, 
            ps_esc.MYSQL_ERRNO AS MYSQL_ERRNO, 
            ps_esc.WARNINGS AS WARNINGS, 
            ps_esc.ROWS_AFFECTED AS ROWS_AFFECTED, 
            ps_esc.ROWS_SENT AS ROWS_SENT, 
            ps_esc.ROWS_EXAMINED AS ROWS_EXAMINED, 
            ps_esc.CREATED_TMP_DISK_TABLES AS CREATED_TMP_DISK_TABLES, 
            ps_esc.CREATED_TMP_TABLES AS CREATED_TMP_TABLES, 
            ps_esc.SELECT_FULL_JOIN AS SELECT_FULL_JOIN, 
            ps_esc.SELECT_FULL_RANGE_JOIN AS SELECT_FULL_RANGE_JOIN, 
            ps_esc.SELECT_RANGE AS SELECT_RANGE, 
            ps_esc.SELECT_RANGE_CHECK AS SELECT_RANGE_CHECK, 
            ps_esc.SELECT_SCAN AS SELECT_SCAN, 
            ps_esc.SORT_MERGE_PASSES AS SORT_MERGE_PASSES, 
            ps_esc.SORT_RANGE AS SORT_RANGE, 
            ps_esc.SORT_ROWS AS SORT_ROWS, 
            ps_esc.SORT_SCAN AS SORT_SCAN, 
            ps_esc.NO_INDEX_USED AS NO_INDEX_USED, 
            ps_esc.NO_GOOD_INDEX_USED AS NO_GOOD_INDEX_USED, 
            ps_esc.NESTING_EVENT_ID AS NESTING_EVENT_ID, 
            ps_esc.NESTING_EVENT_TYPE AS NESTING_EVENT_TYPE, 
            ps_esc.NESTING_EVENT_LEVEL AS NESTING_EVENT_LEVEL 
        FROM performance_schema.events_statements_current ps_esc, performance_schema.threads ps_th 
        WHERE ps_esc.THREAD_ID = ps_th.THREAD_ID AND 
              ps_th.PROCESSLIST_USER not in ('rdsadmin') AND 
              ps_esc.TIMER_WAIT > 0 AND 
              ps_esc.CURRENT_SCHEMA not in ('performance_schema','information_schema','mysql') AND
              ps_esc.DIGEST not in ('00000000000000000000000000000000');"""
        },{
        "measurement": "aurora_mysql_table_autoincrement",
        "query": """SELECT NOW() AS GET_TIME, 
            table_schema AS OBJECT_SCHEMA, 
            table_name AS OBJECT_NAME, 
            column_name AS COLUMN_NAME, 
            auto_increment AS AUTO_INCREMENT,
            CAST(pow(2, case data_type
                when 'tinyint'   then 7
                when 'smallint'  then 15
                when 'mediumint' then 23
                when 'int'       then 31
                when 'bigint'    then 63
            end+(column_type like '% unsigned'))-1 as decimal(19)) as max_int
        FROM information_schema.tables t JOIN information_schema.columns c USING (table_schema,table_name)
        WHERE c.extra = 'auto_increment' AND 
              table_schema not in ('mysql') AND
              t.auto_increment IS NOT NULL;"""
        },{
        "measurement": "aurora_mysql_table_io_wait",
        "query": """SELECT NOW() AS GET_TIME, 
            OBJECT_SCHEMA, 
            OBJECT_NAME, 
            COUNT_FETCH AS COUNT_FETCH_TOTAL, 
            COUNT_INSERT AS COUNT_INSERT_TOTAL, 
            COUNT_UPDATE AS COUNT_UPDATE_TOTAL, 
            COUNT_DELETE AS COUNT_DELETE_TOTAL,
            SEC_TO_TIME(SUM_TIMER_FETCH/1000000000000)  AS TIMER_FETCH_TOTAL, 
            SEC_TO_TIME(SUM_TIMER_INSERT/1000000000000) AS TIMER_INSERT_TOTAL, 
            SEC_TO_TIME(SUM_TIMER_UPDATE/1000000000000) AS TIMER_UPDATE_TOTAL, 
            SEC_TO_TIME(SUM_TIMER_DELETE/1000000000000) AS TIMER_DELETE_TOTAL
        FROM performance_schema.table_io_waits_summary_by_table
        WHERE OBJECT_SCHEMA NOT IN ('mysql', 'performance_schema', 'sys');"""
        },{
        "measurement": "aurora_mysql_query_events",
        "query": """SELECT NOW() AS GET_TIME, 
            EVENT_NAME,
            COUNT_READ_TOTAL, 
            SEC_TO_TIME(SUM_TIMER_READ/1000000000000) AS TIMER_READ_TOTAL
            SUM_NUMBER_OF_BYTES_READ AS NUMBER_OF_BYTES_TOTAL,
            COUNT_WRITE_TOTAL, 
            SEC_TO_TIME(SUM_TIMER_WRITE/1000000000000) AS TIMER_WRITE_TOTAL, 
            SUM_NUMBER_OF_BYTES_WRITE AS NUMBER_OF_BYTES_WRITE_TOTAL
        FROM performance_schema.file_summary_by_event_name"""
        },{
        "measurement": "aurora_mysql_schema_info",
        "query": """SELECT NOW() AS get_time, 
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE,
            ifnull(ENGINE, 'NONE') as ENGINE,
            ifnull(VERSION, '0') as VERSION,
            ifnull(ROW_FORMAT, 'NONE') as ROW_FORMAT,
            ifnull(TABLE_ROWS, '0') as TABLE_ROWS_TOTAL,
            ifnull(DATA_LENGTH, '0') as DATA_LENGTH_TOTAL,
            ifnull(INDEX_LENGTH, '0') as INDEX_LENGTH_TOTAL,
            ifnull(DATA_FREE, '0') as DATA_FREE_TOTAL,
            ifnull(CREATE_OPTIONS, 'NONE') as CREATE_OPTIONS
        FROM information_schema.tables
        WHERE TABLE_SCHEMA not in ('information_schema','mysql','performance_schema','sys');"""
        }
    ]

#--------------------------------------- Initial AWS INFO
    result = FUNC_AURORA_LIST_INFO(GATHERING_ENV)
    #pprint(DB_INSTANCE_RESOURCE_ID)
    FUNC_AURORA_INSTANCE_INFO(CURRENT_END_TIME)
    #print(DB_INSTANCE_ENDPOINT)
  
    GLOBAL_POOL.submit(execute_AWS_List)
    GLOBAL_POOL.submit(execute_AWS_INSTANCE)
    GLOBAL_POOL.submit(execute_RDS_Status())
    GLOBAL_POOL.submit(execute_AWS_Enhanced())
    GLOBAL_POOL.submit(execute_RDS_Query())
    GLOBAL_POOL.daemon = True
