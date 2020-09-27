
all:
	make clean
	make dirs
	make scrape
	make features
	make gephi

clean:
	rm -v data/processed/* || echo ""
	rm -v data/interim/* || echo ""
	rm -v data/report/* || echo ""

venv:
	python3.6 -m "venv" venv36/
	source ./env.sh; pip install -r requirements.txt	
	
dirs:
	mkdir -pv data/external
	mkdir -pv data/interim
	mkdir -pv data/processed
	mkdir -pv data/raw
	mkdir -pv data/report

scrape:
	cd src/download/; python3 download.py

features:
	cd src/; python3 features/reviews.py
	# In order to extend the extracted features by info from the DNB, you will have to add DNB credentials.
	# See Readme
	# cd src/; python3 features/extend_by_dnb.py
	# cd src/; python3 features/locations.py

gephi:
	cd src/; python3 gephi/keywords.py
	cd src/; python3 gephi/keywords.py --time-slice
	cd src/; python3 gephi/keywords.py --group-slice
	cd src/; python3 gephi/text.py
	cd src/; python3 gephi/reviewers.py
	cd src/; python3 gephi/reviewers.py --time-slice

viz:
	cd src/; python3 visualization/books.py
	cd src/; python3 visualization/keywords.py	
	cd src/; python3 visualization/reviewers.py
	cd src/; python3 visualization/texts.py
	# You will have to install additional dependencies to generate maps.
	# See Readme
	cd src/; python3 visualization/map.py
