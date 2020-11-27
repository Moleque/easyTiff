FILES=$(filter-out $@,$(MAKECMDGOALS))
SHELL:=/bin/bash

file:	# transform file to Georeferenced
	gdalwarp -r bilinear -t_srs EPSG:4326 $(FILES)

folder:	# transform folder with files to Georeferenced
	@src="$(word 1,$(FILES))"; \
	dest="$(word 2,$(FILES))"; \
	for path in $${src}*.*; do \
		IFS='/' read -ra filename <<< $${path}; \
		gdalwarp -r bilinear -t_srs EPSG:4326 $${path} $${dest}$${filename[${#filename[@]}-1]}; \
	done
