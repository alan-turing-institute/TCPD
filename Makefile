# Makefile for the Turing Change Point Dataset
#
# Author: G.J.J. van den Burg
# Copyright (c) 2019, The Alan Turing Institute
# License: See LICENSE file.
#

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

DATA_DIR=./datasets
UTIL_DIR=./utils
VENV_DIR=./venv
EXPORT_DIR=./export

.PHONY: all clean collect verify validate test export

all: test

################
# Main targets #
################

collect: venv
	source $(VENV_DIR)/bin/activate && python build_tcpd.py -v collect

##############
# Validation #
##############

test: verify validate

verify: venv collect $(UTIL_DIR)/check_checksums.py ./checksums.json
	@echo "Verifying datasets ..."
	source $(VENV_DIR)/bin/activate && \
		python $(UTIL_DIR)/check_checksums.py -v -c ./checksums.json -d $(DATA_DIR)

validate: venv collect $(UTIL_DIR)/validate_dataset.py ./schema.json
	@echo "Validating datasets"
	source $(VENV_DIR)/bin/activate && \
		python $(UTIL_DIR)/validate_dataset.py -v -s ./schema.json -d $(DATA_DIR)

####################
# Utility commands #
####################

export: test
	mkdir -p $(EXPORT_DIR)
	cp -v $(DATA_DIR)/*/*.json $(EXPORT_DIR)

###########
# Cleanup #
###########

clean:
	if [ -d $(VENV_DIR) ] ; then \
		source $(VENV_DIR)/bin/activate && python build_tcpd.py -v clean ; \
	fi
	rm -rf $(VENV_DIR)
	rm -rf $(EXPORT_DIR)

##############
# Virtualenv #
##############

venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate:
	test -d $(VENV_DIR) || python -m venv $(VENV_DIR)
	source $(VENV_DIR)/bin/activate && \
		pip install wheel && \
		pip install -r ./requirements.txt
	touch $(VENV_DIR)/bin/activate
