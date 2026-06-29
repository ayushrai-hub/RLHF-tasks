#!/bin/bash
# Run the course-scheduler JAR to produce /opt/scheduler/schedule.json
set -e

java -jar /opt/scheduler/scheduler.jar
