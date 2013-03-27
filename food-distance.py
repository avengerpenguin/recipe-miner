#!/usr/bin/python
"""Food distancer

Usage:
  food-distance.py <host> <user> <password> <database>

Options:
  -h --help     Show this screen.

"""

from docopt import docopt
import MySQLdb
import itertools

class Food(object):
    def __init__(self, food_id, title, recipes):
        self.food_id = food_id
        self.title = title
        self.recipes = recipes

    def __str__(self):
        return '<Food: %s {%s}>' % (self.title, ", ".join([x.title for x in self.recipes]))

    def __unicode__(self):
        return str(self)

    def __eq__(self, other):
        return self.food_id == other.food_id

    def __hash__(self):
        return hash(self.food_id)

class Recipe(object):
    def __init__(self, recipe_id, title, cuisine):
        self.recipe_id = recipe_id
        self.title = title
        self.cuisine = cuisine

    def __str__(self):
        return '<{}>'.format(self.title)

    def __unicode__(self):
        return str(self)

    def __eq__(self, other):
        return self.recipe_id == other.recipe_id

    def __hash__(self):
        return hash(self.recipe_id)

def fetch(cursor, query, args=None):
    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)
    for row in cursor.fetchall():
        yield row

def distance(food1, food2):
    a = set(food1.recipes)
    b = set(food2.recipes)

    union = len(a.union(b))
    intersection = len(a.intersection(b))

    return float(union - intersection) / float(union)

if __name__ == '__main__':
    arguments = docopt(__doc__)

    connection = MySQLdb.connect(host=arguments['<host>'],
                                 user=arguments['<user>'],
                                 passwd=arguments['<password>'],
                                 db=arguments['<database>'])

    cursor = connection.cursor() 

    query = """SELECT foods.id, foods.title
FROM foods
JOIN ingredientsToFoods ON ingredientsToFoods.foodId = foods.id
JOIN ingredients ON ingredientsToFoods.ingredientId = ingredients.id
JOIN stages ON ingredients.stageId = stages.id
JOIN recipes ON recipes.id = stages.recipeId AND recipes.cuisineId IS NOT NULL"""

    foods = []

    for food_id, food_title in fetch(cursor, query):
        recipe_query = """
SELECT recipes.id, recipes.title, recipes.cuisineId
FROM recipes
JOIN stages ON stages.recipeId = recipes.id
JOIN ingredients ON ingredients.stageId = stages.id
JOIN ingredientsToFoods ON ingredientsToFoods.ingredientId = ingredients.id
JOIN foods ON foods.id = ingredientsToFoods.foodId
WHERE foods.id =  %s
"""
        recipes = [Recipe(*fields) for fields in fetch(cursor, recipe_query, (food_id))]
        if food_id and food_title and recipes:
            foods.append(Food(food_id, food_title, recipes))

    for food1, food2 in itertools.product(foods, foods):
        food_distance = distance(food1, food2)
        #print food1.title, food2.title, food_distance
        cursor.execute("INSERT INTO foodsDistances (food1, food2, distance) VALUES (%s, %s, %s)",
                       (food1.food_id, food2.food_id, food_distance))
        connection.commit()

    cursor = connection.cursor() 

    cursor.close()
    connection.close()
