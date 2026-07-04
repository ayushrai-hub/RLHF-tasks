JAVAC ?= javac
JAVAFLAGS ?= -encoding UTF-8 -Xlint:all

.PHONY: all clean

all: bin/msreport

bin/msreport: src/MassSpec.java
	mkdir -p bin build/classes
	$(JAVAC) $(JAVAFLAGS) -d build/classes src/MassSpec.java
	printf '%s\n' '#!/bin/sh' 'exec java -cp /app/build/classes MassSpec "$$@"' > bin/msreport
	chmod +x bin/msreport

clean:
	rm -rf build bin/msreport
