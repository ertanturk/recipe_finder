IF DB_ID('TelemetryDB') IS NULL
    BEGIN
        CREATE DATABASE TelemetryDB;
    END
GO

USE TelemetryDB;
GO

IF OBJECT_ID('TelemetryDB.dbo.Sessions', 'U') IS NULL
    BEGIN
        CREATE TABLE Sessions (
            session_id INT IDENTITY(1,1) PRIMARY KEY,
            started_at DATETIME2 NOT NULL,
            ended_at DATETIME2,
            app_version NVARCHAR(20) NOT NULL,
            language_code NVARCHAR(10) NOT NULL
        );
    END
GO

IF OBJECT_ID('TelemetryDB.dbo.Telemetry_Events_Table', 'U') IS NULL
    BEGIN
        CREATE TABLE Telemetry_Events_Table (
            event_type_id INT PRIMARY KEY NOT NULL,
            event_type NVARCHAR(50) NOT NULL UNIQUE
        );
    END
GO

IF OBJECT_ID('TelemetryDB.dbo.Telemetry_Events', 'U') IS NULL
    BEGIN
        CREATE TABLE Telemetry_Events (
            event_id INT IDENTITY(1,1) PRIMARY KEY,
            session_id INT NOT NULL,
            event_type_id INT NOT NULL,
            event_data NVARCHAR(MAX) NOT NULL,
            event_time DATETIME2 NOT NULL,

            CONSTRAINT FK_Telemetry_Events_Sessions
                FOREIGN KEY (session_id) REFERENCES Sessions(session_id),

            CONSTRAINT FK_Telemetry_Events_Type
                FOREIGN KEY (event_type_id) REFERENCES Telemetry_Events_Table(event_type_id),

            CONSTRAINT CK_Telemetry_Events_Data
                CHECK (ISJSON(event_data) = 1)
        );

        CREATE NONCLUSTERED INDEX IX_Telemetry_Events_SessionID ON Telemetry_Events(session_id);
        CREATE NONCLUSTERED INDEX IX_Telemetry_Events_EventTypeID ON Telemetry_Events(event_type_id);
    END
GO

PRINT 'Telemetry DB schema created successfully.';
