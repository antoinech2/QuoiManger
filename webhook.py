from flask import Flask
from flask_assistant import Assistant, ask, tell
from flask_assistant import context_manager
import sqlite3

app = Flask(__name__)
assist = Assistant(app, project_id = "cuisine-bae54", route='/')

database_loc = "datas.bd"
database_connection = sqlite3.connect(database_loc)
database_cursor = database_connection.cursor()
database_cursor.execute("CREATE TABLE IF NOT EXISTS Plats (id integer NOT NULL PRIMARY KEY AUTOINCREMENT, name VARCHAR(200) NOT NULL UNIQUE, ingredients TEXT NOT NULL, last_eat DATE NOT NULL DEFAULT CURRENT_TIMESTAMP, number_eat integer NOT NULL DEFAULT 0)")
database_cursor.execute("CREATE TABLE IF NOT EXISTS ingredients (id integer NOT NULL PRIMARY KEY AUTOINCREMENT, name VARCHAR(200) NOT NULL UNIQUE, stock BOOLEAN NOT NULL DEFAULT TRUE)")
database_connection.commit()
database_cursor.close()
database_connection.close()

def sql_request(request, values = None):
	try:
		database_connection = sqlite3.connect(database_loc)
		database_cursor = database_connection.cursor()
		if values:
			database_cursor.execute(request, values)
		else:
			database_cursor.execute(request)
		database_connection.commit()
		database_cursor.close()
		database_connection.close()
	except sqlite3.Error as error:
		database_cursor.close()
		database_connection.close()
		print("SQLite 3 Error:", error)
		return error

def get_from_sql(request, values = None):
	try:
		database_connection = sqlite3.connect(database_loc)
		database_cursor = database_connection.cursor()
		if values:
			result_request = database_cursor.execute(request, values)
		else:
			result_request = database_cursor.execute(request)
		result = []
		for row in result_request:
			result.append(row)
		database_connection.commit()
		database_cursor.close()
		database_connection.close()
		return result, None
	except sqlite3.Error as error:
		database_cursor.close()
		database_connection.close()
		print("SQLite 3 Error:", error)
		return None, error

def SqlErrorMessage(error):
	return "Malhereusement, une erreur est survenue lors de la communication avec la base de données. SQLite 3 a renvoyé l'erreur suivante :" + str(error)

def GetSingular(text):
	texts = text.split()
	for cur in range(len(texts)):
		texts[cur] = texts[cur].rstrip("s")
	return " ".join(texts)

@assist.action('add_meal')
def add_meal(plat):
	result, error = get_from_sql("SELECT name from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			return ask("Ce plat existe déjà dans votre liste. Essayez autre chose.")
		else:
			#list_ingre = ingredients.split(" et ")
			#final_ingre = "|".join(list_ingre)
			error = sql_request("INSERT INTO Plats (name, ingredients) VALUES (?, '')", (plat,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				context_manager.add("current_plat")
				context_manager.set("current_plat", "name", plat)
				return ask("D'accord, quel est le premier ingrédient de " + plat + " ?")

@assist.action('modif_ingredient')
def modif_ingredient(plat):
	result, error = get_from_sql("SELECT name from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			error = sql_request("UPDATE Plats SET ingredients = '' WHERE name = ?", (plat, ))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				context_manager.add("current_plat")
				context_manager.set("current_plat", "name", plat)
				return ask("D'accord, quel est le premier ingrédient de " + plat + " ?")
		else:
			return ask("Le plat " + plat + " n'est pas enregistré. Essayez autre chose.")


@assist.action('add_ingredient') #mapping={'meal': 'sys.any'}
def add_ingredient(ingredient):
	plat = context_manager.get_param("current_plat", "name")
	result, error = get_from_sql("SELECT ingredients from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		brut_ingredients = result[0][0]
		ingredients = brut_ingredients.split("|")
		if ingredient in ingredients:
			return ask("Cet ingrédient est déjà ajouté. Essayez autre chose.")
		else:
			if brut_ingredients == "":
				new_ingredients = ingredient
			else:
				new_ingredients = brut_ingredients + "|" + ingredient
			error = sql_request("UPDATE Plats SET ingredients = ? WHERE name = ?", (new_ingredients, plat))
			error = sql_request("INSERT OR IGNORE INTO ingredients (name) VALUES (?)", (ingredient,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				return ask("OK, un autre ingrédient ?")

@assist.action('get_eat')
def get_eat(number):
	if number == "":
		number = 3
	result, error = get_from_sql("SELECT name, ingredients, strftime('%s','now') - strftime('%s',last_eat) from Plats ORDER BY last_eat ASC")
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			propotitions = []
			for plat_data in result:
				ingredients = plat_data[1].split("|")
				result_ingre, error = get_from_sql("SELECT stock from ingredients WHERE stock = FALSE AND name IN ({})".format(','.join(['?']*len(ingredients))), (ingredients))
				if error:
					return ask(SqlErrorMessage(error))
				else:
					exist = False
					for data in result_ingre:
						exist = True
					if exist == False:
						propotitions.append((plat_data[0],plat_data[2]))
						if len(propotitions) >= number:
							break
			final_text = ""
			for final_plat in propotitions:
				final_text += "Le plat " + final_plat[0] + " que vous n'avez pas mangé depuis " + str(round(final_plat[1]/86400)) + " jours. "
			return ask("Voici quelques propositions de plats: " + final_text + "N'oubliez pas de me dire ce que vous allez manger. Bon appétit !")
		else:
			return ask("Vous n'avez aucun plat enregistré.")

@assist.action('ingredient_set_stock')
def ingredient_set_stock(ingredient):
	result, error = get_from_sql("SELECT name from ingredients WHERE name = ?", (ingredient,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			error = sql_request("UPDATE ingredients SET stock = TRUE WHERE name = ?", (ingredient,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				return ask("OK, c'est noté, vous avez " + ingredient + " en stock")
		else:
			return ask("L'ingrédient " + ingredient + " n'est pas enregistré car il n'est nécessaire dans aucun des plats enregistrés.")

@assist.action('ingredient_set_no_stock')
def ingredient_set_no_stock(ingredient):
	result, error = get_from_sql("SELECT name from ingredients WHERE name = ?", (ingredient,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			error = sql_request("UPDATE ingredients SET stock = FALSE WHERE name = ?", (ingredient,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				return ask("OK, c'est noté, vous n'avez plus " + ingredient + " en stock")
		else:
			return ask("L'ingrédient " + ingredient + " n'est pas enregistré car il n'est nécessaire dans aucun des plats enregistrés.")

@assist.action('ingredients_set_all_stock')
def ingredients_set_all_stock():
	error = sql_request("UPDATE ingredients SET stock = TRUE")
	if error:
		return ask(SqlErrorMessage(error))
	else:
		return ask("Super! J'ai noté que vous avez tous vos ingrédients en stock.")

@assist.action('ingredients_get_no_stock')
def ingredients_get_no_stock():
	result, error = get_from_sql("SELECT name from ingredients WHERE stock = FALSE")
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			liste_ingre = []
			for data in result:
				liste_ingre.append(data[0])
			output = ", ".join(liste_ingre)
			return ask("Voici les ingrédients que vous n'avez plus en stock: " + output)
		else:
			return ask("Vous avez tous vos ingrédients en stock.")

@assist.action('get_ingredients')
def get_ingredients(plat):
	result, error = get_from_sql("SELECT ingredients from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			liste_ingre = result[0][0].split("|")
			liste_ingre = ", ".join(liste_ingre)
			return ask("Voici la liste des ingrédients du plat "+ plat + " : " + liste_ingre)
		else:
			return ask("Le plat " + plat + " n'est pas enregistré. Essayez autre chose.")

@assist.action('get_ingredient_stock')
def get_ingredient_stock(ingredient):
	result, error = get_from_sql("SELECT stock from ingredients WHERE name = ?", (ingredient,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			if result[0][0]:
				return ask("Oui, vous avez "+ ingredient + " en stock.")
			else:
				return ask("Non, vous n'avez plus "+ ingredient + " en stock.")
		else:
			return ask("L'ingrédient " + ingredient + " n'est pas enregistré car il n'est nécessaire dans aucun des plats enregistrés.")

@assist.action('get_meal')
def get_meal():
	result, error = get_from_sql("SELECT name from Plats")
	if error:
		return ask(SqlErrorMessage(error))
	else:
		plats = []
		for column in result:
			plats.append(column[0])
		ouput = ", ".join(plats)
		return ask("Voici la liste des plats: "+ ouput)

@assist.action('get_all_ingredients')
def get_all_ingredients():
	result, error = get_from_sql("SELECT name from ingredients")
	if error:
		return ask(SqlErrorMessage(error))
	else:
		plats = []
		for column in result:
			plats.append(column[0])
		ouput = ", ".join(plats)
		return ask("Voici la liste de tous les ingrédients: "+ ouput)

@assist.action('remove_meal')
def remove_meal(plat):
	result, error = get_from_sql("SELECT name from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			error = sql_request("DELETE FROM Plats WHERE name = ?", (plat,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				return ask("Très bien, j'ai supprimé le plat " + plat + ". Autre chose ?")
		else:
			return ask("Le plat " + plat + " n'est pas enregistré. Essayez autre chose.")

@assist.action('just_eaten')
def just_eaten(plat):
	result, error = get_from_sql("SELECT name, ingredients from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			error = sql_request("UPDATE Plats SET last_eat = datetime('now', 'localtime'), number_eat = number_eat + 1 WHERE name = ?", (plat,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				return tell("Très bien, c'est noté. N'oubliez pas de me dire s'il vous manque les ingrédients " + ", ".join(result[0][1].split("|")))
		else:
			return ask("Le plat " + plat + " n'est pas enregistré. Essayez autre chose.")

@assist.action('get_meal_eaten')
def get_meal_eaten(date):
	result, error = get_from_sql("SELECT name from Plats WHERE date(last_eat) = date(?)", (date,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		plats = []
		for data in result:
			plats.append(data[0])
		if len(plats) > 0:
			return ask("Vous avez mangé " + ", ".join(plats))
		else:
			return ask("Aucun plat trouvé pour cette date.")

@assist.action('when_eaten')
def when_eaten(plat):
	result, error = get_from_sql("SELECT name from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			result, error = get_from_sql("SELECT strftime('%s','now') - strftime('%s',last_eat) from Plats WHERE name = ?", (plat,))
			if error:
				return ask(SqlErrorMessage(error))
			else:
				days = result[0][0]/86400
				if days < 0.7:
					return ask("Vous avez mangé " + plat + " pour la dernière fois aujourd'hui. Autre chose ?")
				else:
					return ask("Vous avez mangé " + plat + " pour la dernière fois il y a " + str(round(days)) + " jours. Autre chose ?")
		else:
			return ask("Le plat " + plat + " n'est pas enregistré. Essayez autre chose.")

@assist.action('count_eaten')
def count_eaten(plat):
	result, error = get_from_sql("SELECT name, number_eat from Plats WHERE name = ?", (plat,))
	if error:
		return ask(SqlErrorMessage(error))
	else:
		exist = False
		for data in result:
			exist = True
		if exist:
			return ask("Vous avez mangé " + plat + " " + str(result[0][1]) + " fois au total. Autre chose ?")
		else:
			return ask("Le plat " + plat + " n'est pas enregistré. Essayez autre chose.")

if __name__ == '__main__':
	app.run(debug=True)
