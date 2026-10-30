IF DB_ID('RecipeDB') IS NULL
    BEGIN
        CREATE DATABASE RecipeDB;
    END
GO

USE RecipeDB;
GO


IF OBJECT_ID('RecipeDB.dbo.Languages', 'U') IS NULL
    BEGIN
        CREATE TABLE Languages (
            language_code NVARCHAR(10) NOT NULL PRIMARY KEY,
            language_name NVARCHAR(50) NOT NULL
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Text_Keys', 'U') IS NULL
    BEGIN
        CREATE TABLE Text_Keys (
            text_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Localization', 'U') IS NULL
    BEGIN
        CREATE TABLE Localization (
            text_id INT NOT NULL,
            language_code NVARCHAR(10) NOT NULL,
            text_value NVARCHAR(MAX) NOT NULL,

            CONSTRAINT PK_Localization PRIMARY KEY (text_id, language_code),

            CONSTRAINT FK_Localization_Text_Keys
                FOREIGN KEY (text_id) REFERENCES Text_Keys(text_id),

            CONSTRAINT FK_Localization_Languages
                FOREIGN KEY (language_code) REFERENCES Languages(language_code)
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Recipes', 'U') IS NULL
    BEGIN
        CREATE TABLE Recipes (
            recipe_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            name_text_id INT NOT NULL UNIQUE,
            instructions_text_id INT NOT NULL UNIQUE,
            recipe_prep_time_in_minutes INT NOT NULL CHECK (recipe_prep_time_in_minutes > 0),

            CONSTRAINT FK_Recipes_Name
                FOREIGN KEY (name_text_id) REFERENCES Text_Keys(text_id),

            CONSTRAINT FK_Recipes_Instructions
                FOREIGN KEY (instructions_text_id) REFERENCES Text_Keys(text_id),

            CONSTRAINT CK_Recipes_Text_Ids CHECK (name_text_id <> instructions_text_id)
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Recipe_Category', 'U') IS NULL
    BEGIN
        CREATE TABLE Recipe_Category (
            category_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            name_text_id INT NOT NULL UNIQUE,

            CONSTRAINT FK_Recipe_Category_Name
                FOREIGN KEY (name_text_id) REFERENCES Text_Keys(text_id)
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Recipe_Categories', 'U') IS NULL
    BEGIN
        CREATE TABLE Recipe_Categories (
            recipe_id INT NOT NULL,
            category_id INT NOT NULL,

            CONSTRAINT PK_Recipe_Categories
                PRIMARY KEY (recipe_id, category_id),
            CONSTRAINT FK_Recipe_Categories_Recipe
                FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id),
            CONSTRAINT FK_Recipe_Categories_Category
                FOREIGN KEY (category_id) REFERENCES Recipe_Category(category_id)
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Ingredients', 'U') IS NULL
    BEGIN
        CREATE TABLE Ingredients (
            ingredient_id INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            name_text_id INT NOT NULL UNIQUE,
            ingredient_calorie FLOAT NOT NULL CHECK (ingredient_calorie >= 0),
            ingredient_protein FLOAT NOT NULL CHECK (ingredient_protein >= 0),
            ingredient_fat FLOAT NOT NULL CHECK (ingredient_fat >= 0),
            ingredient_carbohydrate FLOAT NOT NULL CHECK (ingredient_carbohydrate >= 0),
            ingredient_sugar FLOAT NOT NULL CHECK (ingredient_sugar >= 0),
            ingredient_fiber FLOAT NOT NULL CHECK (ingredient_fiber >= 0),
            ingredient_sodium FLOAT NOT NULL CHECK (ingredient_sodium >= 0),

            CONSTRAINT FK_Ingredients_Name
                FOREIGN KEY (name_text_id) REFERENCES Text_Keys(text_id)
        );
    END
GO

IF OBJECT_ID('RecipeDB.dbo.Recipe_Ingredients', 'U') IS NULL
    BEGIN
        CREATE TABLE Recipe_Ingredients (
            recipe_id INT NOT NULL,
            ingredient_id INT NOT NULL,
            ingredient_quantity FLOAT NOT NULL CHECK (ingredient_quantity > 0),

            CONSTRAINT PK_Recipe_Ingredients
                PRIMARY KEY (recipe_id, ingredient_id),

            CONSTRAINT FK_Recipe_Ingredients_Recipe
                FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id),
            CONSTRAINT FK_Recipe_Ingredients_Ingredient
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id)
        );
    END
GO

PRINT 'Schema creation for Recipe DB completed successfully.';
