package model

import (
	"bufio"
	"encoding/json"
	"os"
)

type Loader interface {
	Load(modelPath, gaugesPath string) (Input, error)
}

type FileLoader struct{}

func MustLoad(modelPath, gaugesPath string) Input {
	input, err := FileLoader{}.Load(modelPath, gaugesPath)
	if err != nil {
		panic(err)
	}
	return input
}

func (FileLoader) Load(modelPath, gaugesPath string) (Input, error) {
	data, err := os.ReadFile(modelPath)
	if err != nil {
		return Input{}, err
	}
	var m Model
	if err := json.Unmarshal(data, &m); err != nil {
		return Input{}, err
	}
	gauges, err := readGauges(gaugesPath)
	if err != nil {
		return Input{}, err
	}
	return Input{Model: m, Gauges: gauges}, nil
}

func readGauges(path string) ([]Gauge, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var gauges []Gauge
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		if scanner.Text() == "" {
			continue
		}
		var gauge Gauge
		if err := json.Unmarshal([]byte(scanner.Text()), &gauge); err != nil {
			return nil, err
		}
		gauges = append(gauges, gauge)
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return gauges, nil
}
