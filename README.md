Repository includes several implementations of Anomaly Detection solution based on InfluxDB \ TICK-stack.

Generally, each folder contains separate project. Project includes mostly Kapacitor configuration and ML\DL Model to detect anomalies.
The project name follow the template: _'data ingestion'-'data processing'-'ml-algorithm'-'visualization'_, which reflects how the main architectural layers are implemented.


Also repository includes source of kapacitor UDF python agent code in _'influx-anomaly/kapacitor'_ folder. It is included here as copy of https://github.com/influxdata/kapacitor + merged https://github.com/influxdata/kapacitor/pull/2311 .

Current list of implemenations include following:

<table>
    <tr>
        <td>Name \ Folder</td>
        <td>Data source</td>
        <td>Data Ingestion</td>
        <td>Processing</td>
        <td>Anomaly Detection</td>
        <td>Vizualization / Publication</td>
    </tr>
    <tr>
        <td>dummy-kapacitor_udf_python-scikit-grafana</td>
        <td>
	    <ul>
		<li>dummy data</li>
		<li>1 measurement</li>
		<li>1 tag</li>
		<li>3 float fileds</li>
	    </ul>
        <td>
	    <ul>
		<li>python script</li>
		<li>InfluxDB HTTP API</li>
		<li>line protocol</li>
	    </ul>	
	</td>
        <td>
	    <ul> <li>Kapacitor</li> <li>TICK script tasks</li> <li>python UDF agent</li> <li>UDF function</li></ul>
	</td>
        <td>
	    <ul> <li>Isolation Forest alg.</li> <li>scikit_learn lib</li> </ul>
	</td>
        <td>
	    <ul> <li>Grafana</li> <li>InfluxDB plugin</li> <li>Graph element</li>  <li>Dashboard</li> </ul>
	</td>
    </tr>
</table>

# Environment

## TICK-stack
Projects structure supposed to run docker env of `InfluxDB` and `Kapacitor`. Optionally `Chronograf` can be used for more comfortable exploring data in db.

You need kapacitor container/image with *installed python3 and lib used by UDF\Model*.

_TODO_: Incude into repository submodule with kapacitor Dockerfile for image with installed python and kapacitor UDF python agent package

> Note: all commands below are given in Windows PowerShell syntax.

1. Create docker network to run all InfluxDB, Kapacitor, Chronograf in it:

```
	docker network create influxdb-network
```

2. InfluxDB and Chronograf can be started with pretty standard configurations:
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
3. Having kapacitor image you can run it with following command:

> Important. The file `${PWD}/kapacitor/kapacitor.log` must exist on the host machine before running container. Overwise docker will create *folder* kapacitor.log instead of file and later kapacitor deamon will not able to open kapacitor.log to write into.

```
	SET ${PWD} C:\git\influx-anomaly\kapacitor-udf-python_scikit_grafana_dummy
	
	docker run --name=kapacitor -d `
		--net=influxdb-network `
		-h kapacitor `
		-p 9092:9092 `
		-e KAPACITOR_INFLUXDB_0_URLS_0=http://influxdb:8086 `
		-v ${PWD}/kapacitor:/var/lib/kapacitor `
		-v ${PWD}/kapacitor/kapacitor.log:/var/log/kapacitor/kapacitor.log `
		-v ${PWD}/kapacitor/kapacitor.conf:/etc/kapacitor/kapacitor.conf:ro `
		-v ${PWD}/kapacitor/tmp/:/tmp/ `
		-v ${PWD}/model:/var/lib/kapacitor/model `
		-e MODEL_PATH='/var/lib/kapacitor/model/adsmodel.pkl' `
	k_with_p:3
```
	
## UDF and Model dependencies
_TODO_: make project-specific Dockerfile with installation steps for dependencies

Initially UDF configuration in `kapacitor.conf` is commented. It is done so your virgin kapacitor container starts successully and you will able to install all required libs.
The 'UDF' folder contains requirements.txt to install on kapacitor container

1. After container has run connect it to like:

```
	docker exec -it kapacitor bash
```

2. Then inslall packeges with

```lang-sh
		cd /var/lib/kapacitor/UDFs && pip install -r requirements.txt
```

3. Finally uncomment udf configuration in `kapacitor.conf` and restart kapacitor container.

## Kapacitor TICKscript Tasks
In the kapacitor container bash session do steps:

1. Define new task by command

```
kapacitor define ads_demo -tick /var/lib/kapacitor/TICKscripts/ads_demo.tick
```

2. Enable created task:

```
	kapacitor enable ads_demo
```

3. Check the task's content and status 

```
	kapacitor show ads_demo
```
## Run Test Data stream
Each project may has specific steps depend on choosen implementation.

For example _kapacitor-udf-python_scikit_grafana_dummy_ use python stream to generate stream of data points with 3 fields in 24h window with 1 second step.
Configuration is made directly in python script `\test-data-ingestion-scripts\printer_data.py`

1. Change the start date of the stream here:
line 57:
``` 
	now = datetime(2020, 4, 13)
```

2. Change time window here:
line 64:  
```
	for i in range(60*60*2+2):
```
