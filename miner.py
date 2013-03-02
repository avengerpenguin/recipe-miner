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
from scipy.spatial.distance import pdist
from scipy.cluster.hierarchy import linkage
from collections import defaultdict

class Food(object):
    def __init__(self, food_id, title):
        self.food_id = food_id
        self.title = title

    def __str__(self):
        return '<{}>'.format(self.title)

    def __unicode__(self):
        return str(self)

    def __eq__(self, other):
        return self.food_id == other.food_id

    def __hash__(self):
        return hash(self.food_id)

class Recipe(object):
    def __init__(self, recipe_id, title, ingredients):
        self.recipe_id = recipe_id
        self.title = title
        self.ingredients = ingredients

    def __str__(self):
        return '<Recipe: %s (%s)>' % (self.title, ", ".join([x.title for x in self.ingredients]))

    def __unicode__(self):
        return str(self)

    def __eq__(self, other):
        return self.recipe_id == other.recipe_id

class Cluster(object):
    def __init__(self, recipes=None):
        if not recipes:
            recipes = []
        self.recipes = recipes

    def __str__(self):
        return '<Cluster: [{}]>'.format("; ".join([x.title for x in self.recipes]))

    def __unicode__(self):
        return str(self)

    def __eq__(self, other):
        return str(self) == str(other)

def fetch(cursor, query, args=None):
    if args:
        cursor.execute(query, args)
    else:
        cursor.execute(query)
    for row in cursor.fetchall():
        yield row


def get_recipes(cursor):
    query = 'SELECT id, title FROM recipes ORDER BY RAND() LIMIT 200'
    for recipe_id, title in fetch(cursor, query):
        query = """SELECT foods.id, foods.title
FROM stages
JOIN ingredients ON ingredients.stageId = stages.id
JOIN ingredientsToFoods on ingredientsToFoods.ingredientId = ingredients.id
JOIN foods ON foods.id = ingredientsToFoods.foodId
WHERE recipeId=%s"""

        ingredients = [Food(food_id, food_title) for food_id, food_title in fetch(cursor, query, (recipe_id))]
        if recipe_id and title and ingredients:
            yield Recipe(recipe_id, title, ingredients)


def arff_recipes(recipes):
    arff = "@relation recipes\n\n@attribute recipe_id string\n"

    food_ids = list(set(
            [food.food_id for food in itertools.chain(
                    *[recipe.ingredients for recipe in recipes])]))
    food_ids.sort()

    for food_id in food_ids:
        arff += "@attribute %s {False,True}\n" % food_id

    arff += "\n@data\n"

    for recipe in recipes:
        arff += recipe.recipe_id + ","
        arff += ",".join([str(food_id in [ingredient.food_id for ingredient in recipe.ingredients])
                          for food_id in food_ids])
        arff += "\n"

    return arff


def distance(recipe1, recipe2):
    a = set(recipe1.ingredients)
    b = set(recipe2.ingredients)

    union = len(a.union(b))
    intersection = len(a.intersection(b))

    return float(union - intersection) / float(union)
    

def retrieve(distances, cluster1, cluster2):
    for t in distances:
        if t[1] == cluster1 and t[2] == cluster2:
            return t

def cluster(recipes, distances):

    clusters = [Cluster([recipe]) for recipe in recipes]
    distances = [(distance, Cluster([recipe1]), Cluster([recipe2])) for distance, recipe1, recipe2 in distances]

    m = 0

    while len(clusters) > 50:
        #print m, "\n", "\n".join([str(x) for x in clusters])
        print "Number of recipe groups: %s" % len(clusters)

        distances.sort()
        distance, r, s = distances[0]
        #print "Nearest: ", r, s
        print """Found similarity between "%s" and "%s" """ % (r, s)
        rs = Cluster(r.recipes + s.recipes)
 
        clusters.remove(r)
        clusters.remove(s)


        for k in clusters:
            d1 = retrieve(distances, k, r)[0]
            d2 = retrieve(distances, k, s)[0]
            d = min(d1, d2)
            distances.append((d, k, rs))
            distances.append((d, rs, k))

        clusters.append(rs)

        new_distances = []
        for t in distances:
            _, c1, c2 = t
            if r in (c1, c2) or s in (c1, c2):
                pass
                #print "Remove: ", c1, c2
                #distances.remove(t)
            else:
                new_distances.append(t)
                #print "Not remove:", c1, c2

        distances = new_distances
        #remove1 = retrieve(distances, r, s)
        #print "Remove 1", remove1[0], str(remove1[1]), str(remove1[2])
        #if remove1:
        #    distances.remove(remove1)
        #remove2 = retrieve(distances, s, r)
        #print "Remove 2", remove2[0], str(remove2[1]), str(remove2[2])
        #if remove2:
        #    distances.remove(remove2)


        m += 1

    print "Final groups:", "\n".join([str(x) for x in clusters])

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
    #print arff_recipes(recipes)

    distances = []
    for recipe1, recipe2 in itertools.product(recipes, recipes):
        #print recipe1.recipe_id, recipe2.recipe_id
        #print distance(recipe1, recipe2)
    #    cursor.execute("INSERT INTO distances (recipe1, recipe2, distance) VALUES (%s, %s, %s)",
    #                   (recipe1.recipe_id, recipe2.recipe_id, distance(recipe1, recipe2)))
        if recipe1.recipe_id != recipe2.recipe_id:
            distances.append((distance(recipe1, recipe2), recipe1, recipe2))

    cluster(recipes, distances)

    connection.commit()
    cursor.close()
    connection.close()
    
    
    

