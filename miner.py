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
from math import log
import random
import uuid
from collections import Counter

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
    def __init__(self, recipe_id, title, ingredients, cuisine):
        self.recipe_id = recipe_id
        self.title = title
        self.ingredients = ingredients
        self.cuisine = cuisine

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
    query = 'SELECT DISTINCT recipes.id, recipes.title, cuisines.id FROM recipes JOIN cuisines ON cuisines.id = recipes.cuisineId WHERE cuisineId IS NOT NULL'
    for recipe_id, title, cuisine in fetch(cursor, query):
        query = """SELECT DISTINCT foods.id, foods.title
FROM stages
JOIN ingredients ON ingredients.stageId = stages.id
JOIN ingredientsToFoods on ingredientsToFoods.ingredientId = ingredients.id
JOIN foods ON foods.id = ingredientsToFoods.foodId
WHERE recipeId=%s"""

        ingredients = [Food(food_id, food_title)
                       for food_id, food_title in fetch(cursor, query, (recipe_id))]
        if recipe_id and title and ingredients:
            yield Recipe(recipe_id, title, ingredients, cuisine)


def arff_recipes(recipes):
    arff = "@relation recipes\n\n@attribute recipe_id string\n"

    food_ids = list(set(
            [food.food_id for food in itertools.chain(
                    *[recipe.ingredients for recipe in recipes])]))
    food_ids.sort()

    cuisines = list(set(recipe.cuisine for recipe in recipes))
    cuisines.sort()

    arff += "@attribute cuisine {%s}\n" % (",".join(cuisines),)
    for food_id in food_ids:
        arff += "@attribute %s {False,True}\n" % food_id

    arff += "\n@data\n"

    for recipe in recipes:
        arff += "%s,%s," % (recipe.recipe_id, recipe.cuisine)
        arff += ",".join([str(food_id in [ingredient.food_id for ingredient in recipe.ingredients])
                          for food_id in food_ids])
        arff += "\n"

    return arff

def sparse_arff_recipes(recipes, foods = None):
    arff = "@relation recipes\n\n@attribute recipe_id string\n"

    if not foods:
        food_ids = list(set(
                [food.food_id for food in itertools.chain(
                        *[recipe.ingredients for recipe in recipes])]))
    else:
        food_ids = [food.food_id for food in foods]
    food_ids.sort()

    cuisines = list(set(recipe.cuisine for recipe in recipes))
    cuisines.sort()

    arff += "@attribute cuisine {%s}\n" % (",".join(cuisines),)
    for food_id in food_ids:
        arff += "@attribute %s {0,1}\n" % food_id

    arff += "\n@data\n"

    for recipe in recipes:
        arff += "{0 %s,1 %s," % (recipe.recipe_id, recipe.cuisine)
        food_indicies = [food_ids.index(food_id) + 2 for food_id in [ingredient.food_id for ingredient in recipe.ingredients] if food_id in food_ids]
        food_indicies.sort()
        arff += ",".join(["%s 1" % food_index for food_index in food_indicies])
        arff += "}\n"

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

def calc_entropy(recipes):
    num_recipes = len(recipes)
    label_counts = {}
    for recipe in recipes:
        current_cuisine = recipe.cuisine
        if current_cuisine not in label_counts:
            label_counts[current_cuisine] = 0
        label_counts[current_cuisine] += 1

    entropy = 0.0

    for label, count in label_counts.iteritems():
        prob = float(count) / num_recipes
        entropy -= prob * log(prob,2)
        #print label, prob

    return entropy

def build_tree(recipes, foods, node='root', depth=20):

    cuisines = [recipe.cuisine for recipe in recipes]

    if not cuisines:
        return

    #print cuisines
    if len(set(cuisines)) == 1:
        num_cuisines = len(cuisines)
        print '%s [label="%s (%s/0)" shape=rectangle color=green]' % (node, recipes[0].cuisine, num_cuisines)
        return

    if depth == 0:
        num_cuisines = len(cuisines)
        data = Counter(cuisines)

        rankings = data.most_common()
        majority = rankings[0][0]
        correct = rankings[0][1]
        wrong = num_cuisines - correct

        print '%s [label="%s (%s/%s)" shape=rectangle color=red]' % (node, majority, correct, wrong)
        return

    if len(foods) == 0:
        num_cuisines = len(cuisines)
        data = Counter(cuisines)

        rankings = data.most_common()
        majority = rankings[0][0]
        correct = rankings[0][1]
        wrong = num_cuisines - correct

        print '%s [label="%s (%s/%s)" shape=rectangle color=blue]' % (node, majority, correct, wrong)
        return


    foods = foods[:]

    entropy = calc_entropy(recipes)
    #print 'Initial entropy: ', entropy
    #foods = list(set(
    #        [food for food in itertools.chain(
    #                *[recipe.ingredients for recipe in recipes])]))

    num_recipes = len(recipes)

    splits = []
    for food in foods:
    
        left, right = [], []
        for recipe in recipes:
            if food in recipe.ingredients:
                right.append(recipe)
            else:
                left.append(recipe)

        info_left, info_right = calc_entropy(left), calc_entropy(right)

        split_entropy = (float(len(left)) / float(num_recipes) * info_left) + (float(len(right)) / float(num_recipes) * info_right)
        gain = entropy - split_entropy

        splits.append((gain, food))

        #print food, gain
        #cursor.execute("INSERT INTO split_gains (food, gain) VALUES (%s, %s)",
        #           (food.food_id, gain))
        #connection.commit()

    splits.sort()
    splits.reverse()
    [(gain, food.food_id) for gain, food in splits]
    _, best_food = splits[0]
    #print "Best:", best_food

    print '%s [label="%s?"]' % (node, best_food.title)

    left, right = [], []
    for recipe in recipes:
        if best_food in recipe.ingredients:
            right.append(recipe)
        else:
            left.append(recipe)

    subnode1 = 'node_%s_%s' % ((uuid.uuid4().int % 1000000), len(set([recipe.cuisine for recipe in left])))
    subnode2 = 'node_%s_%s' % ((uuid.uuid4().int % 1000000), len(set([recipe.cuisine for recipe in right])))
    print '%s -> %s [label=no]' % (node, subnode1)
    print '%s -> %s [label=yes]' % (node, subnode2)


    foods = [food for food in foods if food.food_id != best_food.food_id]
    #print [food.food_id for food in foods]

    #print best_food.food_id, len(left), len(right), [food.food_id for food in foods]

    build_tree(left, foods, subnode1, depth - 1)
    build_tree(right, foods, subnode2, depth - 1)
    
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
    #print sparse_arff_recipes(recipes)

    #distances = []
    #for recipe1, recipe2 in itertools.product(recipes, recipes):
        #print recipe1.recipe_id, recipe2.recipe_id
        #print distance(recipe1, recipe2)
        #cursor.execute("INSERT INTO distances (recipe1, recipe2, distance) VALUES (%s, %s, %s)",
                       #(recipe1.recipe_id, recipe2.recipe_id, distance(recipe1, recipe2)))
        #connection.commit()
    #    if recipe1.recipe_id != recipe2.recipe_id:
    #        distances.append((distance(recipe1, recipe2), recipe1, recipe2))

    #cluster(recipes, distances)

    food_list = [food for food in itertools.chain(
                    *[recipe.ingredients for recipe in recipes])]

    #food_list = [food for food in food_list if food_list.count(food) > 1]

    food_counts = Counter(food_list)
    food_list = [food for food, count in food_counts.most_common() if count > 4 and count < 1000]

    foods = list(set(food_list))

    print sparse_arff_recipes(recipes, foods)

    #print 'digraph tree {'
    #print 'rankdir=LR;'
    #build_tree(recipes, foods)
    #print '}'

    cursor.close()
    connection.close()

    
    

