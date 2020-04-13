Repository includes several implementations of Anomaly Detection solution based on InfluxDB \ TICK-stack.
Generally, each folder contains separate project. Project includes mostly Kapacitor configuration and ML\DL Model to detect anomalies.

Also repository includes source of kapacitor UDF python agent code. It is included here as copy of https://github.com/influxdata/kapacitor + merged https://github.com/influxdata/kapacitor/pull/2311 .

Current list of implemenations incluse following:

|name\folder							  |Data source|Data Ingestion|Processing|Anomaly Detection|Vizualization|Publication|
|kapacitor-udf-python_scikit_grafana_dummy|dummy data |python script, InfluxDB HTTP API, line protocol|Kapacitor, TICKscript tasks, python UDF agent, UDF function|Isolation Forest alg., sci-kit_learn lib.|Grafana, InfluxDB plugin, Graph element|Grafana Dashboard/Panel|  

Environment

TICK-stack
Projects structure supposed to run docker env of InfluxDB and Kapacitor. Chronograf can be used for more comfortable exploring data in db.

You need kapacitor container/image with installed python3 and lib used by UDF\Model.

TODO: Incude into repository submodule with kapacitor Dockerfile for image with installed python and kapacitor UDF python agent package

Note: all commands below are given in Windows PowerShell syntax.

All InfluxDB, Kapacitor, Chronograf must be started in one docker network:

```
	docker network create influxdb-network
```

InfluxDB and Chronograf can be started with pretty standard configurations:
```
	docker run --name=influxdb -d `
		--net=influxdb-network `
		-p 8086:8086 `
		-v <path-to-work-dir>\influxdb_docker\:/var/lib/influxdb `
	influxdb
```
```
	docker run --name=chronograf -d `
		--net=influxdb-network `
		-p 8888:8888 `
		-v <path-to-work-dir>\chronograf_docker:/var/lib/chronograf `
      chronograf --influxdb-url=http://influxdb:8086
```
Having kapacitor image you can run it with following command:

```
	SET ${PWD} C:\git\influx-anomaly\kapacitor-udf-python_scikit_grafana_dummy
	
	docker run --name=kapacitor -d `
		--net=influxdb-network `
		-h kapacitor_with_python `
		-p 9092:9092 `
		-e KAPACITOR_INFLUXDB_0_URLS_0=http://influxdb:8086 `
		-v ${PWD}/kapacitor:/var/lib/kapacitor `
		-v ${PWD}/kapacitor/kapacitor.log:/var/log/kapacitor/kapacitor.log `
		-v ${PWD}/kapacitor/kapacitor.conf:/etc/kapacitor/kapacitor.conf:ro `
		-v ${PWD}/tmp/:/tmp/ `
	k_with_p:3
```
	
UDF and Model dependencies
Initially UDF configuration in `kapacitor.conf` is commented. It is done so your virgin kapacitor container starts successully and you will able to install all required libs.
The 'UDF' folder contains requirements.txt to install on kapacitor container

After container has run connect it to like:
	docker exec -it kapacitor_with_python bash

Then inslall packeges with

```lang-sh
		cd /var/lib/kapacitor/UDFs && pip install -r requirements.txt
```
	
Finally uncomment udf configuration in `kapacitor.conf` and restart kapacitor container.