import psycopg2, psycopg2.extras
import sys
import getpass

def sql_connect(OUSER=None,OPASS=None):
    global con
    USER=getpass.getuser()
    try:
      with open('/home/'+USER+'/.omni/sql.conf') as fp:
        DBPORT="5432"
        for line in fp:
          #print line
          if line.split('=')[0] == "sqluser":
            if OUSER==None:
              DBUSER=line.split('=')[1].strip()
            else:
              DBUSER=OUSER
          elif line.split('=')[0] == "sqlpassword":
            if OPASS==None:
              DBPASS=line.split('=')[1].strip()
            else:
              DBPASS=OPASS
          elif line.split('=')[0] == "sqlconnect":
            DBHOST=line.split('=')[1].strip()
          elif line.split('=')[0] == "sqlport":
            DBPORT=line.split('=')[1].strip()
          elif line.split('=')[0] == "sqldatabase":
            DBNAME=line.split('=')[1].strip()
    except IOError as e:
      response='{"error": "Unable to load sql config file. Please Notify Site Administrator"}'
      return response
    try:
        con = psycopg2.connect(database=DBNAME, user=DBUSER, password=DBPASS, host=DBHOST, port=DBPORT)
        cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return cur
    except psycopg2.DatabaseError, e:
        print 'Error %s' % e
        sys.exit(1)

def dbInit(ouser=None,opass=None ):
    #Prime the DB Connection, it can be restarted in the select/execute statement if it gets closed prematurely. 
    global dbc
    try:
      if dbc.closed:
        dbc=sql_connect(ouser,opass)
    except NameError:
      dbc=sql_connect(ouser,opass)

def dbSelect(statement, values=None):
    dbInit()
    try:
        dbc.execute(statement, values)
        ROWS = dbc.fetchall()
        return ROWS
    except psycopg2.DatabaseError, e:
        print 'Error', e, 'Rollback returned: ', dbRollback()
        sys.exit(1)

def dbExecute(statement, values=None):
    dbInit()
    try:
        dbc.execute(statement, values)
    except psycopg2.DatabaseError, e:
        print 'Error', e, 'Rollback returned: ', dbRollback()
        sys.exit(1)

def dbUpgradeExecute(ouser, opass, statement, values=None):
    dbInit(ouser,opass)
    try:
      con.set_session(autocommit=True)
      dbc.execute(statement, values)
      con.set_session(autocommit=False)
    except psycopg2.DatabaseError, e:
        print 'Error', e, 'Rollback returned: ', dbRollback()

def dbCommit():
    try:
        con.commit()
    except psycopg2.DatabaseError, e:
        print 'Error', e, 'Rollback returned: ', dbRollback()
        sys.exit(1)

def dbRollback():
    if con:
       con.rollback()
       return 1
    else:
       return 0

def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError
