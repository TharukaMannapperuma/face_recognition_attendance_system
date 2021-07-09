import mysql.connector
mysqldb = mysql.connector.connect(
    host="localhost", user="root", password="")
try:
    mycursor = mysqldb.cursor()
    db_name = "python"
    mycursor.execute("create database {}".format(db_name))
    print("Success!")
except Exception as e:
    print("Error", e)
mysqldb.close()
