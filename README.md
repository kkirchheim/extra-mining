# Extra Mining

This is the code used for the project presented on [www.extra-mining.de](https://extra-mining.de), surveying social sciences in germany based on reviews from *a well known website* and 
information provided by the Deutsche Nationalbilbiothek.

## Usage
To collect all webpages, invoke:
````shell script
make scrape
````

To extract features from the raw html files, invoke:
````shell script
make features
````

To generate files to use with Gephi, invoke:
````shell script
make gephi
````


To generate (some) visualizations, invoke:
````shell script
make viz
````

## Configuration

### Website
For this to work, you will have to adjust `URL_WEBSITE` in `src/config.py`
```
URL_WEBSITE = "https://www.xxx.de"
```

### Secrets
Secrets should be stored in `data/secrets.json`. 

#### DNB
You will need `dnb-access-token` to scrape information from the 
database of the Deutsche Nationalbibliothek (disabled by default). Contact the DNB for further information.

#### Tor
Optionally, you may want to provide a `tor-access-token` to 
fetch articles via tor, and obtain a new ip address after each download. 
You will have to install the `stem` package as well.

Note that we implemented this feature without any malicious intent, and for experimental purposes only. 

```json
{
    "dnb-access-token": "xxx",
    "tor-access-token": "xxx"
}
```

### Ignored Links
During feature extraction, we parse URLs from the reviews. To ignore certain URLs, add them to 
`resources/ignored-urls.txt`


### User Agent
If the file `data/user_agents.txt` is present while downloading, we will choose a random line from it as user agent 
string for HTTP requests.

## Dependencies

### Basic Dependencies
To install the basic dependencies, execute:

````shell script
pip install -r requirements.txt
````

### Maps
If you want to generate maps, you will need a file mapping city names to GPS coordinates. Unfortunately, 
the restrictive license does not allow me to share mine. The file should be a CSV with 
the following columns:

- city_name
- lng 
- lat 
- comment

Put it in `data/external/de.csv`.

Furthermore, you will have to install cartopy. At the time of writing, the package provided by PyPI
seems to be broken.

#### Anaconda
Cartopy can be installed via coda forge. 
```shell script
conda install -c conda-forge cartopy
```

#### Arch Linux

On Arch Linux, you will need the geos and the python proj package:
```shell script
pacman -S geos python-pyproj
```

To install Cartopy:
````shell script
pip install shapely --no-binary  :all:
pip install Cython
pip install -U git+https://github.com/SciTools/Cartopy.git
````

## Experimental

### Language Model
We tried to implement a simple language model (`notebooks/lang-model.ipynb`) that would allow us generate reviews. It did work that well. 
To run it, you will need Keras and Tensorflow:

````shell script
pip install keras tensorflow
````

### Recommender SVM
We build a SVM to created recommendations for articles (`notebooks/recommendations-svm.ipynb`) 
based on some reading history. The implementation is inspired by 
[Arxiv Sanity Preserver](https://github.com/karpathy/arxiv-sanity-preserver). 

 



