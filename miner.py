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


class Food:
    def __init__(self, food_id, title):
        self.food_id = food_id
        self.title = title

    def __str__(self):
        return '<{}>'.format(self.title)

    def __unicode__(self):
        return str(self)

class Recipe:
    def __init__(self, recipe_id, title, ingredients):
        self.recipe_id = recipe_id
        self.title = title
        self.ingredients = ingredients

    def __str__(self):
        return '<Recipe: %s (%s)>' % (self.title, ", ".join([x.title for x in self.ingredients]))

    def __unicode__(self):
        return str(self)


def fetch(cursor, query):
    cursor.execute(query)
    for row in cursor.fetchall():
        yield row


def get_recipes(cursor):
    query = 'SELECT id, title FROM recipes ORDER BY RAND()'
    for recipe_id, title in itertools.islice(fetch(cursor, query), 10):
        query = """SELECT foods.id, foods.title
FROM stages
JOIN ingredients ON ingredients.stageId = stages.id
JOIN ingredientsToFoods on ingredientsToFoods.ingredientId = ingredients.id
JOIN foods ON foods.id = ingredientsToFoods.foodId
WHERE recipeId='{}'""".format(recipe_id)

        ingredients = [Food(food_id, food_title) for food_id, food_title in fetch(cursor, query)]
        yield Recipe(recipe_id, title, ingredients)


def arff_recipes(recipes):
    arff = "@relation recipes\n\n@attribute recipe_id string\n"

    food_ids = list(set(
            [food.food_id for food in itertools.chain(
                    *[recipe.ingredients for recipe in recipes])]))
    food_ids.sort()

    for food_id in food_ids:
        arff += "@attribute {} numeric\n".format(food_id)

    arff += "\n@data\n"

    for recipe in recipes:
        arff += recipe.recipe_id + ","
        arff += ",".join([str(int(food_id in [ingredient.food_id for ingredient in recipe.ingredients]))
                          for food_id in food_ids])
        arff += "\n"

    return arff


if __name__ == '__main__':
   arguments = docopt(__doc__)

   connection = MySQLdb.connect(host=arguments['<host>'],
                        user=arguments['<user>'],
                        passwd=arguments['<password>'],
                        db=arguments['<database>'])

   cursor = connection.cursor() 

   recipes = list(get_recipes(cursor))
   #for recipe in recipes:
   #    print recipe
   print arff_recipes(recipes)

   connection.close()
