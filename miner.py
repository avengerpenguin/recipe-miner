#!/usr/bin/python
"""Recipe Miner

Usage:
  miner.py <host> <user> <password> <database>

Options:
  -h --help     Show this screen.

"""
from docopt import docopt
import MySQLdb

def fetch(cursor, query):
    cursor.execute(query)
    for row in cursor.fetchall():
        yield row

if __name__ == '__main__':
   arguments = docopt(__doc__)

   connection = MySQLdb.connect(host=arguments['<host>'],
                        user=arguments['<user>'],
                        passwd=arguments['<password>'],
                        db=arguments['<database>'])

   cursor = connection.cursor() 

   

   connection.close()
