USE master;
GO

BEGIN TRY
    --- Create admin login
    IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = N'admin')
    BEGIN
        CREATE LOGIN admin WITH PASSWORD = N'<Place_Holder_For_Admin_Password>', CHECK_POLICY = OFF;
    END

    --- Create recipe reader login
    IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = N'recipe_reader')
    BEGIN
            CREATE LOGIN recipe_reader WITH PASSWORD = N'<Place_Holder_For_Recipe_Reader_Password>', CHECK_POLICY = OFF;
    END

    --- Create telemetry writer login
    IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = N'telemetry_writer')
    BEGIN
        CREATE LOGIN telemetry_writer WITH PASSWORD = N'<Place_Holder_For_Telemetry_Writer_Password>', CHECK_POLICY = OFF;
    END

    PRINT N'All login accounts created successfully.';
END TRY
BEGIN CATCH
    PRINT N'Error: ' + ERROR_MESSAGE();
    THROW;
END CATCH
GO

BEGIN TRY
    -- Create recipe reader user
    IF DB_ID('RecipeDB') IS NOT NULL
        BEGIN
            USE RecipeDB;
            IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = N'recipe_reader')
                CREATE USER recipe_reader FOR LOGIN recipe_reader;
            IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = N'admin')
                CREATE USER admin FOR LOGIN admin;
        END

    -- Create telemetry writer user
    IF DB_ID('TelemetryDB') IS NOT NULL
        BEGIN
            USE TelemetryDB;
            IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = N'telemetry_writer')
                CREATE USER telemetry_writer FOR LOGIN telemetry_writer;
            IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = N'admin')
                CREATE USER admin FOR LOGIN admin;
        END

END TRY
BEGIN CATCH
    PRINT N'Error: ' + ERROR_MESSAGE();
    THROW;
END CATCH
GO

BEGIN TRY
    -- Assign roles to recipe reader user
    IF DB_ID('RecipeDB') IS NOT NULL
        BEGIN
            USE RecipeDB;
            IF IS_ROLEMEMBER(N'db_datareader', N'recipe_reader') = 0
                BEGIN
                    ALTER ROLE db_datareader ADD MEMBER recipe_reader;
                END
            IF IS_ROLEMEMBER(N'db_owner', N'admin') = 0
                BEGIN
                    ALTER ROLE db_owner ADD MEMBER admin;
                END
        END

    -- Assign roles to telemetry writer user
    IF DB_ID('TelemetryDB') IS NOT NULL
        BEGIN
            USE TelemetryDB;
            IF OBJECT_ID('TelemetryDB.dbo.Sessions', 'U') IS NOT NULL
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM sys.database_permissions AS p
                        JOIN sys.database_principals AS u ON p.grantee_principal_id = u.principal_id
                        WHERE u.name = 'telemetry_writer'
                          AND p.major_id = OBJECT_ID('TelemetryDB.dbo.Sessions')
                          AND p.permission_name IN ('INSERT', 'UPDATE')
                          AND p.state_desc = 'GRANT'
                        HAVING COUNT(DISTINCT p.permission_name) = 2
                    )
                        BEGIN
                            GRANT INSERT, UPDATE ON dbo.Sessions TO telemetry_writer;
                        END
                    GRANT SELECT (session_id) ON dbo.Sessions TO telemetry_writer;
                END
            IF OBJECT_ID('TelemetryDB.dbo.Telemetry_Events', 'U') IS NOT NULL
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM sys.database_permissions AS p
                        JOIN sys.database_principals AS u ON p.grantee_principal_id = u.principal_id
                        WHERE u.name = 'telemetry_writer'
                          AND p.major_id = OBJECT_ID('TelemetryDB.dbo.Telemetry_Events')
                          AND p.permission_name IN ('INSERT')
                          AND p.state_desc = 'GRANT'
                        HAVING COUNT(DISTINCT p.permission_name) = 1
                    )
                        BEGIN
                            GRANT INSERT ON dbo.Telemetry_Events TO telemetry_writer;
                        END
                    GRANT SELECT (event_id) ON dbo.Telemetry_Events TO telemetry_writer;
                END
            IF OBJECT_ID('TelemetryDB.dbo.Telemetry_Events_Table', 'U') IS NOT NULL
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM sys.database_permissions AS p
                        JOIN sys.database_principals AS u ON p.grantee_principal_id = u.principal_id
                        WHERE u.name = 'telemetry_writer'
                            AND p.major_id = OBJECT_ID('TelemetryDB.dbo.Telemetry_Events_Table')
                            AND p.permission_name IN ('SELECT')
                            AND p.state_desc = 'GRANT'
                        HAVING COUNT(DISTINCT p.permission_name) = 1
                    )
                        BEGIN
                            GRANT SELECT ON dbo.Telemetry_Events_Table TO telemetry_writer;
                        END
                END
            IF IS_ROLEMEMBER(N'db_owner', N'admin') = 0
                BEGIN
                    ALTER ROLE db_owner ADD MEMBER admin;
                END
        END
    PRINT N'Accounts script executed successfully.';
END TRY
BEGIN CATCH
    PRINT N'Error: ' + ERROR_MESSAGE();
    THROW;
END CATCH
GO
