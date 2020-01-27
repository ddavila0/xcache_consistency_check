import sys
import sqlite3

sql_file = sys.argv[1]
sqliteConnection = sqlite3.connect(sql_file)
cursor = sqliteConnection.cursor()
print("Connected to SQLite")

sqlite_select_query = """SELECT * from files"""
cursor.execute(sqlite_select_query)
records = cursor.fetchall()
print("Total rows are:  ", len(records))
print("Printing each row")
print("id | filename\t\t | last_check_ts | last_modification_date | checksum |")
for row in records:
    print(row)
