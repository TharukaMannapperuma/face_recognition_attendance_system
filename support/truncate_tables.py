import mysql.connector

mysqldb = mysql.connector.connect(
    host="localhost", user="root", password="", database="python")
try:
    mycursor = mysqldb.cursor()

    table = []
    table.append(""" TRUNCATE TABLE `logs`; """)

    table.append("""TRUNCATE TABLE `users`;""")
    for query in table:
        mycursor.execute(query)
        print("Success!")
except Exception as e:
    print("Error", e)
mysqldb.close()
