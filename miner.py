#!/usr/bin/python
"""Recipe Miner

Usage:
  miner.py <host> <user> <password> <database>

Options:
  -h --help     Show this screen.

"""
from docopt import docopt
import MySQLdb
import itertools


class Recipe:
    def __init__(self, recipe_id, title):
        self.recipe_id = recipe_id
        self.title = title

    def __str__(self):
        return '<Recipe: {}>'.format(self.title)


def fetch(cursor, query):
    cursor.execute(query)
    for row in cursor.fetchall():
        yield row


def get_recipes(cursor):
    query = 'SELECT id, title FROM recipes ORDER BY RAND()'
    for recipe_id, title in itertools.islice(fetch(cursor, query), 10):
        yield Recipe(recipe_id, title)


if __name__ == '__main__':
   arguments = docopt(__doc__)

   connection = MySQLdb.connect(host=arguments['<host>'],
                        user=arguments['<user>'],
                        passwd=arguments['<password>'],
                        db=arguments['<database>'])

   cursor = connection.cursor() 

   for recipe in get_recipes(cursor):
       print recipe

   connection.close()
