USE RecipeDB;
GO

SET NOCOUNT ON;

CREATE TABLE #problems (
    rule_name NVARCHAR(50) NOT NULL,
    item NVARCHAR(100) NOT NULL
);

-- Every text key that is used as a name or as instructions.
WITH used_text_keys AS (
    SELECT name_text_id AS text_id FROM Recipes
    UNION ALL
    SELECT instructions_text_id FROM Recipes
    UNION ALL
    SELECT name_text_id FROM Recipe_Category
    UNION ALL
    SELECT name_text_id FROM Ingredients
)
INSERT INTO #problems (rule_name, item)

-- Rule 1: a recipe must have at least 1 category.
SELECT 'recipe_without_category', CONCAT('recipe_id=', r.recipe_id)
FROM Recipes r
WHERE NOT EXISTS (
    SELECT 1 FROM Recipe_Categories rc WHERE rc.recipe_id = r.recipe_id
)

UNION ALL

-- Rule 2: a recipe must have at least 1 ingredient.
SELECT 'recipe_without_ingredient', CONCAT('recipe_id=', r.recipe_id)
FROM Recipes r
WHERE NOT EXISTS (
    SELECT 1 FROM Recipe_Ingredients ri WHERE ri.recipe_id = r.recipe_id
)

UNION ALL

-- Rule 3: a text key must be used in only one place.
SELECT 'text_key_used_more_than_once', CONCAT('text_id=', text_id, ' used ', COUNT(*), ' times')
FROM used_text_keys
GROUP BY text_id
HAVING COUNT(*) > 1

UNION ALL

-- Rule 4: every text key must have a translation for each language.
SELECT 'missing_translation', CONCAT('text_id=', t.text_id, ' language=', l.language_code)
FROM Text_Keys t
CROSS JOIN Languages l
WHERE NOT EXISTS (
    SELECT 1
    FROM Localization lo
    WHERE lo.text_id = t.text_id
      AND lo.language_code = l.language_code
)

UNION ALL

-- Extra check: a text key that nothing uses is probably a seed mistake.
SELECT 'unused_text_key', CONCAT('text_id=', t.text_id)
FROM Text_Keys t
WHERE NOT EXISTS (
    SELECT 1 FROM used_text_keys u WHERE u.text_id = t.text_id
);

SELECT rule_name, item
FROM #problems
ORDER BY rule_name, item;

DECLARE @problem_count INT = (SELECT COUNT(*) FROM #problems);

IF @problem_count = 0
    PRINT 'All application rules are satisfied.';
ELSE
    PRINT CONCAT('Problems found: ', @problem_count);

DROP TABLE #problems;
GO
