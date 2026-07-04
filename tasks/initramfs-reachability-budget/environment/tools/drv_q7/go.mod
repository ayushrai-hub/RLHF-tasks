module lab/drv_q7

go 1.24

require (
	github.com/BurntSushi/toml v1.4.0
	lab/pk_a v0.0.0
	lab/pk_b v0.0.0
	lab/pk_c v0.0.0
)

replace (
	lab/pk_a => ../../pk_a
	lab/pk_b => ../../pk_b
	lab/pk_c => ../../pk_c
)
