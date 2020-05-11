@ECHO OFF
TITLE projectbox.bat - dummy-kapacitor_udf_python-scikit-grafana Project Environment

SET interactive=1
SET COMPOSE_CONVERT_WINDOWS_PATHS=1

SET TYPE=latest
SET TELEGRAF_TAG=latest
SET INFLUXDB_TAG=latest
SET CHRONOGRAF_TAG=latest
REM Note the kapacitor image tag, it differs from official because we need python more than 3.5
SET KAPACITOR_TAG=buster

ECHO %cmdcmdline% | FIND /i "/c"
IF %ERRORLEVEL% == 0 SET interactive=0

REM Enter attaches users to a shell in the desired container
IF "%1"=="enter" (
    IF "%2"=="" (
        ECHO projectbox enter ^(influxdb^|^|chronograf^|^|kapacitor^|^|telegraf^)
        GOTO End
    )
    IF "%2"=="influxdb" (
        ECHO Entering ^/bin^/bash session in the influxdb container...
        docker-compose exec influxdb /bin/bash
        GOTO End
    )
    IF "%2"=="chronograf" (
        ECHO Entering ^/bin^/bash session in the chronograf container...
        docker-compose exec chronograf /bin/bash
        GOTO End
    )
    IF "%2"=="kapacitor" (
        ECHO Entering ^/bin^/bash session in the kapacitor container...
        docker-compose exec kapacitor /bin/bash
        GOTO End
    )
    IF "%2"=="telegraf" (
        ECHO Entering ^/bin^/bash session in the telegraf container...
        docker-compose exec telegraf /bin/bash
        GOTO End
    )
)

REM Logs streams the logs from the container to the shell
IF "%1"=="logs" (
    IF "%2"=="" (
        ECHO projectbox logs ^(influxdb^|^|chronograf^|^|kapacitor^|^|telegraf^)
        GOTO End
    )
    IF "%2"=="influxdb" (
        ECHO Following the logs from the influxdb container...
        docker-compose logs -f influxdb
        GOTO End
    )
    IF "%2"=="chronograf" (
        ECHO Following the logs from the chronograf container...
        docker-compose logs -f chronograf
        GOTO End
    )
    IF "%2"=="kapacitor" (
        ECHO Following the logs from the kapacitor container...
        docker-compose logs -f kapacitor
        GOTO End
    )
    IF "%2"=="telegraf" (
        ECHO Following the logs from the telegraf container...
        docker-compose logs -f telegraf
        GOTO End
    )
)


IF "%1"=="up" (
		ECHO Building Kapacitor image based on debian-buster and python 3.7
		ECHO If this is your first time starting projectbox this might take a minute...
		docker build -f ./images/kapacitor/buster/Dockerfile -t kapacitor:buster ./images/kapacitor/buster/
		
        ECHO Spinning up latest, stable Docker Images for InfluxDB, Chronograf, Telegraf...
        ECHO If this is your first time starting projectbox this might take a minute...
        docker-compose up -d --build
		timeout /t 10 /nobreak > NUL
		ECHO Containers have running

REM		PAUSE
		ECHO Configuring Project artifacts...
REM Create db for the current project. If you attempt to create a database that already exists, InfluxDB does nothing and does not return an error.
		ECHO Creating database "printer" by InfluxDB HTTP API. If a database that already exists, InfluxDB does nothing and does not return an error.
		ECHO Expected response is {"results":[{"statement_id":0}]}. If differ then try to restart .bat or run manually: cmd.exe /c curl --data "q=CREATE DATABASE "printer"" http://localhost:8086/query
		cmd.exe /c curl --data "q=CREATE DATABASE "printer"" http://localhost:8086/query
REM		ECHO Configuring Kapacitor Task ads_demo...
		docker exec -it dummy-kapacitor_udf_python-scikit-grafana_kapacitor_1 bash -c "kapacitor define ads_demo -tick ./TICKscripts/ads_demo.tick && kapacitor enable ads_demo && kapacitor list tasks"
REM		ECHO Task "ads_demo" has configured. Check the task state in the Chronograf Manage Tasks tab.
        ECHO Grafana is available on http://localhost:3001
        ECHO Chronograf is available on http://localhost:8888
		ECHO Kapacitor and Influx will sync subscription during 1 minutes. Wait before sending the test datastream by test-data-ingestion-scripts\printer_data.py
        GOTO End
    )


IF "%1"=="down" (
    ECHO Stopping and removing running projectbox containers...
    docker-compose down
    GOTO End
)

IF "%1"=="restart" (
    ECHO Stopping all projectbox processes...
    docker-compose down >NUL 2>NUL
    ECHO Starting all projectbox processes...
    docker-compose up -d --build >NUL 2>NUL
    ECHO Services available!
    GOTO End
)

REM We do not delete grafana data as user do not need import dashboards manualy again, it is more convenient 
IF "%1"=="delete-data" (
    ECHO Deleting all influxdb, kapacitor and chronograf data...
    rmdir /S /Q kapacitor\data influxdb\data chronograf\data
    GOTO End
)
REM Dislike this command as it delete all images even those are not created by this script

REM IF "%1"=="docker-clean" (
REM     ECHO Stopping all running projectbox containers...
REM     docker-compose down
REM     echo Removing TICK images...
REM     docker-compose down --rmi=all
REM     GOTO End
REM )

IF "%1"=="influxdb" (
    ECHO Entering the influx cli...
    docker-compose exec influxdb /usr/bin/influx
    GOTO End
)
REM This option does not used in current prototype version
REM IF "%1"=="flux" (
REM     ECHO Entering the flux cli...
REM     docker-compose exec influxdb /usr/bin/influx -type flux
REM     GOTO End
REM )

REM This is optional command to local access native Influx Docs
REM IF "%1"=="rebuild-docs" (
REM     echo Rebuilding documentation container...
REM     docker build -t projectbox_documentation documentation\  >NUL 2>NUL
REM     echo "Restarting..."
REM     docker-compose down >NUL 2>NUL
REM     docker-compose up -d --build >NUL 2>NUL
REM     GOTO End
REM )

ECHO projectbox commands:
ECHO   up           -^> spin up the projectbox environment
ECHO   down         -^> tear down the projectbox environment
ECHO   restart      -^> restart the projectbox
ECHO   influxdb     -^> attach to the influx cli
REM ECHO   flux         -^> attach to the flux REPL
ECHO.
ECHO   enter ^(influxdb^|^|kapacitor^|^|chronograf^|^|telegraf^) -^> enter the specified container
ECHO   logs  ^(influxdb^|^|kapacitor^|^|chronograf^|^|telegraf^) -^> stream logs for the specified container
ECHO.
ECHO   delete-data  -^> delete all data created by the TICK Stack
REM ECHO   docker-clean -^> stop and remove all running docker containers and images
REM ECHO   rebuild-docs -^> rebuild the documentation image

:End
IF "%interactive%"=="0" PAUSE
EXIT /B 0
