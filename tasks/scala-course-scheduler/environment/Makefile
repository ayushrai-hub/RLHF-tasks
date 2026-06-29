.PHONY: build run score clean

build:
	cd /app && sbt assembly && cp target/scala-3.3.4/scheduler.jar /opt/scheduler/scheduler.jar

run:
	java -jar /opt/scheduler/scheduler.jar

score:
	python3 /opt/scheduler/model.py /opt/scheduler/schedule.json

all: build run score

clean:
	cd /app && sbt clean
