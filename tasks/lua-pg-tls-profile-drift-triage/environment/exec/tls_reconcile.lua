#!/usr/bin/env lua5.4
package.path = "/app/environment/?.lua;/app/environment/?/init.lua;" .. package.path

local json = require("lib.lua.json")
local path = require("lib.lua.path")
local driver = require("exec.driver")

local cfg = json.decode(path.read_all("/app/environment/config/pipeline.json"))
local report = driver.run(cfg)
driver.write_report(report, "/app/out/reconcile_report.json")
