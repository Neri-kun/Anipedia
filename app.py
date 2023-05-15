import math
from io import BytesIO

import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, url_for
from SPARQLWrapper import SPARQLWrapper, JSON
from urllib.parse import urlencode
from jinja2 import Template
from flask_paginate import Pagination, get_page_args, get_page_parameter


# import required module
from PIL import Image
import requests
global_results = []
app = Flask(__name__, static_url_path='/static')
#app.config['STATIC_URL'] = '/static'

# Define the DBpedia endpoint
#sparql = SPARQLWrapper("https://dbpedia.org/sparql")

@app.route('/')
def home():

    # Define the SPARQL endpoint and query
    endpoint_url = "http://dbpedia.org/sparql"

    # Set the SPARQL query
    query = """
        SELECT DISTINCT ?anime (REPLACE(REPLACE(SUBSTR(STR(?anime), STRLEN("http://dbpedia.org/resource/") + 1), "_", " "), "\'", "") AS ?title) (GROUP_CONCAT(DISTINCT ?episode; separator=", ") AS ?episodes) ?date ?abstract ?genres (GROUP_CONCAT(DISTINCT REPLACE(STR(?studio), "http://dbpedia.org/resource/", ""); separator=", ") AS ?studios)
        WHERE {
                {
                    SELECT DISTINCT ?anime (GROUP_CONCAT(DISTINCT CONCAT(UCASE(SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 1, 1)), SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 2)); separator=", ") AS ?genres)
                    (GROUP_CONCAT(DISTINCT REPLACE(STR(?studio), "http://dbpedia.org/resource/", ""); separator=", ") AS ?studios)
                        WHERE {
                                ?anime rdf:type dbo:Anime.
                                OPTIONAL { ?anime dbp:genre ?genre. }
                                   
                                }
                }
          ?anime rdf:type dbo:Anime ;
                 dbo:abstract ?abstract;
                 dbp:first ?date;
                dbp:episodes ?episode.
                 
                OPTIONAL {
                        ?anime dbp:studio ?studio.
                }
          FILTER (LANG(?abstract) = 'en')
        }
        ORDER BY DESC(?date)
        LIMIT 12
    """
    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    urls = []
    anime_results = results["results"]["bindings"]
    for result in anime_results :
        result["title"]["value"] = result["title"]["value"].replace("'", "\\'")
        url = generate_url_by_anime_title(result["title"]["value"])
        urls.append(url)

    query = """SELECT DISTINCT (REPLACE(STRAFTER(str(?genre), "http://dbpedia.org/resource/"), "_", " ") AS ?genre)
        WHERE {
          ?anime rdf:type dbo:Anime;
            dbp:genre ?genre.
          FILTER (!regex(?genre, '^".*@".*en$'))
            }"""

    new_results = []

    for result in results["results"]["bindings"] :

        episodes_string = result["episodes"]["value"]  # Assuming it is a string like "1,2,3,4,5"
        episodes_list = episodes_string.split(",")  # Split the string by comma to get a list of strings
        try:
            episodes_int = [int(num) for num in episodes_list]  # Convert each string element to an integer
            total_episodes = sum(episodes_int)  # Compute the sum of the integers

            result["episodes"]["value"] = total_episodes
            new_results.append(result["episodes"]["value"])
        except:
            new_results.append("")

    for i in range(len(new_results)):
        results["results"]["bindings"][i]["episodes"]["value"] = new_results[i]


    sparql = SPARQLWrapper(endpoint_url)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    genres = sparql.query().convert()["results"]["bindings"]
    filtered_genres = []

    for genre in genres:
        genre_value = genre["genre"]["value"]
        if genre_value and genre_value.strip():
            filtered_genres.append(genre_value)
    print("Genres :")
    filtered_genres = list(filter(lambda genre: genre["genre"]["value"].strip(), genres))


    return render_template("anime_website.html",results=results["results"]["bindings"], urls = urls, genres = filtered_genres)


#de refactorizat
@app.route('/search', methods=['GET','POST'])
def search():

    # Define the SPARQL endpoint and query
    print (request.args.get('query'))
    print (request.args.get('page'))
    print("Date : " + request.form['date'])
    print("End date : " + request.form['endDate'])
    endDate = request.form['endDate']
    date = request.form['date']
    query_keyword = request.form['query']
    query_keyword = query_keyword.replace("'", "\\'")
    genre = request.form['genre']

    # Get the current page from the query parameters, or default to page 1
    page = request.args.get('page',default= 1, type=int)
    return searchPaginated(page,query_keyword, genre,date, endDate)



#@app.route('/search/<int:page>/<query>/<genre>/<date>/<endDate>', methods=['GET'])
@app.route('/search/<int:page>/<query>/<genre>/<date>/<endDate>', methods=['GET'])
@app.route('/search/<int:page>/<query>/<genre>/<endDate>',defaults={'date': ''}, methods=['GET'])
@app.route('/search/<int:page>/<query>/<endDate>',defaults={'date': '', 'genre': ''}, methods=['GET'])
@app.route('/search/<int:page>/<query>', methods=['GET'])
def searchPaginated(page, query, genre="", date="", endDate=""):

    # Define the SPARQL endpoint and query
    #print(request.args.get('query'))
    print(page)
    print(query)
    print("Genre : " + genre)
    #print("Genre : " + genre)
    #print(genre)
    # Perform SPARQL query and return results
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query_statement = generate_query(query, genre, date, endDate)
    sparql.setQuery(query_statement)
    sparql.setReturnFormat(JSON)
    all_results = sparql.query().convert()['results']['bindings']

    # Calculate the number of results to display per page
    results_per_page = 10

    # Calculate the start and end indices of the results to display on the current page
    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page

    # Slice the results to only include the current page
    total_results = len(all_results)
    results = all_results[start_index:end_index]

    # Calculate the total number of pages for the search results
    num_pages = math.ceil(len(all_results) / results_per_page)

    # Determine if there is a previous page and/or a next page
    has_prev = page > 1
    has_next = page < num_pages

    # Generate pagination object
    #pagination = Pagination(page=page, total=total_results, per_page=results_per_page)
    print("Value of page before render: " + str(page))

    # Render the search results template with the current page, total number of pages, and results
    return render_template('search_results.html', results=results, current_page=page, num_pages=num_pages, has_prev=has_prev, has_next=has_next,
                           query=query, page=page, date=date, endDate=endDate, genre=genre)#, pagination=pagination)



@app.route('/destination/<int:page>/<query>/<int:loop_index>/<genre>/<date>/<endDate>',methods=['GET'])
@app.route('/destination/<int:page>/<query>/<int:loop_index>/<date>/<endDate>',methods=['GET'])
@app.route('/destination/<int:page>/<query>/<int:loop_index>/<genre>/<endDate>',methods=['GET'])
@app.route('/destination/<int:page>/<query>/<int:loop_index>/<endDate>',methods=['GET'])
@app.route('/destination/<int:page>/<query>/<int:loop_index>',methods=['GET'])
def destination(page,query, loop_index, genre="", date="", endDate=""):

    print(page)
    print(query)
    print(genre)
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query_statement = generate_query(query, genre,date, endDate)
    sparql.setQuery(query_statement)
    sparql.setReturnFormat(JSON)
    all_results = sparql.query().convert()['results']['bindings']

    # Calculate the number of results to display per page
    results_per_page = 10

    # Calculate the start and end indices of the results to display on the current page
    start_index = (page - 1) * results_per_page
    end_index = start_index + results_per_page

    # Slice the results to only include the current page
    total_results = len(all_results)
    results = all_results[start_index:end_index]

    result = results[loop_index]
    # Calculate the total number of pages for the search results
    num_pages = math.ceil(len(all_results) / results_per_page)

    print("Value of page before render: " + str(page))


    url = generate_url_by_anime_title(result["title"]["value"])


    episodes_string = result["episodes"]["value"]  # Assuming it is a string like "1,2,3,4,5"
    episodes_list = episodes_string.split(",")  # Split the string by comma to get a list of strings
    try:
        episodes_int = [int(num) for num in episodes_list]  # Convert each string element to an integer
        total_episodes = sum(episodes_int)  # Compute the sum of the integers
    except :
        total_episodes = ""
    print(total_episodes)  # Output the sum of the episodes

    result["episodes"]["value"] = total_episodes


    return render_template('destination.html', result=result, url = url)



@app.context_processor
def utility_processor():
    def generate_search_url(query,page):
        return url_for('searchPaginated', query=query, page=page)
    return dict(generate_search_url=generate_search_url)




def generate_query(query_keyword, genre, startDate, endDate):
    query = """
              SELECT DISTINCT
                  ?anime
                      (REPLACE(REPLACE(SUBSTR(STR(?anime), STRLEN("http://dbpedia.org/resource/") + 1), "_", " "), "\'", "") AS ?title)
                      ?genres
                      (GROUP_CONCAT(DISTINCT REPLACE(STR(?studio), "http://dbpedia.org/resource/", ""); separator=", ") AS ?studios)
                      (GROUP_CONCAT(DISTINCT ?title; separator=", ") AS ?titles)
                      (GROUP_CONCAT(DISTINCT ?episode; separator=", ") AS ?episodes)
                      (GROUP_CONCAT(DISTINCT ?first_release_date; separator=", ") AS ?first_release_dates)
                      (GROUP_CONCAT(DISTINCT ?last_release_date; separator=", ") AS ?last_release_dates)
                      (GROUP_CONCAT(DISTINCT CONCAT(UCASE(SUBSTR(REPLACE(LCASE(SUBSTR(STR(?network), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 1, 1)), SUBSTR(REPLACE(LCASE(SUBSTR(STR(?network), STRLEN("http://dbpedia.org/resource/")+1)), "_", ","), 2)); separator=",") AS ?networks)
                      ?homepage
                      ?abstract
                      
                  WHERE {
                  
                                {
                                    SELECT DISTINCT ?anime (GROUP_CONCAT(DISTINCT CONCAT(UCASE(SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 1, 1)), SUBSTR(REPLACE(LCASE(SUBSTR(STR(?genre), STRLEN("http://dbpedia.org/resource/")+1)), "_", " "), 2)); separator=", ") AS ?genres)
                                    WHERE {
                                        ?anime rdf:type dbo:Anime.
                                        OPTIONAL { ?anime dbp:genre ?genre. }
                                   
                                    }
                                }
                      ?anime rdf:type dbo:Anime.
                      OPTIONAL {
                          ?anime dbo:abstract ?abstract.
                      }
                      OPTIONAL {
                          ?anime foaf:name ?title.
                      }
                      OPTIONAL { 
                          ?anime dbo:network ?network.
                      }
                      OPTIONAL {
                          ?anime dbp:episodes ?episode.
                      }
                      OPTIONAL {
                          ?anime dbp:studio ?studio.
                      }
                      FILTER (LANG(?abstract) = "en")
                      OPTIONAL {
                          ?anime foaf:homepage ?homepage .
                      }
                      OPTIONAL {
                          ?anime dbp:first ?first_release_date.
                      }
                      OPTIONAL {
                          ?anime dbp:last ?last_release_date.
                      }
                      FILTER(REGEX(?anime, \'http://dbpedia.org/resource/.*""" + query_keyword + """.*\', "i"))
                """

    if startDate == "":
        query += """\nFILTER (?first_release_date <= '""" + endDate + """'^^xsd:date)
        """
    else:
        query += """\nFILTER (?first_release_date >= '""" + startDate + """'^^xsd:date && ?first_release_date <= '""" + endDate + """'^^xsd:date)
        """

    if genre != "All genres":
        words = genre.split()
        for word in words:
            query+= """\nFILTER(CONTAINS(LCASE(STR(?genres)),'""" + word.lower() + """'))
                    """
    query +="""\n}"""

    return query

def get_original_image_size(image_url):
    response = requests.get(image_url, stream=True)
    response.raw.decode_content = True

    # Open the image using PIL
    image = Image.open(response.raw)

    # Get the original image size
    original_size = image.size

    return original_size




def generate_url_by_anime_title(anime_title):

    url = f"https://www.google.com/search?q={anime_title}&tbm=isch"

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    image = soup.find("img", class_="yWs4tf")
    print(image["src"])

    image_url = image["src"]
    # Get the original image size
    original_size = get_original_image_size(image_url)
    width, height = original_size

    return image["src"]



if __name__ == '__main__':
    app.run()