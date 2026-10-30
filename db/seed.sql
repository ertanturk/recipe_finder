-- TELEMETRY DB SEED DATA
IF DB_ID('TelemetryDB') IS NOT NULL
    BEGIN
        USE TelemetryDB;

        BEGIN TRANSACTION;

        BEGIN TRY
            INSERT INTO Telemetry_Events_Table(event_type_id, event_type)
            VALUES (1, 'db_connection_opened'),
                   (2, 'db_connection_failed'),
                   (3, 'db_query_completed'),
                   (4, 'db_query_failed'),
                   (5, 'search_executed'),
                   (6, 'no_results'),
                   (7, 'recipe_clicked'),
                   (8, 'recipe_skipped'),
                   (9, 'invalid_input'),
                   (10, 'language_changed'),
                   (11, 'error');

            COMMIT TRANSACTION;
            PRINT N'TelemetryDB seed completed.';
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
            THROW;
        END CATCH
    END
GO


-- RECIPE DB SEED DATA
IF DB_ID('RecipeDB') IS NOT NULL
    BEGIN
        USE RecipeDB;

        BEGIN TRANSACTION;

        BEGIN TRY
            INSERT INTO Languages(language_code, language_name)
            VALUES (N'en', N'English'),
                   (N'tr', N'Turkish');

            DECLARE @breakfastTextId INT, @breakfastCatId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @breakfastTextId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@breakfastTextId, N'en', N'Breakfast'), (@breakfastTextId, N'tr', N'Kahvaltı');
            INSERT INTO Recipe_Category (name_text_id) VALUES (@breakfastTextId); SET @breakfastCatId = SCOPE_IDENTITY();

            DECLARE @lunchTextId INT, @lunchCatId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @lunchTextId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@lunchTextId, N'en', N'Lunch'), (@lunchTextId, N'tr', N'Öğle Yemeği');
            INSERT INTO Recipe_Category (name_text_id) VALUES (@lunchTextId); SET @lunchCatId = SCOPE_IDENTITY();

            DECLARE @dinnerTextId INT, @dinnerCatId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @dinnerTextId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@dinnerTextId, N'en', N'Dinner'), (@dinnerTextId, N'tr', N'Akşam Yemeği');
            INSERT INTO Recipe_Category (name_text_id) VALUES (@dinnerTextId); SET @dinnerCatId = SCOPE_IDENTITY();

            DECLARE @snackTextId INT, @snackCatId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @snackTextId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@snackTextId, N'en', N'Snack'), (@snackTextId, N'tr', N'Atıştırmalık');
            INSERT INTO Recipe_Category (name_text_id) VALUES (@snackTextId); SET @snackCatId = SCOPE_IDENTITY();

            DECLARE @chickenNameId INT, @chickenId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @chickenNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@chickenNameId, N'en', N'chicken breast'), (@chickenNameId, N'tr', N'tavuk göğsü');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@chickenNameId, 120.0, 22.5, 2.6, 0.0, 0.0, 0.0, 74.0); SET @chickenId = SCOPE_IDENTITY();

            DECLARE @oilNameId INT, @oilId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @oilNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@oilNameId, N'en', N'olive oil'), (@oilNameId, N'tr', N'zeytinyağı');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@oilNameId, 884.0, 0.0, 100.0, 0.0, 0.0, 0.0, 2.0); SET @oilId = SCOPE_IDENTITY();

            DECLARE @oatsNameId INT, @oatsId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @oatsNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@oatsNameId, N'en', N'rolled oats'), (@oatsNameId, N'tr', N'yulaf ezmesi');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@oatsNameId, 389.0, 16.9, 6.9, 66.3, 0.9, 10.6, 2.0); SET @oatsId = SCOPE_IDENTITY();

            DECLARE @eggNameId INT, @eggId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @eggNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@eggNameId, N'en', N'egg'), (@eggNameId, N'tr', N'yumurta');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@eggNameId, 143.0, 12.6, 9.5, 0.7, 0.4, 0.0, 142.0); SET @eggId = SCOPE_IDENTITY();

            DECLARE @riceNameId INT, @riceId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @riceNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@riceNameId, N'en', N'white rice'), (@riceNameId, N'tr', N'pirinç');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@riceNameId, 365.0, 7.1, 0.6, 80.0, 0.1, 1.3, 5.0); SET @riceId = SCOPE_IDENTITY();

            DECLARE @bananaNameId INT, @bananaId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @bananaNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@bananaNameId, N'en', N'banana'), (@bananaNameId, N'tr', N'muz');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@bananaNameId, 89.0, 1.1, 0.3, 22.8, 12.2, 2.6, 1.0); SET @bananaId = SCOPE_IDENTITY();

            DECLARE @milkNameId INT, @milkId INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @milkNameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@milkNameId, N'en', N'milk'), (@milkNameId, N'tr', N'süt');
            INSERT INTO Ingredients (name_text_id, ingredient_calorie, ingredient_protein, ingredient_fat, ingredient_carbohydrate, ingredient_sugar, ingredient_fiber, ingredient_sodium)
            VALUES (@milkNameId, 42.0, 3.4, 1.0, 5.0, 5.0, 0.0, 44.0); SET @milkId = SCOPE_IDENTITY();

            -- Recipe 1:
            DECLARE @r1NameId INT, @r1InstId INT, @r1Id INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @r1NameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@r1NameId, N'en', N'Grilled Chicken with Rice'), (@r1NameId, N'tr', N'Pirinç Pilavı Eşliğinde Izgara Tavuk');

            INSERT INTO Text_Keys DEFAULT VALUES; SET @r1InstId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value)
            VALUES (@r1InstId, N'en', REPLACE(N'1. Wash the raw rice thoroughly with warm water until the water runs clear.\n2. Heat olive oil in a pan, add the rice and sauté for 3-4 minutes until translucent.\n3. Add boiling water and salt, cover the pan, and cook on low heat until the water is fully absorbed, then let it rest.\n4. Slice the raw chicken breast into uniform fillets and season with preferred spices.\n5. Heat a grill pan over high heat, place the chicken fillets, and cook for 4-5 minutes on each side until well-browned and cooked through.\n6. Serve the warm cooked chicken alongside the cooked rice.', N'\n', NCHAR(10))),
                   (@r1InstId, N'tr', REPLACE(N'1. Pirinci berrak bir su akana kadar ılık suda iyice yıkayın ve süzün.\n2. Pilav tenceresinde zeytinyağını ısıtın, pirinçleri ekleyip şeffaflaşana kadar 3-4 dakika kavurun.\n3. Sıcak su ve tuzu ilave edin, tencerenin kapağını kapatıp kısık ateşte suyunu tamamen çekene kadar pişirin ve demlenmeye bırakın.\n4. Çiğ tavuk göğsünü eşit kalınlıkta filetolar halinde dilimleyin ve dilediğiniz baharatlarla harmanlayın.\n5. Izgara tavasını yüksek ateşte iyice ısıtın, tavuk filetolarını yerleştirip her iki yüzünü de altın sarısı renk alana kadar 4-5 er dakika pişirin.\n6. Hazırlanan pirinç pilavı ile ızgara tavuğu sıcak olarak servis tabağına aktarın.', N'\n', NCHAR(10)));

            INSERT INTO Recipes (name_text_id, instructions_text_id, recipe_prep_time_in_minutes) VALUES (@r1NameId, @r1InstId, 35); SET @r1Id = SCOPE_IDENTITY();
            INSERT INTO Recipe_Categories (recipe_id, category_id) VALUES (@r1Id, @dinnerCatId), (@r1Id, @lunchCatId);
            INSERT INTO Recipe_Ingredients (recipe_id, ingredient_id, ingredient_quantity) VALUES (@r1Id, @chickenId, 250.0), (@r1Id, @riceId, 150.0), (@r1Id, @oilId, 20.0);

            -- Recipe 2:
            DECLARE @r2NameId INT, @r2InstId INT, @r2Id INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @r2NameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@r2NameId, N'en', N'Protein Oatmeal Bowl'), (@r2NameId, N'tr', N'Proteinli Yulaf Lapası');

            INSERT INTO Text_Keys DEFAULT VALUES; SET @r2InstId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value)
            VALUES (@r2InstId, N'en', REPLACE(N'1. Pour milk into a small saucepan and add rolled oats.\n2. Cook over medium-low heat, stirring continuously with a spatula, until the mixture thickens to a creamy consistency (about 5-7 minutes).\n3. Remove the saucepan from heat and transfer the oatmeal into a serving bowl.\n4. Slice the banana into clean, uniform rounds.\n5. Arrange the banana slices neatly on top of the warm oatmeal and serve immediately.', N'\n', NCHAR(10))),
                   (@r2InstId, N'tr', REPLACE(N'1. Küçük bir sos tenceresine sütü dökün ve yulaf ezmesini ekleyin.\n2. Orta-kısık ateşte, spatula ile sürekli karıştırarak kıvam alıp koyulaşana kadar (yaklaşık 5-7 dakika) pişirin.\n3. Tencereyi ocaktan alın ve yulaf lapasını derin bir servis kasesine aktarın.\n4. Muzu kabuğundan ayırıp ince halkalar halinde dilimleyin.\n5. Dilimlenen muzları sıcak yulafın üzerine düzenli bir şekilde dizerek servis edin.', N'\n', NCHAR(10)));

            INSERT INTO Recipes (name_text_id, instructions_text_id, recipe_prep_time_in_minutes) VALUES (@r2NameId, @r2InstId, 10); SET @r2Id = SCOPE_IDENTITY();
            INSERT INTO Recipe_Categories (recipe_id, category_id) VALUES (@r2Id, @breakfastCatId), (@r2Id, @snackCatId);
            INSERT INTO Recipe_Ingredients (recipe_id, ingredient_id, ingredient_quantity) VALUES (@r2Id, @oatsId, 60.0), (@r2Id, @milkId, 200.0), (@r2Id, @bananaId, 120.0);


            -- Recipe 3:
            DECLARE @r3NameId INT, @r3InstId INT, @r3Id INT;
            INSERT INTO Text_Keys DEFAULT VALUES; SET @r3NameId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value) VALUES (@r3NameId, N'en', N'Scrambled Eggs'), (@r3NameId, N'tr', N'Çırpılmış Yumurta');

            INSERT INTO Text_Keys DEFAULT VALUES; SET @r3InstId = SCOPE_IDENTITY();
            INSERT INTO Localization (text_id, language_code, text_value)
            VALUES (@r3InstId, N'en', REPLACE(N'1. Crack the eggs into a mixing bowl, add a pinch of salt, and beat thoroughly with a fork until smooth.\n2. Heat olive oil in a non-stick frying pan over low heat.\n3. Pour the beaten eggs into the heated pan and let them sit undisturbed for 20-30 seconds until the edges start to firm up.\n4. Using a spatula, gently push the edges toward the center to create soft, fluffy curds.\n5. Remove from heat just before they look fully dry to retain creaminess, then plate and serve.', N'\n', NCHAR(10))),
                   (@r3InstId, N'tr', REPLACE(N'1. Yumurtaları bir kaseye kırın, bir tutam tuz ilave edin ve çatalla iyice çırparak homojen hale getirin.\n2. Yapışmaz tabanlı bir tavada zeytinyağını kısık ateşte hafifçe ısıtın.\n3. Çırpılmış yumurtaları tavaya dökün ve kenarları hafifçe katılaşana kadar 20-30 saniye hiç dokunmadan bekletin.\n4. Bir spatula yardımıyla dış kısımlardan içe doğru nazikçe çekerek yumuşak yumurta tanecikleri oluşturun.\n5. Tamamen kurumadan, hafif kremsi yapısını korurken ocaktan alın ve sıcak olarak servis tabağına aktarın.', N'\n', NCHAR(10)));

            INSERT INTO Recipes (name_text_id, instructions_text_id, recipe_prep_time_in_minutes) VALUES (@r3NameId, @r3InstId, 5); SET @r3Id = SCOPE_IDENTITY();
            INSERT INTO Recipe_Categories (recipe_id, category_id) VALUES (@r3Id, @breakfastCatId), (@r3Id, @snackCatId);
            INSERT INTO Recipe_Ingredients (recipe_id, ingredient_id, ingredient_quantity) VALUES (@r3Id, @eggId, 150.0), (@r3Id, @oilId, 10.0);

            COMMIT TRANSACTION;
            PRINT N'RecipeDB seed completed.';
        END TRY
        BEGIN CATCH
            IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
            THROW;
        END CATCH
    END
GO
